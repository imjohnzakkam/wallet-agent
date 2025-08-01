from dataclasses import asdict
import datetime
import re
from dotenv.main import logger
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from google.cloud import storage

from ai_pipeline.pipeline import AIPipeline, Receipt, ReceiptCategory
from backend.api.receipts import create_wallet_receipt
from backend.firestudio.firebase import FirebaseClient
from backend.api.insights import create_insights_pass

# Load environment variables
load_dotenv()

# Get project configuration
PROJECT_ID = os.getenv("PROJECT_ID", "steady-anagram-466916-t6")
LOCATION = os.getenv("LOCATION", "us-central1")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "wallet-agent")

# Initialize FastAPI app
app = FastAPI()

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Initialize AI Pipeline and Firebase Client
try:
    firebase_client = FirebaseClient()
    pipeline = AIPipeline(project_id=PROJECT_ID, location=LOCATION, firebase_client=firebase_client)
    logger.info("Successfully initialized AI Pipeline and Firebase Client.")
except Exception as e:
    logger.error(f"Failed to initialize AI Pipeline or Firebase Client: {e}", exc_info=True)
    raise RuntimeError(f"Failed to initialize AI Pipeline or Firebase Client: {e}")


# Pydantic models for request bodies
class QueryRequest(BaseModel):
    query: str
    user_id: str = '123'

class InsightsRequest(BaseModel):
    user_id: str = '123'

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

        response = result['wallet_pass']['details']['response']
        response = response if response else str(result)

        
        # Store the query and its response in Firestore
        firebase_client.add_user_query(
            user_id=request.user_id,
            query=request.query,
            llm_response= response  # Assuming result is the string response
        )
        
        wallet_link = result['wallet_pass']['details'].get('wallet_link', None)
        
        return {
            "llm_response" : response,
            "wallet_link": wallet_link
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/insights")
async def insights_endpoint(user_id='123'):
    try:
        insights_data = pipeline.generate_insights(user_id=user_id)
        
        # Ensure insights_data is a dictionary
        if isinstance(insights_data, list) and insights_data:
            insights_data = insights_data[0]
        elif not isinstance(insights_data, dict):
            raise HTTPException(status_code=404, detail="Could not generate insights.")

        wallet_link = create_insights_pass(insights_data)
        return {"wallet_link": wallet_link}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queries")
async def get_queries_endpoint(user_id: str = '123'):
    try:
        queries = firebase_client.get_user_queries(user_id=user_id)
        return {"queries": queries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...), user_id: str = Form(default='123')):
    try:
        image_bytes = await file.read()
        result = pipeline.process_receipt(media_content=image_bytes, media_type="image", user_id=user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")

@app.post("/add-to-wallet")
async def add_to_wallet(request: AddToWalletRequest):
    try:
        
        receipt_doc = firebase_client.get_receipt_by_user_id_receipt_id(receipt_id=request.receipt_id,user_id=request.user_id)
        receipt_object = Receipt.from_dict(receipt_doc)
        receipt_object.amount = float(request.amount)
        receipt_object.vendor_name = request.vendor
        receipt_object.category = ReceiptCategory(request.category)
        receipt_object.date_time = datetime.datetime.strptime(f"{request.date} {request.time}", "%Y-%m-%d %H:%M:%S")

        wallet_link = create_wallet_receipt(
            receipt_object            
        )
        
        receipt_dict = asdict(receipt_object)
        receipt_dict.pop('raw_text', None)
        receipt_dict['category'] = receipt_object.category.value

        # Update the receipt with the wallet link
        firebase_client.add_update_receipt_details(
            user_id=request.user_id,
            receipt_id=request.receipt_id,
            receipt_doc=receipt_dict
        )
        return {"wallet_link": wallet_link}
    except Exception as e:
        logger.info("Error in adding to wallet",e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create wallet pass: {str(e)}")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Wallet Agent AI Pipeline"} 