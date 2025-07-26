from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.auth import jwt, crypt
import uuid

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

def create_wallet_receipt(vendor, category, amount, date, time, barcode_value="12345678"):
    """
    Create a Google Wallet receipt pass and return the 'Add to Google Wallet' link.
    """
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

    # --- 2. Create the pass object ---
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
                "value": vendor
            }
        },
        "textModulesData": [
            {"id": "bill_category", "header": "Bill Category", "body": category},
            {"id": "amount", "header": "Amount", "body": amount},
            {"id": "date", "header": "Date", "body": date},
            {"id": "time", "header": "Time", "body": time}
        ],
        "barcode": {
            "type": "QR_CODE",
            "value": barcode_value,
            "alternateText": ""
        },
        "hexBackgroundColor": "#90ee90",
        "heroImage": {
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