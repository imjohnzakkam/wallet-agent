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
from pathlib import Path

from backend.firestudio.firebase import FirebaseClient

# Setup logging
def setup_logging():
    """Setup logging configuration"""
    Path("logs").mkdir(exist_ok=True)
    
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

    @classmethod
    def from_dict(cls, data: dict) -> 'ReceiptItem':
        """
        Create a ReceiptItem instance from a dictionary.
        """
        return cls(
            name=data.get('name', ''),
            quantity=float(data.get('quantity', 0)),
            unit=data.get('unit', ''),
            price=float(data.get('price', 0)),
            category=data.get('category', '')
        )

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
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Receipt':
        """
        Create a Receipt instance from a dictionary.
        Handles type conversions for category, date_time, and items.
        """
        # Convert items to ReceiptItem objects
        items = []
        if data.get('items'):
            for item_data in data['items']:
                items.append(ReceiptItem.from_dict(item_data))
        
        # Convert category string to ReceiptCategory enum
        category_str = data.get('category', 'other').lower()
        
        category = ReceiptCategory(category_str)

        
        # Convert date_time string to datetime object if it's a string
        date_time = data.get('date_time')
        if isinstance(date_time, str):
            date_time = datetime.fromisoformat(date_time.replace('Z', '+00:00'))
        elif not isinstance(date_time, datetime):
            date_time = datetime.now()
        
        return Receipt(
            vendor_name=data.get('vendor_name', 'Unknown'),
            category=category,
            date_time=date_time,
            amount=float(data.get('amount', 0)),
            items=items,
            subtotal=float(data.get('subtotal', 0)),
            tax=float(data.get('tax', 0)),
            payment_method=data.get('payment_method', ''),
            currency=data.get('currency', 'INR'),
            language=data.get('language', 'en'),
            raw_text=data.get('raw_text', '')
        )
    
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
        self.model = GenerativeModel('gemini-2.5-flash')
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
            "amount": "total amount as float",
            "subtotal": "subtotal as float",
            "tax": "tax amount as float",
            "currency": "currency code (INR/USD/etc)",
            "payment_method": "cash/card/upi/other",
            "language": "ISO language code of the receipt",
            "items": [
                {
                    "name": "item name",
                    "quantity": "quantity as float",
                    "unit": "unit (pcs/kg/l/etc)",
                    "price": "price per unit as float"
                }
            ]
        }
        
        If any field is not clearly visible, use reasonable defaults or empty strings.
        Ensure all numeric values are proper floats.
        """
        
        try:
            start_time = datetime.now()
            
            if media_type == "image":
                image_part = Part.from_data(media_content, mime_type="image/jpeg")
                response = self.model.generate_content([prompt, image_part])
            else:
                video_part = Part.from_data(media_content, mime_type="video/mp4")
                response = self.model.generate_content([prompt, video_part])
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Gemini processing completed in {processing_time:.2f} seconds")
            
            json_str = self._extract_json(response.text)
            data = json.loads(json_str)
            
            receipt = self._parse_receipt_data(data)
            receipt.raw_text = response.text
            
            logger.info(f"OCR extraction successful - Vendor: {receipt.vendor_name}, Amount: ₹{receipt.amount:.2f}, Items: {len(receipt.items)}")
            
            return receipt
            
        except Exception as e:
            logger.error(f"OCR extraction error: {e}", exc_info=True)
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
        return json_match.group(0) if json_match else "{}"
    
    def _parse_receipt_data(self, data: dict) -> Receipt:
        """Convert extracted data to Receipt object"""
        date_str = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        time_str = data.get("time", "00:00")
        date_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        
        items = [ReceiptItem(**item_data) for item_data in data.get("items", [])]
        
        category_str = data.get("category", "other").lower()
        category = next((cat for cat in ReceiptCategory if cat.value == category_str), ReceiptCategory.OTHER)
        
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
    def __init__(self, project_id: str, location: str, db_client: FirebaseClient):
        logger.info("Initializing ReceiptChatAssistant with Vertex AI")
        vertexai.init(project=project_id, location=location)
        self.model = GenerativeModel('gemini-2.5-flash')
        self.db = db_client
        logger.info("ReceiptChatAssistant initialized successfully")
        
    def process_query(self, query: str, user_id: str) -> WalletPass:
        """Process user query and generate appropriate wallet pass"""
        
        logger.info(f"Processing query for user {user_id}: {query}")
        
        intent, params = self._classify_query(query)
        logger.debug(f"Query classified as: {intent} with params: {params}")
        
        handler_map = {
            "spending_analysis": self._handle_spending_analysis,
            "shopping_list": self._handle_shopping_list,
            "show_receipt": self._handle_show_receipt,
        }
        
        handler = handler_map.get(intent, self._handle_complex_query)
        result = handler(query, params, user_id)
        
        logger.info(f"Query processed successfully - Pass type: {result.pass_type.value}, Title: {result.title}")
        return result
    
    def _classify_query(self, query: str) -> Tuple[str, Dict]:
        """Classify query intent using Gemini"""
        
        prompt = f"""
        Analyze the user's query to understand their intent and extract relevant parameters for querying a receipt database.
        The current date is {datetime.now().strftime('%Y-%m-%d')}.

        Available intents: "show_receipt", "spending_analysis", "shopping_list", "other".
        Extract parameters: "start_date", "end_date", "category", "vendor_name", "amount_condition", "query_text".

        User Query: "{query}"

        Return your analysis as a JSON object: {{"intent": "...", "params": {{...}}}}
        """
        
        try:
            response = self.model.generate_content(prompt)
            data = json.loads(self._extract_json(response.text))
            return data.get("intent", "other"), data.get("params", {})
        except Exception as e:
            logger.warning(f"Query classification failed: {e}")
            return "other", {}
    
    def _fetch_receipts(self, user_id: str, params: Dict) -> List[Dict]:
        """Fetch receipts from Firestore based on query parameters."""
        if not self.db:
            logger.warning("Firestore is not available. Cannot fetch receipts.")
            return []

        try:
            start_date = params.get("start_date")
            end_date = params.get("end_date")
            
            receipts = self.db.get_receipts_by_timerange(user_id, start_date, end_date)
            
            # Further filtering in Python
            if params.get("category"):
                receipts = [r for r in receipts if r.get('category') == params["category"]]
            if params.get("vendor_name"):
                receipts = [r for r in receipts if r.get('vendor_name') == params["vendor_name"]]
            if params.get("amount_condition"):
                cond = params["amount_condition"]
                op = cond.get("operator")
                val = float(cond.get("value", 0))
                op_map = {"gt": lambda x: x > val, "lt": lambda x: x < val, "eq": lambda x: x == val}
                if op in op_map:
                    receipts = [r for r in receipts if op_map[op](r.get('amount', 0))]

            logger.info(f"Fetched and filtered {len(receipts)} receipts for user {user_id} with params {params}")
            return receipts

        except Exception as e:
            logger.error(f"Error fetching receipts from Firestore: {e}", exc_info=True)
            return []

    def _handle_spending_analysis(self, query: str, params: Dict, user_id: str) -> WalletPass:
        """Handle spending analysis queries"""
        receipts = self._fetch_receipts(user_id, params)
        if not receipts:
            return WalletPass(pass_type=PassType.ANALYTICS, title="Spending Analysis", subtitle="No receipts found.", details={"query": query})

        total_spending = sum(r.get('amount', 0) for r in receipts)
        by_category = {}
        for r in receipts:
            by_category[r.get('category', 'other')] = by_category.get(r.get('category', 'other'), 0) + r.get('amount', 0)

        return WalletPass(
            pass_type=PassType.ANALYTICS,
            title="Spending Analysis",
            subtitle=f"Analysis for: {query}",
            details={
                "total_spending": total_spending,
                "receipt_count": len(receipts),
                "by_category": by_category,
            }
        )
    
    def _handle_shopping_list(self, query: str, params: Dict, user_id: str) -> WalletPass:
        """Generate shopping lists based on query"""
        today = datetime.now().date()
        last_month_end = today.replace(day=1) - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        
        receipts = self._fetch_receipts(user_id, {
            "start_date": last_month_start.strftime("%Y-%m-%d"),
            "end_date": last_month_end.strftime("%Y-%m-%d"),
        })
        
        recent_items_str = ", ".join(list(set(item['name'] for r in receipts for item in r.get('items', [])))[:20])

        prompt = f"""
        User query: "{query}".
        Recent items: {recent_items_str}.
        Generate a shopping list in JSON: {{"items": [{{"name": "...", "quantity": "...", "estimated_price": ...}}], "total_estimate": ...}}
        """

        try:
            response = self.model.generate_content(prompt)
            list_data = json.loads(self._extract_json(response.text))
        except Exception as e:
            logger.error(f"Failed to generate shopping list with Gemini: {e}")
            list_data = {"items": [], "total_estimate": 0}

        return WalletPass(
            pass_type=PassType.SHOPPING_LIST,
            title="Your Shopping List",
            subtitle=f"Generated from: '{query}'",
            details=list_data,
            valid_until=datetime.now() + timedelta(days=7)
        )
    
    def _handle_show_receipt(self, query: str, params: Dict, user_id: str) -> WalletPass:
        """Handle showing specific receipts"""
        receipts = self._fetch_receipts(user_id, params)

        if not receipts:
            return WalletPass(pass_type=PassType.RECEIPT, title="Receipt Search", subtitle="No results.", details={"query": query})

        return WalletPass(
            pass_type=PassType.RECEIPT,
            title="Receipt Search",
            subtitle=f"Found {len(receipts)} receipts",
            details={
                "receipt_summaries": [{k: r[k] for k in ('receipt_id', 'vendor_name', 'amount', 'date_time')} for r in receipts],
                "total_amount": sum(r.get('amount', 0) for r in receipts),
            }
        )
    
    def _handle_complex_query(self, query: str, params: Dict, user_id: str) -> WalletPass:
        """Handle complex queries using full context"""
        return WalletPass(pass_type=PassType.ANALYTICS, title="Query Results", subtitle="Analysis complete", details={"query": query})
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from text"""
        json_match = re.search(r'\{[\s\S]*\}', text)
        return json_match.group(0) if json_match else "{}"

# 3. Analysis Pipeline Component
class ReceiptAnalysisPipeline:
    def __init__(self, db_client: FirebaseClient, project_id: str = None, location: str = None):
        logger.info("Initializing ReceiptAnalysisPipeline")
        self.db = db_client
        if project_id and location:
            vertexai.init(project=project_id, location=location)
        logger.info("ReceiptAnalysisPipeline initialized successfully")
        
    def generate_periodic_insights(self, user_id: str) -> List[WalletPass]:
        """Generate periodic insights and alerts"""
        logger.info(f"Generating insights for user {user_id}")
        
        # This is a mock implementation. A real implementation would fetch and analyze data.
        return [
            WalletPass(pass_type=PassType.ANALYTICS, title=f"Monthly Summary", subtitle="Sample insight"),
            WalletPass(pass_type=PassType.ALERT, title="Spending Alert", subtitle="Sample alert"),
        ]

# Main Integration Class
class AIPipeline:
    def __init__(self, project_id: str, location: str, firebase_client: FirebaseClient):
        logger.info("Initializing AIPipeline")
        
        self.db = firebase_client
        self.ocr = ReceiptOCRPipeline(project_id, location)
        self.chat = ReceiptChatAssistant(project_id, location, self.db)
        self.analytics = ReceiptAnalysisPipeline(self.db, project_id, location)
        
        logger.info("AIPipeline initialized successfully")
    
    def process_receipt(self, media_content: bytes, media_type: str, user_id: str) -> Dict[str, Any]:
        """Process a receipt and store in database"""
        logger.info(f"Processing receipt for user {user_id}")
        
        receipt = self.ocr.extract_receipt_data(media_content, media_type)
        
        receipt_data_to_store = asdict(receipt)
        receipt_data_to_store.pop('raw_text', None)
        receipt_data_to_store['category'] = receipt.category.value

        receipt_id = self.db.add_update_receipt_details(user_id, receipt_doc=receipt_data_to_store)
        logger.info(f"Receipt stored with ID: {receipt_id}")
        
        return {
            'receipt_id': receipt_id,
            'receipt_data': receipt_data_to_store,
        }
    
    def handle_query(self, query: str, user_id: str) -> Dict[str, Any]:
        """Handle user query and return wallet pass"""
        logger.info(f"Handling query for user {user_id}: {query}")
        
        pass_data = self.chat.process_query(query, user_id)
        
        pass_dict = asdict(pass_data)
        pass_dict['user_id'] = user_id
        pass_dict['pass_type'] = pass_data.pass_type.value
        
        pass_id = self.db.add_update_pass_details(user_id, pass_doc=pass_dict)
        logger.info(f"Query pass stored with ID: {pass_id}")
        
        return {
            'pass_id': pass_id,
            'wallet_pass': pass_dict
        }
    
    def generate_insights(self, user_id: str) -> List[Dict[str, Any]]:
        """Generate analytical insights for user"""
        logger.info(f"Generating insights for user {user_id}")
        
        passes = self.analytics.generate_periodic_insights(user_id)
        
        results = []
        for pass_data in passes:
            pass_dict = asdict(pass_data)
            pass_dict['user_id'] = user_id
            pass_dict['pass_type'] = pass_data.pass_type.value
            
            pass_id = self.db.add_update_pass_details(user_id, pass_doc=pass_dict)
            results.append({'pass_id': pass_id, 'wallet_pass': pass_dict})
        
        logger.info(f"Insights generation completed - {len(results)} insights generated")
        return results