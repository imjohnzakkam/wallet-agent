from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.auth import jwt, crypt
import uuid
from typing import List
from datetime import datetime, timedelta

# --- CONFIGURATION ---
SERVICE_ACCOUNT_FILE = 'backend/config/service-account.json'
ISSUER_ID = '3388000000022968883'
PASS_CLASS_ID = f"{ISSUER_ID}.{uuid.uuid4()}"

# Authenticate and create the Wallet service
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=['https://www.googleapis.com/auth/wallet_object.issuer']
)
wallet_service = build('walletobjects', 'v1', credentials=credentials)

def create_shopping_list_pass(items: List[str], title: str = "My Shopping List") -> str:
    """
    Create a Google Wallet shopping list pass from a list of items and return the 'Add to Google Wallet' link.
    
    Args:
        items: A list of strings, where each string is an item on the shopping list.
        title: The title of the shopping list.
    
    Returns:
        str: 'Add to Google Wallet' link
    """
    
    # Ensure title has a default value if it is None or empty
    final_title = title if title else "My Shopping List"

    # --- 1. Create the pass class if needed ---
    
    card_row_template_infos = [
        {
            "twoItems": {
                "startItem": {
                    "firstValue": {
                        "fields": [
                            {"fieldPath": "object.textModulesData['created_date']"}
                        ]
                    }
                },
                "endItem": {
                    "firstValue": {
                        "fields": [
                            {"fieldPath": "object.textModulesData['expired_date']"}
                        ]
                    }
                }
            }
        }
    ]

    for i in range(len(items)):
        card_row_template_infos.append({
            "oneItem": {
                "item": {
                    "firstValue": {
                        "fields": [
                            {"fieldPath": f"object.textModulesData['item_{i}']"}
                        ]
                    }
                }
            }
        })

    generic_class = {
        "id": PASS_CLASS_ID,
        "classTemplateInfo": {
            "cardTemplateOverride": {
                "cardRowTemplateInfos": card_row_template_infos
            }
        }
    }
    try:
        wallet_service.genericclass().insert(body=generic_class).execute()
    except Exception:
        pass  # Class may already exist

    # --- 2. Create the pass object with the shopping list ---
    pass_object_id = f"{ISSUER_ID}.{uuid.uuid4()}"

    created_date = datetime.now()
    expired_date = created_date + timedelta(days=1)
    
    text_modules_data = [
        {"id": "created_date", "header": "Created", "body": created_date.strftime("%Y-%m-%d")},
        {"id": "expired_date", "header": "Expires", "body": expired_date.strftime("%Y-%m-%d")},
    ]

    for i, item in enumerate(items):
        text_modules_data.append(
            {"id": f"item_{i}", "body": item}
        )

    generic_object = {
        "id": pass_object_id,
        "classId": PASS_CLASS_ID,
        "logo": {
            "sourceUri": {
                "uri": "https://storage.googleapis.com/wallet-lab-tools-codelab-artifacts-public/pass_google_logo.jpg"
            }
        },
        "cardTitle": {
            "defaultValue": {
                "language": "en-US",
                "value": "Shopping List"
            }
        },
        "subheader": {
            "defaultValue": {
                "language": "en-US",
                "value": final_title
            }
        },
        "header": {
            "defaultValue": {
                "language": "en-US",
                "value": "Your Items"
            }
        },
        "textModulesData": text_modules_data,
        "hexBackgroundColor": "#4285F4"  # Google Blue
    }
    
    try:
        wallet_service.genericobject().insert(body=generic_object).execute()
    except Exception as e:
        raise RuntimeError(f"Error creating pass object: {e}")

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
