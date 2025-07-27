from google.oauth2 import service_account
from googleapiclient.discovery import build
import uuid
import os
from google.auth import jwt, crypt

# --- CONFIGURATION ---
SERVICE_ACCOUNT_FILE = 'backend/config/service-account.json'
ISSUER_ID = os.getenv("ISSUER_ID", "3388000000022968883")
PASS_CLASS_ID_INSIGHTS = f"{ISSUER_ID}.insights-class-g"
SAVE_URL_BASE = "https://pay.google.com/gp/v/save/"

# Authenticate and create the Wallet service
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=['https://www.googleapis.com/auth/wallet_object.issuer']
)
wallet_service = build('walletobjects', 'v1', credentials=credentials)

def create_insights_pass(insights_data: dict):
    """
    Creates a Google Wallet pass for spending insights.
    """
    total_spending = insights_data.get('total_spending', 0.0)
    top_categories = insights_data.get('top_categories', [])
    plot_url = insights_data.get('spending_chart_url', '')

    # Define the pass class
    pass_class = {
        "id": PASS_CLASS_ID_INSIGHTS,
        "classTemplateInfo": {
            "cardTemplateOverride": {
                "cardRowTemplateInfos": [
                    {
                        "twoItems": {
                            "startItem": {
                                "firstValue": {
                                    "fields": [
                                        {"fieldPath": "object.textModulesData['cat1_label']"}
                                    ]
                                }
                            },
                            "endItem": {
                                "firstValue": {
                                    "fields": [
                                        {"fieldPath": "object.textModulesData['cat1_amount']"}
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
                                        {"fieldPath":  "object.textModulesData['cat2_label']"}
                                    ]
                                }
                            },
                            "endItem": {
                                "firstValue": {
                                    "fields": [
                                        {"fieldPath": "object.textModulesData['cat2_amount']"}
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
                                        {"fieldPath":  "object.textModulesData['cat3_label']"}
                                    ]
                                }
                            },
                            "endItem": {
                                "firstValue": {
                                    "fields": [
                                        {"fieldPath": "object.textModulesData['cat3_amount']"}
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
    }

    # Create or update the pass class
    try:
        wallet_service.genericclass().insert(body=pass_class).execute()
    except Exception as e:
        if "already exists" not in str(e):
            raise e

    # Define the pass object
    pass_object = {
        "id": f"{ISSUER_ID}.{uuid.uuid4()}",
        "classId": PASS_CLASS_ID_INSIGHTS,
        "state": "ACTIVE",
        "heroImage": {
            "sourceUri": {
                "uri": plot_url
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
                "value": f"{insights_data.get('month','')} Insights"
            }
        },
        "header": {
            "defaultValue": {
                "language": "en-US",
                "value": f"Total Spent: ₹{total_spending:.2f}"
            }
        },
        "textModulesData": [
            {"id": "cat1_label", "header": "Top Category", "body": f"{top_categories[0]['category']}" if len(top_categories) > 0 else ""},
            {"id": "cat1_amount", "header": "Amount", "body": f"₹{top_categories[0]['amount']}" if len(top_categories) > 0 else ""},
            {"id": "cat2_label", "header": "Second Category", "body": f"{top_categories[1]['category']}" if len(top_categories) > 1 else ""},
            {"id": "cat2_amount", "header": "Amount", "body": f"₹{top_categories[1]['amount']}" if len(top_categories) > 1 else ""},
            {"id": "cat3_label", "header": "Third Category", "body": f"{top_categories[2]['category']}" if len(top_categories) > 2 else ""},
            {"id": "cat3_amount", "header": "Amount", "body": f"₹{top_categories[2]['amount']}" if len(top_categories) > 2 else ""}
        ]
    }
    
    pass_object["hexBackgroundColor"] = "#87ceeb"

    # Generate the JWT for the save link
    claims = {
        'iss': credentials.service_account_email,
        'aud': 'google',
        'origins': ['www.example.com'],  # Update with your domain
        'typ': 'savetowallet',
        'payload': {
            'genericObjects': [pass_object]
        }
    }
    
    signer = crypt.RSASigner.from_service_account_file(SERVICE_ACCOUNT_FILE)
    token = jwt.encode(signer, claims).decode('utf-8')
    
    save_url = f"{SAVE_URL_BASE}{token}"
    return save_url 