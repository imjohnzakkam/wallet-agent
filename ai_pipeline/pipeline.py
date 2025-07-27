# Core Features: OCR, Chat Assistant, Analytics

import json
import re
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from google.auth import credentials
import vertexai
from vertexai.generative_models import (
    Content,
    FunctionDeclaration,
    GenerationConfig,
    GenerativeModel,
    Part,
    Tool,
)
from pathlib import Path
import matplotlib.pyplot as plt
from collections import Counter
from google.cloud import storage

from backend.firestudio.firebase import FirebaseClient
from ai_pipeline import analysis_tools
from ai_pipeline.search_tools import WebSearchTool
from ai_pipeline.create_shopping_wallet_tool import create_shopping_list_pass

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
    OTHER = "other"

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
            language=data.get('language', 'en')
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
    def __init__(self, project_id: str, location: str, firebase_client: FirebaseClient, web_search_tool: WebSearchTool = None):
        logger.info("Initializing ReceiptOCRPipeline with Vertex AI")
        self.model = GenerativeModel('gemini-2.5-pro')
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
    def __init__(self, project_id: str, location: str, firebase_client: FirebaseClient, web_search_tool: WebSearchTool = None):
        logger.info("Initializing ReceiptChatAssistant")
        self.shopping_list_model = GenerativeModel('gemini-2.0-flash')
        self.db_client = firebase_client
        self.generation_config = GenerationConfig(temperature=0)

        # Create system instruction
        system_instruction = f"""You are a helpful financial assistant for the Wallet Agent app called Raseed.
You help users analyze their spending patterns, track expenses, and make better financial decisions.

## Data Structures You Work With:

### Receipt Categories:
The receipts are categorized into the following types:
- GROCERY: "grocery" - Supermarkets, food stores, vegetable vendors
- RESTAURANT: "restaurant" - Dining out, food delivery, cafes
- SHOPPING: "shopping" - Clothing, accessories, general retail
- FUEL: "fuel" - Petrol, diesel, gas stations
- PHARMACY: "pharmacy" - Medical stores, drug stores
- ELECTRONICS: "electronics" - Electronic goods, gadgets, appliances
- UTILITIES: "utilities" - Subscriptions, bills, recurring services
- OTHER: "other" - Anything that doesn't fit above categories

### Receipt Structure:
Each receipt contains:
- vendor_name: Name of the store/restaurant
- category: One of the categories above
- date_time: When the purchase was made
- amount: Total amount paid
- items: List of purchased items (each with name, quantity, unit, price, category)
- subtotal: Amount before tax
- tax: Tax amount
- payment_method: How the payment was made (cash/card/upi/other)
- currency: Currency code (default: INR)
- language: Language of the receipt

### Pass Types:
Your responses can be categorized as:
- RECEIPT: "receipt" - For receipt-related information
- SHOPPING_LIST: "shopping_list" - For shopping lists and purchase planning
- ANALYTICS: "analytics" - For spending analysis and insights
- ALERT: "alert" - For warnings and notifications
- OTHER: "other" - General responses

## Key Instructions:
- All currencies are in INR (Indian Rupees)
- Today's date is {datetime.now().strftime('%Y-%m-%d')}
- Use the available tools to answer user queries accurately
- For any date range queries, use the _fetch_receipts_all_categories tool to get comprehensive data
- Be concise but informative in your responses
- Always provide specific numbers and data when available
- When analyzing spending, consider the receipt categories to provide category-wise insights
- Understand that items within receipts also have categories (like "dairy", "vegetables", "meat" for grocery items)
- If you need to calculate or analyze spending patterns, use the appropriate analysis tools
- Never ask follow-up questions; instead, make reasonable assumptions and provide a complete answer
- Focus on being helpful and actionable in your responses

## Understanding Receipt Data:
- Grocery receipts often contain items with sub-categories like dairy, vegetables, fruits, grains, household items
- Restaurant receipts may include food, beverages, and service charges
- Utility receipts typically represent recurring subscriptions (Netflix, Amazon Prime, etc.)
- Use this understanding to provide more detailed insights when analyzing spending

Remember: You have access to the user's complete receipt history and various analysis tools. Use them effectively to provide accurate, data-driven insights based on the structured data format described above."""

        # Initialize model with system instruction
        self.model = GenerativeModel(
            'gemini-2.0-flash',
            system_instruction=system_instruction
        )
        self.web_search_tool = web_search_tool

        # --- Vertex AI Tool Calling Setup ---
        
        self.function_declarations = [
            FunctionDeclaration.from_func(tool) for tool in analysis_tools.all_tool_calls.values()
        ]
        self.function_declarations.append(FunctionDeclaration.from_func(self.web_search_tool.search))
        
        self.tool = Tool(
            function_declarations=self.function_declarations
        )

        self.shopping_list_tool = Tool(
            function_declarations=[
                FunctionDeclaration.from_func(create_shopping_list_pass)
            ]
        )
        # --- End of Tool Setup ---

        self.toolbox = analysis_tools.all_tool_calls
        self.toolbox['search'] = self.web_search_tool.search
        logger.info("ReceiptChatAssistant initialized with system prompt")

        self.shopping_list_toolbox = {
            "create_shopping_list_pass": create_shopping_list_pass
        }

    def process_query(self, query: str, user_id: str) -> WalletPass:
        """
        Processes a user query using the Vertex AI tool-calling feature by manually
        managing conversation history.
        """
        logger.info(f"Handling query for user {user_id} with Vertex AI tools: '{query}'")

        # Manually manage conversation history - now without the system message
        history = [
            Content(role="user", parts=[Part.from_text(f"User ID: {user_id}\n\nQuery: {query}")])
        ]
        
        execution_results = []

        # Loop to handle multi-turn tool calls
        for _ in range(5): # Max 5 turns to prevent infinite loops
            
            response = self.model.generate_content(
                history,
                tools=[self.tool],
                generation_config=self.generation_config
            )

            # After generating content, check for function calls
            if not response.candidates or not response.candidates[0].content.parts or not response.candidates[0].content.parts[0].function_call:
                # If no function call, we have the final text response
                break

            # Add the model's request to the history
            history.append(response.candidates[0].content)
            
            # Prepare a list of tool responses
            tool_responses = []

            for part in response.candidates[0].content.parts:
                if not part.function_call:
                    continue

                function_call = part.function_call
                tool_name = function_call.name
                tool_func = self.toolbox.get(tool_name)

                if not tool_func:
                    logger.error(f"Tool '{tool_name}' not found.")
                    tool_responses.append(Part.from_function_response(
                        name=tool_name,
                        response={"error": f"Tool '{tool_name}' not found."}
                    ))
                    continue
                
                try:
                    args = dict(function_call.args)
                    # Inject user_id dependency
                    args["user_id"] = user_id
                    
                    result = tool_func(**args)
                    
                    log_args = {k: v for k, v in args.items() if k not in ['user_id']}
                    execution_results.append({"tool": tool_name, "args": log_args, "result": result})
                    logger.info(f"Executed tool '{tool_name}' with args {log_args}. Result: {result}")

                    tool_responses.append(Part.from_function_response(
                        name=tool_name,
                        response={"content": json.dumps(result, default=str)}
                    ))
                except Exception as e:
                    logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
                    tool_responses.append(Part.from_function_response(
                        name=tool_name,
                        response={"error": str(e)}
                    ))
            
            # Add the tool execution results to the history
            history.append(Content(role="tool", parts=tool_responses))


        final_response_text = response.text if response.candidates else "No response from model."
        logger.info(f"Final synthesized response: {final_response_text}")
        
        shopping_list_prompt = f"""
        Based on the following user request and assistant response, determine if a shopping list should be created.
        If so, call the `create_shopping_list_pass` function with the extracted items.
        If a shopping list is not explicitly requested or implied, do not call any function.

        User Request: "{query}"
        Assistant Response: "{final_response_text}"
        """
        # print(query)
        shopping_list_response = self.shopping_list_model.generate_content(
            [shopping_list_prompt],
            tools=[self.shopping_list_tool]
        )
        # print(shopping_list_response)
        # print(final_response_text)
        # print(shopping_list_response.text)
        if shopping_list_response.candidates and shopping_list_response.candidates[0].content.parts and shopping_list_response.candidates[0].content.parts[0].function_call:
            function_call = shopping_list_response.candidates[0].content.parts[0].function_call
            tool_name = function_call.name
            
            if tool_name == "create_shopping_list_pass":
                logger.info(f"Shopping list tool called: {tool_name}")
                tool_func = self.shopping_list_toolbox.get(tool_name)
                if tool_func:
                    try:
                        args = dict(function_call.args)
                        shopping_list_data = tool_func(**args)
                        
                        # logger.info(f"Created shopping list: {shopping_list_data}")
                        
                        shopping_list_data['response'] = final_response_text
                        return WalletPass(
                            pass_type=PassType.SHOPPING_LIST,
                            title="Your Shopping List",
                            subtitle=f"Created from your request",
                            details=shopping_list_data
                        )
                    except Exception as e:
                        logger.error(f"Error executing shopping list tool: {e}", exc_info=True)
        
        logger.info("No shopping list created. Returning original response.")

        return WalletPass(
            pass_type=PassType.OTHER,
            title="Your Agent's Answer",
            subtitle=query,
            details={"response": final_response_text, "execution_results": execution_results}
        )
    
    def _determine_pass_type(self, query: str, execution_results: List[Dict]) -> PassType:
        """Determine the appropriate pass type based on query and results"""
        query_lower = query.lower()
        
        # Check for shopping list queries
        if any(keyword in query_lower for keyword in ['shopping list', 'need to buy', 'grocery list', 'items to purchase']):
            return PassType.SHOPPING_LIST
        
        # Check for analytics queries
        if any(keyword in query_lower for keyword in ['analysis', 'analyze', 'spending pattern', 'trend', 'breakdown', 'summary', 'insights']):
            return PassType.ANALYTICS
        
        # Check for alerts
        if any(keyword in query_lower for keyword in ['alert', 'warning', 'unusual', 'overspending', 'budget exceeded']):
            return PassType.ALERT
        
        # Check execution results for more context
        if execution_results:
            tool_names = [result['tool'] for result in execution_results]
            
            if 'suggest_shopping_list' in tool_names or 'create_shopping_list_pass' in tool_names:
                return PassType.SHOPPING_LIST
            
            if any('analysis' in tool or 'insight' in tool or 'trend' in tool for tool in tool_names):
                return PassType.ANALYTICS
            
            if any('alert' in tool or 'unusual' in tool for tool in tool_names):
                return PassType.ALERT
        
        # Default to OTHER
        return PassType.OTHER
    
    def _generate_title(self, pass_type: PassType, query: str, execution_results: List[Dict]) -> str:
        """Generate an appropriate title based on pass type"""
        if pass_type == PassType.SHOPPING_LIST:
            return "Shopping List"
        elif pass_type == PassType.ANALYTICS:
            return "Spending Analysis"
        elif pass_type == PassType.ALERT:
            return "Financial Alert"
        else:
            return "Raseed's Response"
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from text"""
        json_match = re.search(r'\{[\s\S]*\}', text)
        return json_match.group(0) if json_match else "{}"

# 3. Analysis Pipeline Component
class ReceiptAnalysisPipeline:
    def __init__(self, db_client: FirebaseClient, project_id: str = None, location: str = None):
        logger.info("Initializing ReceiptAnalysisPipeline")
        self.db = db_client
        self.storage_client = storage.Client(
            project=project_id,
            credentials=db_client.google_cloud_creds
        )
        logger.info("ReceiptAnalysisPipeline initialized successfully")
        
    def generate_periodic_insights(self, user_id: str) -> List[dict[str,Any]]:
        """
        Generate periodic insights by analyzing monthly spending, creating a histogram,
        and identifying top spending categories.
        """
        logger.info(f"Generating insights for user {user_id}")
        
        # 1. Fetch current month's receipts
        now = datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        receipt_docs = self.db.get_receipts_by_timerange(user_id, start_of_month, now)
        receipts = [Receipt.from_dict(doc) for doc in receipt_docs]
        
        if not receipts:
            return [WalletPass(pass_type=PassType.ANALYTICS, title="Monthly Summary", subtitle="No receipts found for this month.", details={})]

        # 2. Aggregate spending by category
        spending_by_category = Counter()
        for receipt in receipts:
            spending_by_category[receipt.category.value] += receipt.amount
            
        # 3. Get top 3 spending categories
        top_3_categories = spending_by_category.most_common(3)
        
        # 4. Generate histogram plot
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(12, 7), facecolor='#1E1E1E')
        
        categories = list(spending_by_category.keys())
        amounts = list(spending_by_category.values())
        
        bars = ax.bar(categories, amounts, color='#4CAF50')
        
        ax.set_title(f'Monthly Spending for {now.strftime("%B %Y")}', fontsize=20, color='white')
        ax.set_ylabel('Amount (INR)', fontsize=14, color='white')
        ax.set_xlabel('Category', fontsize=14, color='white')
        ax.tick_params(axis='x', colors='white', rotation=45)
        ax.tick_params(axis='y', colors='white')
        ax.grid(axis='y', linestyle='--', alpha=0.6)
        
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.2f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=10, color='white')

        plot_filename = f"/tmp/insights_{user_id}_{now.strftime('%Y%m')}.png"
        plt.savefig(plot_filename, facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close()
        
        # 5. Upload plot to GCS
        gcs_bucket_name = os.getenv("GCS_BUCKET_NAME", "wallet-agent")
        plot_url = ""
        if gcs_bucket_name:
            blob_name = f"insights/{user_id}/spending_{now.strftime('%Y%m')}.png"
            try:
                bucket = self.storage_client.bucket(gcs_bucket_name)
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(plot_filename)

                # Generate a signed URL for the blob, valid for 15 minutes
                plot_url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(minutes=15),
                    method="GET",
                )
                # logger.info(f"Generated signed URL for plot: {plot_url}")
            except Exception as e:
                logger.error(f"Failed to upload plot or generate signed URL: {e}", exc_info=True)
        else:
            logger.error("GCS_BUCKET_NAME environment variable not set. Skipping plot upload.")

        # 6. Create WalletPass with insights
        return [
            {
            "top_categories": [{"category": cat, "amount": f"{amt:.2f}"} for cat, amt in top_3_categories],
            "spending_chart_url": plot_url,
            "total_spending": sum(amounts),
            "month": now.strftime("%B %Y")
            }
        ]

# Main Integration Class
class AIPipeline:
    def __init__(self, project_id: str, location: str, firebase_client: FirebaseClient):
        logger.info("Initializing AIPipeline")
        
        # Centralized Vertex AI initialization with the correct credentials
        credentials = firebase_client.google_cloud_creds
        vertexai.init(project=project_id, location=location, credentials=credentials)
        scoped_credentials = firebase_client.google_cloud_creds
        if credentials:
            # Re-scope credentials to ensure they have cloud-platform access.
            # This is necessary for services like Vertex AI.
            try:
                scoped_credentials = credentials.with_scopes([
                    "https://www.googleapis.com/auth/cloud-platform"
                ])
            except AttributeError:
                logger.warning("Credentials object does not support re-scoping. Proceeding with original credentials.")
        self.db = firebase_client
        self.ocr = ReceiptOCRPipeline(project_id, location, firebase_client)
        self.web_search = WebSearchTool(project_id, location, scoped_credentials)
        self.chat = ReceiptChatAssistant(project_id, location, self.db, self.web_search)
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
    
    def generate_insights(self, user_id: str) -> Dict[str, Any]:
        """Generate analytical insights and return the details."""
        logger.info(f"Generating insights for user {user_id}")
        
        return self.analytics.generate_periodic_insights(user_id)