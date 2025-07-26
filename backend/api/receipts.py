from dotenv.main import logger
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.auth import jwt, crypt
import uuid
from datetime import datetime
from typing import List, Optional

# Import Receipt dataclass from ai_pipeline
from ai_pipeline.pipeline import Receipt, ReceiptItem

# --- CONFIGURATION ---
SERVICE_ACCOUNT_FILE = 'backend/config/service-account.json'
ISSUER_ID = '3388000000022968883'
PASS_CLASS_ID = f"{ISSUER_ID}.9937af69-6694-4681-a557-7fa3b4a09c70"

# Authenticate and create the Wallet service
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=['https://www.googleapis.com/auth/wallet_object.issuer']
)
wallet_service = build('walletobjects', 'v1', credentials=credentials)

def create_wallet_receipt(receipt: Receipt) -> str:
    """
    Create a Google Wallet receipt pass from a Receipt POJO and return the 'Add to Google Wallet' link.
    
    Args:
        receipt: Receipt dataclass object containing all receipt information
        barcode_value: Optional barcode value, defaults to receipt ID if not provided
    
    Returns:
        str: 'Add to Google Wallet' link
    """
    # Format date and time
    date_str = receipt.date_time.strftime('%Y-%m-%d')
    time_str = receipt.date_time.strftime('%H:%M')
    
    # Format currency amount
    currency_symbol = "₹" if receipt.currency == "INR" else "$" if receipt.currency == "USD" else receipt.currency
    amount_str = f"{currency_symbol}{receipt.amount:.2f}"
    subtotal_str = f"{currency_symbol}{receipt.subtotal:.2f}"
    tax_str = f"{currency_symbol}{receipt.tax:.2f}"
    
    # Format items list (limit to first 5 items for display)
    items_text = ""
    if receipt.items:
        items_list = []
        for item in receipt.items[:5]:  # Limit to first 5 items
            item_text = f"{item.name} ({item.quantity}{item.unit}) - {currency_symbol}{item.price:.2f}"
            items_list.append(item_text)
        items_text = "; ".join(items_list)
        if len(receipt.items) > 5:
            items_text += f"; +{len(receipt.items) - 5} more items"
    
    # --- 1. Create the pass class if needed ---
    generic_class = {
        "id": PASS_CLASS_ID,
        "classTemplateInfo": {
            "cardTemplateOverride": {
                "cardRowTemplateInfos": [
                    {
                        "twoItems": {
                            "startItem": {
                                "firstValue": {
                                    "fields": [
                                        {"fieldPath": "object.textModulesData['bill_category']"}
                                    ]
                                }
                            },
                            "endItem": {
                                "firstValue": {
                                    "fields": [
                                        {"fieldPath": "object.textModulesData['amount']"}
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "twoItems": {
                            "startItem": {
                                "firstValue": {
                                    "fields": [
                                        {"fieldPath": "object.textModulesData['date']"}
                                    ]
                                }
                            },
                            "endItem": {
                                "firstValue": {
                                    "fields": [
                                        {"fieldPath": "object.textModulesData['time']"}
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
    }
    try:
        wallet_service.genericclass().insert(body=generic_class).execute()
    except Exception:
        pass  # Class may already exist

    # print(receipt)
    # --- 2. Create the pass object with comprehensive data ---
    pass_object_id = f"{ISSUER_ID}.{uuid.uuid4()}"
    generic_object = {
        "id": pass_object_id,
        "classId": PASS_CLASS_ID,
        "logo": {
            "sourceUri": {
                "uri": "https://storage.googleapis.com/wallet-lab-tools-codelab-artifacts-public/pass_google_logo.jpg"
            },
            "contentDescription": {
                "defaultValue": {
                    "language": "en-US",
                    "value": "LOGO_IMAGE_DESCRIPTION"
                }
            }
        },
        "cardTitle": {
            "defaultValue": {
                "language": "en-US",
                "value": "Project Raseed"
            }
        },
        "subheader": {
            "defaultValue": {
                "language": "en-US",
                "value": "Vendor"
            }
        },
        "header": {
            "defaultValue": {
                "language": "en-US",
                "value": receipt.vendor_name
            }
        },
        "textModulesData": [
            {"id": "bill_category", "header": "Category", "body": receipt.category.value.title()},
            {"id": "amount", "header": "Total Amount", "body": amount_str},
            {"id": "date", "header": "Date", "body": date_str},
            {"id": "time", "header": "Time", "body": time_str},
            {"id": "subtotal", "header": "Subtotal", "body": subtotal_str},
            {"id": "tax", "header": "Tax", "body": tax_str},
            {"id": "currency", "header": "Currency", "body": receipt.currency},
            {"id": "payment_method", "header": "Payment Method", "body": receipt.payment_method or "Not specified"},
            {"id": "language", "header": "Receipt Language", "body": receipt.language.upper()},
            {"id": "items_count", "header": "Items Count", "body": str(len(receipt.items))},
        ]
    }
    
    # Add items list if available
    if items_text:
        generic_object["textModulesData"].append(
            {"id": "items", "header": "Items", "body": items_text}
        )
    
    # Set background color based on category
    category_colors = {
        "grocery": "#90ee90",      # Light green
        "restaurant": "#ffb6c1",   # Light pink
        "shopping": "#87ceeb",     # Light blue
        "fuel": "#ffd700",         # Gold
        "pharmacy": "#dda0dd",     # Plum
        "electronics": "#f0e68c",  # Khaki
        "utilities": "#98fb98",    # Pale green
        "other": "#d3d3d3"         # Light gray
    }
    
    generic_object["hexBackgroundColor"] = category_colors.get(receipt.category.value, "#90ee90")
    
    # Add hero image
    generic_object["heroImage"] = {
        "sourceUri": {
            "uri": "https://drive.google.com/uc?export=download&id=1Ay-ssjh6eGV6DMlo9rWJM_oztGRlOoOV"
        },
        "contentDescription": {
            "defaultValue": {
                "language": "en-US",
                "value": "HERO_IMAGE_DESCRIPTION"
            }
        }
    }
    
    try:
        wallet_service.genericobject().insert(body=generic_object).execute()
    except Exception as e:
        logger.info("Error creating pass object",e,exc_info=True)
        raise RuntimeError(f"Error creating pass object: {e}", (e))

    # --- 3. Generate the 'Add to Google Wallet' link ---
    claims = {
        'iss': credentials.service_account_email,
        'aud': 'google',
        'origins': ['www.example.com'],
        'typ': 'savetowallet',
        'payload': {
            'genericClasses': [generic_class],
            'genericObjects': [generic_object]
        }
    }
    signer = crypt.RSASigner.from_service_account_file(SERVICE_ACCOUNT_FILE)
    token = jwt.encode(signer, claims).decode('utf-8')
    wallet_link = f'https://pay.google.com/gp/v/save/{token}'
    return wallet_link 