from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from ai_pipeline.pipeline import AIPipeline

# Load environment variables
load_dotenv()

# Get project configuration
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")

# Initialize FastAPI app
app = FastAPI()

# Initialize AI Pipeline
if not PROJECT_ID or not LOCATION:
    raise RuntimeError("PROJECT_ID and LOCATION must be set in .env file")

pipeline = AIPipeline(project_id=PROJECT_ID, location=LOCATION)

# Pydantic models for request bodies
class QueryRequest(BaseModel):
    query: str
    user_id: str

class InsightsRequest(BaseModel):
    user_id: str

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    try:
        result = pipeline.handle_query(query=request.query, user_id=request.user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/insights")
async def insights_endpoint(request: InsightsRequest):
    try:
        result = pipeline.generate_insights(user_id=request.user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "Welcome to the Wallet Agent AI Pipeline"} 