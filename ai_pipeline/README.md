# Wallet Agent AI Pipeline

This directory contains the core AI pipeline for the  application. The pipeline is responsible for processing receipts, enabling chat-based financial queries, and generating automated spending insights.

## Overview

The pipeline is built using Google's Gemini models and is designed to be modular and extensible. It integrates OCR capabilities, a natural language chat assistant, and an analytics engine to provide users with a comprehensive overview of their spending.

## Core Features

- **Receipt OCR**: Extracts structured data (vendor, amount, items, etc.) from receipt images and videos using the `gemini-1.5-flash` vision model.
- **AI Chat Assistant**: Allows users to query their spending data using natural language. The assistant can classify user intent and provide relevant information, such as spending summaries or specific receipt details.
- **Automated Analytics**: Periodically generates insights and alerts based on user spending patterns, such as monthly summaries or high-spending warnings.
- **Wallet Pass System**: Creates standardized "wallet pass" objects for receipts, queries, and insights, which can be easily used by frontend applications.
- **Database Integration**: Optionally integrates with Google Cloud Firestore to store and retrieve receipt and user data.

## Architecture

The pipeline consists of three main components, orchestrated by a primary integration class.

-   **`AIPipeline`**: The main class that initializes and coordinates the other components. It provides the primary interface for processing receipts, handling queries, and generating insights.

-   **`ReceiptOCRPipeline`**: This component is responsible for all OCR-related tasks. It takes raw media content (images/videos) of receipts and uses a multimodal LLM to extract structured JSON data.

-   **`ReceiptChatAssistant`**: This component powers the chat functionality. It classifies the user's query intent and routes it to the appropriate handler to generate a response, such as a spending analysis or a shopping list.

-   **`ReceiptAnalysisPipeline`**: This component handles the generation of periodic, automated insights. It can create monthly spending summaries, alerts for unusual activity, and other proactive financial tips.

### Data Models

The pipeline uses several `dataclasses` to ensure data consistency:

-   `Receipt`: A structured representation of a processed receipt.
-   `ReceiptItem`: Represents a single item within a receipt.
-   `WalletPass`: A generic object used to pass data back to the application. It can represent a receipt, an analytical insight, an alert, or a shopping list.

## Usage

### Prerequisites

-   Python 3.8+
-   Google Gemini API Key
-   (Optional) Google Cloud Firestore service account credentials.

### Initialization

First, initialize the main pipeline class with your Gemini API key and optional Firestore credentials.

```python
from ai_pipeline.pipeline import AIPipeline

# Initialize the pipeline
api_key = "YOUR_GEMINI_API_KEY"
firestore_creds_path = "path/to/your/firestore-credentials.json" # Optional

pipeline = AIPipeline(
    gemini_api_key=api_key,
    firestore_credentials=firestore_creds_path
)
```

### Processing a Receipt

To process a receipt, provide the media content (as bytes) and the user ID.

```python
# Read an image file
with open("path/to/receipt.jpg", "rb") as f:
    image_bytes = f.read()

# Process the receipt
user_id = "user-123"
result = pipeline.process_receipt(
    media_content=image_bytes,
    media_type="image",
    user_id=user_id
)

print(result)
```

### Handling a User Query

To handle a text-based query from a user, use the `handle_query` method.

```python
user_id = "user-123"
query = "How much did I spend on groceries last week?"

result = pipeline.handle_query(query=query, user_id=user_id)
print(result)
```

### Generating Insights

To generate periodic insights for a user, call the `generate_insights` method.

```python
user_id = "user-123"
insights = pipeline.generate_insights(user_id=user_id)

for insight in insights:
    print(insight)
```

## Testing

Unit tests and integration tests for the pipeline can be found in `test_pipeline.py`. 