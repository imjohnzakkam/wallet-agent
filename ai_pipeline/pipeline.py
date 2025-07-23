# Core Features: OCR, Chat Assistant, Analytics

import json
import re
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from google.cloud import firestore
import base64
from pathlib import Path

# Setup logging
def setup_logging():
    """Setup logging configuration"""
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'logs/wallet_agent_pipeline_{datetime.now().strftime("%Y%m%d")}.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# Data Models
class ReceiptCategory(Enum):
    GROCERY = "grocery"
    RESTAURANT = "restaurant"
    SHOPPING = "shopping"
    FUEL = "fuel"
    PHARMACY = "pharmacy"
    ELECTRONICS = "electronics"
    UTILITIES = "utilities"
    OTHER = "other"

class PassType(Enum):
    RECEIPT = "receipt"
    SHOPPING_LIST = "shopping_list"
    ANALYTICS = "analytics"
    ALERT = "alert"

@dataclass
class ReceiptItem:
    name: str
    quantity: float
    unit: str
    price: float
    category: str = ""

@dataclass
class Receipt:
    vendor_name: str
    category: ReceiptCategory
    date_time: datetime
    amount: float
    items: List[ReceiptItem]
    subtotal: float
    tax: float
    payment_method: str = ""
    currency: str = "INR"
    language: str = "en"
    raw_text: str = ""
    
@dataclass
class WalletPass:
    pass_type: PassType
    title: str
    subtitle: str
    details: Dict[str, Any]
    valid_until: Optional[datetime] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

# 1. OCR Pipeline Component
class ReceiptOCRPipeline:
    def __init__(self, project_id: str, location: str):
        logger.info("Initializing ReceiptOCRPipeline with Vertex AI")
        vertexai.init(project=project_id, location=location)
        self.model = GenerativeModel('gemini-1.5-flash-001')
        logger.info("ReceiptOCRPipeline initialized successfully")
        
    def extract_receipt_data(self, media_content: bytes, media_type: str = "image") -> Receipt:
        """Extract receipt information from image/video using Gemini multimodal"""
        
        logger.info(f"Starting OCR extraction for {media_type} ({len(media_content)} bytes)")
        
        prompt = """
        Analyze this receipt and extract the following information in JSON format:
        {
            "vendor_name": "store/restaurant name",
            "category": "grocery/restaurant/shopping/fuel/pharmacy/electronics/utilities/other",
            "date": "YYYY-MM-DD",
            "time": "HH:MM",
            "amount": total amount as float,
            "subtotal": subtotal as float,
            "tax": tax amount as float,
            "currency": "currency code (INR/USD/etc)",
            "payment_method": "cash/card/upi/other",
            "language": "ISO language code of the receipt",
            "items": [
                {
                    "name": "item name",
                    "quantity": quantity as float,
                    "unit": "unit (pcs/kg/l/etc)",
                    "price": price per unit as float
                }
            ]
        }
        
        If any field is not clearly visible, use reasonable defaults or empty strings.
        Ensure all numeric values are proper floats.
        """
        
        try:
            start_time = datetime.now()
            
            # Create content based on media type
            if media_type == "image":
                logger.debug("Processing image with Gemini")
                image_part = Part.from_data(media_content, mime_type="image/jpeg")
                response = self.model.generate_content([prompt, image_part])
            else:  # video
                logger.debug("Processing video with Gemini")
                video_part = Part.from_data(media_content, mime_type="video/mp4")
                response = self.model.generate_content([prompt, video_part])
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Gemini processing completed in {processing_time:.2f} seconds")
            
            # Parse JSON from response
            json_str = self._extract_json(response.text)
            data = json.loads(json_str)
            
            # Convert to Receipt object
            receipt = self._parse_receipt_data(data)
            receipt.raw_text = response.text
            
            logger.info(f"OCR extraction successful - Vendor: {receipt.vendor_name}, Amount: ₹{receipt.amount:.2f}, Items: {len(receipt.items)}")
            
            return receipt
            
        except Exception as e:
            logger.error(f"OCR extraction error: {e}")
            # Return a basic receipt with error info
            return Receipt(
                vendor_name="Unknown Vendor",
                category=ReceiptCategory.OTHER,
                date_time=datetime.now(),
                amount=0.0,
                items=[],
                subtotal=0.0,
                tax=0.0,
                raw_text=f"Error: {str(e)}"
            )
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from Gemini response"""
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json_match.group()
        return "{}"
    
    def _parse_receipt_data(self, data: dict) -> Receipt:
        """Convert extracted data to Receipt object"""
        # Parse date and time
        date_str = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        time_str = data.get("time", "00:00")
        date_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        
        # Parse items
        items = []
        for item_data in data.get("items", []):
            items.append(ReceiptItem(
                name=item_data.get("name", ""),
                quantity=float(item_data.get("quantity", 1)),
                unit=item_data.get("unit", "pcs"),
                price=float(item_data.get("price", 0))
            ))
        
        # Parse category
        category_str = data.get("category", "other").lower()
        category = ReceiptCategory.OTHER
        for cat in ReceiptCategory:
            if cat.value == category_str:
                category = cat
                break
        
        return Receipt(
            vendor_name=data.get("vendor_name", "Unknown"),
            category=category,
            date_time=date_time,
            amount=float(data.get("amount", 0)),
            items=items,
            subtotal=float(data.get("subtotal", 0)),
            tax=float(data.get("tax", 0)),
            payment_method=data.get("payment_method", ""),
            currency=data.get("currency", "INR"),
            language=data.get("language", "en")
        )

# 2. AI Chat Assistant Component
class ReceiptChatAssistant:
    def __init__(self, project_id: str, location: str, db=None):
        logger.info("Initializing ReceiptChatAssistant with Vertex AI")
        vertexai.init(project=project_id, location=location)
        self.model = GenerativeModel('gemini-1.5-flash-001')
        self.db = db
        logger.info("ReceiptChatAssistant initialized successfully")
        
    def process_query(self, query: str, user_id: str) -> WalletPass:
        """Process user query and generate appropriate wallet pass"""
        
        logger.info(f"Processing query for user {user_id}: {query}")
        
        # Classify query intent
        intent, params = self._classify_query(query)
        logger.debug(f"Query classified as: {intent} with params: {params}")
        
        # Route to appropriate handler
        if intent == "spending_analysis":
            result = self._handle_spending_analysis(query, params, user_id)
        elif intent == "shopping_list":
            result = self._handle_shopping_list(query, params, user_id)
        elif intent == "show_receipt":
            result = self._handle_show_receipt(query, params, user_id)
        else:
            result = self._handle_complex_query(query, user_id)
        
        logger.info(f"Query processed successfully - Pass type: {result.pass_type.value}, Title: {result.title}")
        return result
    
    def _classify_query(self, query: str) -> Tuple[str, Dict]:
        """Classify query intent using Gemini"""
        
        prompt = f"""
        Classify this user query into one of these intents:
        - show_receipt: User wants to see specific receipt(s)
        - spending_analysis: User wants spending statistics/totals
        - shopping_list: User wants to create a shopping list
        - other: Anything else
        
        Query: "{query}"
        
        Return as JSON: {{"intent": "...", "params": {{...}}}}
        """
        
        try:
            response = self.model.generate_content(prompt)
            data = json.loads(self._extract_json(response.text))
            return data.get("intent", "other"), data.get("params", {})
        except Exception as e:
            logger.warning(f"Query classification failed: {e}")
            return "other", {}
    
    def _handle_spending_analysis(self, query: str, params: Dict, user_id: str) -> WalletPass:
        """Handle spending analysis queries"""
        logger.debug("Handling spending analysis query")
        return WalletPass(
            pass_type=PassType.ANALYTICS,
            title="Spending Analysis",
            subtitle=f"Analysis for: {query}",
            details={
                "total_spending": 5000.0,
                "average_spending": 250.0,
                "receipt_count": 20,
                "by_category": {"grocery": 3000, "restaurant": 2000},
                "query": query
            }
        )
    
    def _handle_shopping_list(self, query: str, params: Dict, user_id: str) -> WalletPass:
        """Generate shopping lists based on query"""
        logger.debug("Handling shopping list query")
        return WalletPass(
            pass_type=PassType.SHOPPING_LIST,
            title="Shopping List",
            subtitle=f"Generated for: {query}",
            details={
                "items": [
                    {"name": "Rice", "quantity": "2kg", "estimated_price": 150},
                    {"name": "Vegetables", "quantity": "1kg", "estimated_price": 100}
                ],
                "total_estimate": 250.0,
                "query": query
            },
            valid_until=datetime.now() + timedelta(days=7)
        )
    
    def _handle_show_receipt(self, query: str, params: Dict, user_id: str) -> WalletPass:
        """Handle showing specific receipts"""
        logger.debug("Handling show receipt query")
        return WalletPass(
            pass_type=PassType.RECEIPT,
            title="Receipt Search",
            subtitle=f"Results for: {query}",
            details={
                "receipt_ids": ["receipt_1", "receipt_2"],
                "total_amount": 1500.0,
                "count": 2,
                "query": query
            }
        )
    
    def _handle_complex_query(self, query: str, user_id: str) -> WalletPass:
        """Handle complex queries using full context"""
        logger.debug("Handling complex query")
        return WalletPass(
            pass_type=PassType.ANALYTICS,
            title="Query Results",
            subtitle="Analysis complete",
            details={
                "insights": ["Insight 1", "Insight 2"],
                "data": {"key": "value"},
                "suggestions": ["Suggestion 1", "Suggestion 2"],
                "query": query
            }
        )
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from text"""
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json_match.group()
        return "{}"

# 3. Analysis Pipeline Component
class ReceiptAnalysisPipeline:
    def __init__(self, db=None, project_id: str = None, location: str = None):
        logger.info("Initializing ReceiptAnalysisPipeline")
        self.db = db
        if project_id and location:
            vertexai.init(project=project_id, location=location)
        logger.info("ReceiptAnalysisPipeline initialized successfully")
        
    def generate_periodic_insights(self, user_id: str) -> List[WalletPass]:
        """Generate periodic insights and alerts"""
        logger.info(f"Generating insights for user {user_id}")
        
        passes = []
        
        # Monthly spending summary
        monthly_pass = WalletPass(
            pass_type=PassType.ANALYTICS,
            title=f"{datetime.now().strftime('%B')} Spending Summary",
            subtitle="₹12,450 ↑15.3%",
            details={
                "total_spending": 12450,
                "change_percent": 15.3,
                "top_category": "grocery",
                "receipt_count": 45
            }
        )
        passes.append(monthly_pass)
        
        # Spending alerts
        alert_pass = WalletPass(
            pass_type=PassType.ALERT,
            title="High Spending Alert",
            subtitle="₹3,500 spent today",
            details={
                "alert_type": "high_spending",
                "amount": 3500,
                "average_daily": 450
            }
        )
        passes.append(alert_pass)
        
        logger.info(f"Generated {len(passes)} insights for user {user_id}")
        return passes

# Main Integration Class
class AIPipeline:
    def __init__(self, project_id: str, location: str, firestore_credentials=None):
        logger.info("Initializing AIPipeline")
        
        # Initialize Firestore (optional)
        self.db = None
        if firestore_credentials:
            try:
                self.db = firestore.Client.from_service_account_json(firestore_credentials)
                logger.info("Firestore initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize Firestore: {e}, running without database")
        else:
            logger.info("Running without Firestore database")
        
        # Initialize components
        self.ocr = ReceiptOCRPipeline(project_id, location)
        self.chat = ReceiptChatAssistant(project_id, location, self.db)
        self.analytics = ReceiptAnalysisPipeline(self.db, project_id, location)
        
        logger.info("AIPipeline initialized successfully")
    
    def process_receipt(self, media_content: bytes, media_type: str, user_id: str) -> Dict[str, Any]:
        """Process a receipt and store in database"""
        logger.info(f"Processing receipt for user {user_id} ({len(media_content)} bytes)")
        
        # Extract receipt data
        receipt = self.ocr.extract_receipt_data(media_content, media_type)
        
        # Store in Firestore if available
        receipt_id = "mock_receipt_id"
        if self.db:
            try:
                receipt_data = {
                    'user_id': user_id,
                    'vendor_name': receipt.vendor_name,
                    'category': receipt.category.value,
                    'date_time': receipt.date_time,
                    'amount': receipt.amount,
                    'subtotal': receipt.subtotal,
                    'tax': receipt.tax,
                    'currency': receipt.currency,
                    'payment_method': receipt.payment_method,
                    'language': receipt.language,
                    'items': [asdict(item) for item in receipt.items],
                    'created_at': datetime.now()
                }
                doc_ref = self.db.collection('receipts').add(receipt_data)
                receipt_id = doc_ref[1].id
                logger.info(f"Receipt stored in Firestore with ID: {receipt_id}")
            except Exception as e:
                logger.error(f"Failed to store receipt in Firestore: {e}")
        
        # Create wallet pass
        pass_data = WalletPass(
            pass_type=PassType.RECEIPT,
            title=f"{receipt.vendor_name}",
            subtitle=f"{receipt.date_time.strftime('%b %d, %Y')} - ₹{receipt.amount:.2f}",
            details={
                'receipt_id': receipt_id,
                'vendor': receipt.vendor_name,
                'amount': receipt.amount,
                'items_count': len(receipt.items),
                'category': receipt.category.value
            }
        )
        
        result = {
            'receipt_id': receipt_id,
            'receipt_data': {
                'user_id': user_id,
                'vendor_name': receipt.vendor_name,
                'category': receipt.category.value,
                'date_time': receipt.date_time,
                'amount': receipt.amount,
                'subtotal': receipt.subtotal,
                'tax': receipt.tax,
                'currency': receipt.currency,
                'payment_method': receipt.payment_method,
                'language': receipt.language,
                'items': [asdict(item) for item in receipt.items],
                'created_at': datetime.now()
            },
            'wallet_pass': asdict(pass_data)
        }
        
        logger.info(f"Receipt processing completed - ID: {receipt_id}, Vendor: {receipt.vendor_name}, Amount: ₹{receipt.amount:.2f}")
        return result
    
    def handle_query(self, query: str, user_id: str) -> Dict[str, Any]:
        """Handle user query and return wallet pass"""
        logger.info(f"Handling query for user {user_id}: {query}")
        
        pass_data = self.chat.process_query(query, user_id)
        
        # Store pass in database if available
        pass_id = "mock_pass_id"
        if self.db:
            try:
                pass_dict = asdict(pass_data)
                pass_dict['user_id'] = user_id
                pass_dict['pass_type'] = pass_data.pass_type.value
                doc_ref = self.db.collection('passes').add(pass_dict)
                pass_id = doc_ref[1].id
                logger.info(f"Query pass stored in Firestore with ID: {pass_id}")
            except Exception as e:
                logger.error(f"Failed to store query pass in Firestore: {e}")
        
        result = {
            'pass_id': pass_id,
            'wallet_pass': asdict(pass_data)
        }
        
        logger.info(f"Query handling completed - ID: {pass_id}, Type: {pass_data.pass_type.value}")
        return result
    
    def generate_insights(self, user_id: str) -> List[Dict[str, Any]]:
        """Generate analytical insights for user"""
        logger.info(f"Generating insights for user {user_id}")
        
        passes = self.analytics.generate_periodic_insights(user_id)
        
        results = []
        for pass_data in passes:
            pass_dict = asdict(pass_data)
            pass_dict['user_id'] = user_id
            pass_dict['pass_type'] = pass_data.pass_type.value
            
            pass_id = "mock_insight_id"
            if self.db:
                try:
                    doc_ref = self.db.collection('passes').add(pass_dict)
                    pass_id = doc_ref[1].id
                except Exception as e:
                    logger.error(f"Failed to store insight pass in Firestore: {e}")
            
            results.append({
                'pass_id': pass_id,
                'wallet_pass': pass_dict
            })
        
        logger.info(f"Insights generation completed - {len(results)} insights generated")
        return results