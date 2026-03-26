"""
Data Agent - Data Processing & Storage Agent
Handles data ingestion, transformation, queries, and storage operations.
"""

import logging
import os
import json
import uuid
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from datetime import datetime
from io import BytesIO

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import create_engine, Column, String, DateTime, JSON, Text, Integer, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from minio import Minio
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/aipm"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Prometheus metrics
REQUEST_COUNT = Counter('data_agent_requests_total', 'Total requests', ['endpoint'])
DATA_OPERATIONS = Counter('data_agent_operations_total', 'Data operations', ['operation'])

# MinIO client setup
minio_client = Minio(
    os.getenv("MINIO_ENDPOINT", "minio:9000"),
    access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
    secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
    secure=False
)

# Redis client
redis_client: Optional[redis.Redis] = None

# Database Models
class Dataset(Base):
    __tablename__ = "datasets"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    source_type = Column(String)  # upload, database, api
    storage_path = Column(String)
    schema_info = Column(JSON)
    row_count = Column(Integer)
    size_bytes = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extra_metadata = Column(JSON)

class QueryLog(Base):
    __tablename__ = "query_logs"
    
    id = Column(String, primary_key=True)
    dataset_id = Column(String)
    query_type = Column(String)
    query_details = Column(JSON)
    result_count = Column(Integer)
    execution_time_ms = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic Models
class QueryRequest(BaseModel):
    dataset_id: str = Field(..., description="Dataset to query")
    query_type: str = Field(..., description="Type: filter, aggregate, transform")
    parameters: Dict[str, Any] = Field(default_factory=dict)

class TransformRequest(BaseModel):
    dataset_id: str = Field(..., description="Dataset to transform")
    operations: List[Dict[str, Any]] = Field(..., description="List of transformation operations")
    output_name: Optional[str] = Field(default=None)

class IngestRequest(BaseModel):
    source_type: str = Field(..., description="Type: api, database, file")
    source_config: Dict[str, Any] = Field(..., description="Source configuration")
    dataset_name: str = Field(..., description="Name for the dataset")
    description: Optional[str] = Field(default=None)

class AgentResponse(BaseModel):
    result: Any
    operation: str
    rows_affected: Optional[int] = None
    processing_time_ms: float
    timestamp: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global redis_client
    redis_client = redis.from_url("redis://redis:6379", decode_responses=True)
    
    # Ensure MinIO bucket exists
    try:
        if not minio_client.bucket_exists("datasets"):
            minio_client.make_bucket("datasets")
    except Exception as e:
        logger.warning(f"MinIO bucket check failed: {e}")
    
    logger.info("Data Agent starting up...")
    
    yield
    
    if redis_client:
        await redis_client.close()
    logger.info("Data Agent shutting down...")

app = FastAPI(
    title="Data Agent",
    description="Data Processing & Storage Agent",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "data-agent",
        "timestamp": datetime.utcnow().isoformat(),
        "capabilities": ["ingest", "query", "transform", "store"]
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/execute")
async def execute(data: Dict[str, Any]):
    """Main execution endpoint for orchestrator"""
    action = data.get("action", "query")
    
    if action == "query":
        req = QueryRequest(**data.get("params", {}))
        return await execute_query(req)
    elif action == "transform":
        req = TransformRequest(**data.get("params", {}))
        return await transform_data(req)
    elif action == "ingest":
        req = IngestRequest(**data.get("params", {}))
        return await ingest_data(req)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    name: Optional[str] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Upload a data file (CSV, JSON, Parquet)"""
    import time
    start_time = time.time()
    
    REQUEST_COUNT.labels(endpoint="upload").inc()
    DATA_OPERATIONS.labels(operation="upload").inc()
    
    try:
        content = await file.read()
        dataset_id = str(uuid.uuid4())
        
        # Parse file based on type
        if file.filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(content))
        elif file.filename.endswith('.json'):
            df = pd.read_json(BytesIO(content))
        elif file.filename.endswith('.parquet'):
            df = pd.read_parquet(BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        # Save to MinIO
        parquet_buffer = BytesIO()
        df.to_parquet(parquet_buffer, index=False)
        parquet_buffer.seek(0)
        
        minio_client.put_object(
            "datasets",
            f"{dataset_id}.parquet",
            parquet_buffer,
            length=len(parquet_buffer.getvalue())
        )
        
        # Store metadata
        schema_info = {col: str(dtype) for col, dtype in df.dtypes.items()}
        
        dataset = Dataset(
            id=dataset_id,
            name=name or file.filename,
            description=description,
            source_type="upload",
            storage_path=f"datasets/{dataset_id}.parquet",
            schema_info=schema_info,
            row_count=len(df),
            size_bytes=len(content),
            metadata={"filename": file.filename, "columns": list(df.columns)}
        )
        
        db.add(dataset)
        db.commit()
        
        processing_time = (time.time() - start_time) * 1000
        
        return AgentResponse(
            result={"dataset_id": dataset_id, "columns": list(df.columns), "rows": len(df)},
            operation="upload",
            rows_affected=len(df),
            processing_time_ms=processing_time,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=AgentResponse)
async def execute_query(request: QueryRequest, db: Session = Depends(get_db)):
    """Execute a query on a dataset"""
    import time
    start_time = time.time()
    
    REQUEST_COUNT.labels(endpoint="query").inc()
    DATA_OPERATIONS.labels(operation="query").inc()
    
    try:
        # Get dataset info
        dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Load from MinIO
        response = minio_client.get_object("datasets", f"{request.dataset_id}.parquet")
        df = pd.read_parquet(BytesIO(response.read()))
        
        result_df = df
        
        # Execute query based on type
        if request.query_type == "filter":
            conditions = request.parameters.get("conditions", [])
            for condition in conditions:
                col = condition.get("column")
                op = condition.get("operator", "==")
                val = condition.get("value")
                
                if op == "==":
                    result_df = result_df[result_df[col] == val]
                elif op == "!=":
                    result_df = result_df[result_df[col] != val]
                elif op == ">":
                    result_df = result_df[result_df[col] > val]
                elif op == "<":
                    result_df = result_df[result_df[col] < val]
                elif op == "contains":
                    result_df = result_df[result_df[col].astype(str).str.contains(val, na=False)]
        
        elif request.query_type == "aggregate":
            group_by = request.parameters.get("group_by")
            aggregations = request.parameters.get("aggregations", {})
            
            if group_by:
                agg_dict = {}
                for col, agg in aggregations.items():
                    if agg in ["sum", "mean", "count", "min", "max"]:
                        agg_dict[col] = agg
                result_df = result_df.groupby(group_by).agg(agg_dict).reset_index()
        
        elif request.query_type == "sort":
            sort_by = request.parameters.get("sort_by", [])
            ascending = request.parameters.get("ascending", True)
            result_df = result_df.sort_values(by=sort_by, ascending=ascending)
        
        elif request.query_type == "limit":
            n = request.parameters.get("n", 100)
            result_df = result_df.head(n)
        
        # Convert to dict for response
        result_data = result_df.to_dict(orient='records')
        
        # Log query
        query_log = QueryLog(
            id=str(uuid.uuid4()),
            dataset_id=request.dataset_id,
            query_type=request.query_type,
            query_details=request.parameters,
            result_count=len(result_df),
            execution_time_ms=(time.time() - start_time) * 1000
        )
        db.add(query_log)
        db.commit()
        
        processing_time = (time.time() - start_time) * 1000
        
        return AgentResponse(
            result=result_data,
            operation="query",
            rows_affected=len(result_df),
            processing_time_ms=processing_time,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transform", response_model=AgentResponse)
async def transform_data(request: TransformRequest, db: Session = Depends(get_db)):
    """Apply transformations to a dataset"""
    import time
    start_time = time.time()
    
    REQUEST_COUNT.labels(endpoint="transform").inc()
    DATA_OPERATIONS.labels(operation="transform").inc()
    
    try:
        # Get dataset
        dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Load data
        response = minio_client.get_object("datasets", f"{request.dataset_id}.parquet")
        df = pd.read_parquet(BytesIO(response.read()))
        
        # Apply transformations
        for op in request.operations:
            op_type = op.get("type")
            
            if op_type == "drop_columns":
                cols = op.get("columns", [])
                df = df.drop(columns=[c for c in cols if c in df.columns])
            
            elif op_type == "rename":
                mapping = op.get("mapping", {})
                df = df.rename(columns=mapping)
            
            elif op_type == "fillna":
                col = op.get("column")
                value = op.get("value")
                df[col] = df[col].fillna(value)
            
            elif op_type == "astype":
                col = op.get("column")
                dtype = op.get("dtype")
                df[col] = df[col].astype(dtype)
            
            elif op_type == "calculate":
                new_col = op.get("new_column")
                expression = op.get("expression")  # e.g., "col1 + col2"
                # Simple calculation (can be enhanced)
                df[new_col] = df.eval(expression)
        
        # Save transformed dataset
        new_dataset_id = str(uuid.uuid4())
        parquet_buffer = BytesIO()
        df.to_parquet(parquet_buffer, index=False)
        parquet_buffer.seek(0)
        
        minio_client.put_object(
            "datasets",
            f"{new_dataset_id}.parquet",
            parquet_buffer,
            length=len(parquet_buffer.getvalue())
        )
        
        # Store metadata
        schema_info = {col: str(dtype) for col, dtype in df.dtypes.items()}
        
        new_dataset = Dataset(
            id=new_dataset_id,
            name=request.output_name or f"{dataset.name}_transformed",
            description=f"Transformed from {dataset.name}",
            source_type="transform",
            storage_path=f"datasets/{new_dataset_id}.parquet",
            schema_info=schema_info,
            row_count=len(df),
            metadata={"parent_id": request.dataset_id, "operations": request.operations}
        )
        
        db.add(new_dataset)
        db.commit()
        
        processing_time = (time.time() - start_time) * 1000
        
        return AgentResponse(
            result={"dataset_id": new_dataset_id, "columns": list(df.columns), "rows": len(df)},
            operation="transform",
            rows_affected=len(df),
            processing_time_ms=processing_time,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Transform failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest", response_model=AgentResponse)
async def ingest_data(request: IngestRequest, db: Session = Depends(get_db)):
    """Ingest data from external sources"""
    import time
    start_time = time.time()
    
    REQUEST_COUNT.labels(endpoint="ingest").inc()
    DATA_OPERATIONS.labels(operation="ingest").inc()
    
    try:
        df = None
        
        if request.source_type == "api":
            url = request.source_config.get("url")
            headers = request.source_config.get("headers", {})
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=30.0)
                data = response.json()
                
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                else:
                    # Try to normalize nested JSON
                    df = pd.json_normalize(data)
        
        elif request.source_type == "database":
            # Note: In production, use proper connection string handling
            raise HTTPException(status_code=501, detail="Database ingestion not yet implemented")
        
        if df is None or df.empty:
            raise HTTPException(status_code=400, detail="No data ingested")
        
        # Save to storage
        dataset_id = str(uuid.uuid4())
        parquet_buffer = BytesIO()
        df.to_parquet(parquet_buffer, index=False)
        parquet_buffer.seek(0)
        
        minio_client.put_object(
            "datasets",
            f"{dataset_id}.parquet",
            parquet_buffer,
            length=len(parquet_buffer.getvalue())
        )
        
        # Store metadata
        schema_info = {col: str(dtype) for col, dtype in df.dtypes.items()}
        
        dataset = Dataset(
            id=dataset_id,
            name=request.dataset_name,
            description=request.description,
            source_type=request.source_type,
            storage_path=f"datasets/{dataset_id}.parquet",
            schema_info=schema_info,
            row_count=len(df),
            metadata={"source_config": request.source_config, "columns": list(df.columns)}
        )
        
        db.add(dataset)
        db.commit()
        
        processing_time = (time.time() - start_time) * 1000
        
        return AgentResponse(
            result={"dataset_id": dataset_id, "columns": list(df.columns), "rows": len(df)},
            operation="ingest",
            rows_affected=len(df),
            processing_time_ms=processing_time,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/datasets")
async def list_datasets(db: Session = Depends(get_db)):
    """List all datasets"""
    datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).all()
    
    return [
        {
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "source_type": d.source_type,
            "row_count": d.row_count,
            "size_bytes": d.size_bytes,
            "created_at": d.created_at.isoformat(),
            "columns": list(d.schema_info.keys()) if d.schema_info else []
        }
        for d in datasets
    ]

@app.get("/datasets/{dataset_id}/download")
async def download_dataset(dataset_id: str, format: str = "csv", db: Session = Depends(get_db)):
    """Download a dataset in specified format"""
    try:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Load data
        response = minio_client.get_object("datasets", f"{dataset_id}.parquet")
        df = pd.read_parquet(BytesIO(response.read()))
        
        # Convert to requested format
        if format == "csv":
            buffer = BytesIO()
            df.to_csv(buffer, index=False)
            buffer.seek(0)
            return StreamingResponse(buffer, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={dataset.name}.csv"})
        
        elif format == "json":
            buffer = BytesIO()
            df.to_json(buffer, orient="records")
            buffer.seek(0)
            return StreamingResponse(buffer, media_type="application/json", headers={"Content-Disposition": f"attachment; filename={dataset.name}.json"})
        
        elif format == "parquet":
            buffer = BytesIO()
            df.to_parquet(buffer, index=False)
            buffer.seek(0)
            return StreamingResponse(buffer, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={dataset.name}.parquet"})
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")
            
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
