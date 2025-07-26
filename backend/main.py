from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from google.oauth2 import service_account
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from ai_pipeline.pipeline import AIPipeline
from backend.api.receipts import create_wallet_receipt
from backend.firestudio.firebase import FirebaseClient

firebase_client = FirebaseClient()

# Load environment variables
load_dotenv()

# Get project configuration
PROJECT_ID = os.getenv("PROJECT_ID", "steady-anagram-466916-t6")
LOCATION = os.getenv("LOCATION", "us-central1")
CREDENTIALS = service_account.Credentials.from_service_account_file(
    "backend/config/service-account.json",
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

# Initialize FastAPI app
app = FastAPI()

# Initialize AI Pipeline
if not PROJECT_ID or not LOCATION:
    raise RuntimeError("PROJECT_ID and LOCATION must be set in .env file")

pipeline = AIPipeline(project_id=PROJECT_ID, location=LOCATION, credentials=CREDENTIALS)

# Pydantic models for request bodies
class QueryRequest(BaseModel):
    query: str
    user_id: str

class InsightsRequest(BaseModel):
    user_id: str

class AddToWalletRequest(BaseModel):
    user_id: str = '123'
    receipt_id: str
    vendor: str
    category: str
    amount: str
    date: str
    time: str

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

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...), user_id: str = Form(default='123')):
    try:
        image_bytes = await file.read()
        result = pipeline.process_receipt(media_content=image_bytes, media_type="image", user_id=user_id)
        recipt_id = firebase_client.add_update_recipt_details(user_id = user_id, recipt_doc = result)
        # Only return OCR result, do not create wallet receipt here
        return {"ocr_result": result, "recipt_id": recipt_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")

@app.post("/add-to-wallet")
async def add_to_wallet(request: AddToWalletRequest):
    try:
        wallet_link = create_wallet_receipt(
            request.vendor,
            request.category,
            request.amount,
            request.date,
            request.time
        )
        
        firebase_client.add_update_recipt_details(user_id=request.user_id, recipt_id=request.receipt_id, recipt_doc=request.model_dump())
        return {"wallet_link": wallet_link}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create wallet pass: {str(e)}")
   

@app.get("/")
def read_root():
    return {"message": "Welcome to the Wallet Agent AI Pipeline"} 