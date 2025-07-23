# Wallet Agent AI

A simple, powerful AI Agent for receipt management and spending analysis using Google's Gemini AI.

##  Features

### Core AI Features
1. **OCR Receipt Processing** - Extract structured data from receipt images
2. **AI Chat Assistant** - Natural language queries about spending
3. **Analytics & Insights** - Automated spending analysis and alerts

### Key Benefits
- ✅ **Simple Integration** - Drop-in replacement for backend systems
- ✅ **No Complex Setup** - Just environment variables
- ✅ **Production Ready** - Handles real-world scenarios gracefully
- ✅ **Optional Database** - Works with or without Firestore
- ✅ **Multi-language Support** - Handles receipts in multiple languages

## 📋 Requirements

- Python 3.8+
- Google Gemini API key
- Optional: Google Firestore (for data persistence)

##  Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd cfp_mvp
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
```bash
# Copy environment template
cp .env .env.local

# Edit .env.local with your API key
# GEMINI_API_KEY=your_actual_api_key_here
```

### 4. Create test directories
```bash
mkdir -p data/test_images data/test_results
```

##  Configuration

### Environment Variables (.env.local)

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Firestore Configuration
FIRESTORE_CREDENTIALS_PATH=path/to/firestore-credentials.json
FIRESTORE_PROJECT_ID=your-project-id

# Testing Configuration
TEST_INPUT_DIR=data/test_images
TEST_OUTPUT_DIR=data/test_results
TEST_USER_ID=test_user_123
```

### Getting a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create a new project
3. Generate an API key
4. Add it to your `.env.local` file

##  Testing

### Quick Test
```bash
# Test all features
python test_pipeline.py

# Test specific features
python test_pipeline.py --test ocr --image data/test_images/receipt.jpg
python test_pipeline.py --test chat
python test_pipeline.py --test analytics

# Test with custom API key
python test_pipeline.py --api-key your_api_key_here
```

### Test with Your Own Images
```bash
# Add your receipt images to data/test_images/
cp your_receipt.jpg data/test_images/

# Run OCR test
python test_pipeline.py --test ocr --image data/test_images/your_receipt.jpg
```

## 🔌 Backend Integration

### Simple Integration

```python
from pipeline import RaseedAIPipeline

# Initialize pipeline
pipeline = RaseedAIPipeline(
    gemini_api_key=os.getenv('GEMINI_API_KEY')
)

# Process receipt image
with open("receipt.jpg", "rb") as f:
    result = pipeline.process_receipt(
        media_content=f.read(),
        media_type="image",
        user_id="user123"
    )

# Handle user query
query_result = pipeline.handle_query(
    query="How much did I spend on groceries?",
    user_id="user123"
)

# Generate insights
insights = pipeline.generate_insights(user_id="user123")
```

### API Endpoints (Flask Example)

```python
from flask import Flask, request
from pipeline import RaseedAIPipeline

app = Flask(__name__)
pipeline = RaseedAIPipeline(gemini_api_key=os.getenv('GEMINI_API_KEY'))

@app.post("/receipts/process")
def process_receipt():
    image_data = request.files['image'].read()
    user_id = request.json['user_id']
    
    result = pipeline.process_receipt(
        media_content=image_data,
        media_type="image", 
        user_id=user_id
    )
    
    return result

@app.post("/queries/handle")
def handle_query():
    query = request.json['query']
    user_id = request.json['user_id']
    
    result = pipeline.handle_query(query, user_id)
    return result

@app.get("/insights/generate")
def generate_insights():
    user_id = request.args['user_id']
    insights = pipeline.generate_insights(user_id)
    return insights
```

##  API Reference

### RaseedAIPipeline

Main pipeline class that orchestrates all AI features.

#### Methods

##### `process_receipt(media_content, media_type, user_id)`
Processes receipt images and extracts structured data.

**Parameters:**
- `media_content` (bytes): Image/video data
- `media_type` (str): "image" or "video"
- `user_id` (str): User identifier

**Returns:**
```json
{
  "receipt_id": "receipt_123",
  "receipt_data": {
    "vendor_name": "BigBasket",
    "category": "grocery",
    "amount": 657.30,
    "items": [...],
    "date_time": "2024-11-15T14:30:00"
  },
  "wallet_pass": {
    "pass_type": "receipt",
    "title": "BigBasket",
    "subtitle": "Nov 15, 2024 - ₹657.30",
    "details": {...}
  }
}
```

##### `handle_query(query, user_id)`
Processes natural language queries about spending.

**Parameters:**
- `query` (str): Natural language query
- `user_id` (str): User identifier

**Returns:**
```json
{
  "pass_id": "pass_456",
  "wallet_pass": {
    "pass_type": "analytics|shopping_list|receipt",
    "title": "Query Response",
    "subtitle": "Summary",
    "details": {...}
  }
}
```

##### `generate_insights(user_id)`
Generates spending insights and analytics.

**Parameters:**
- `user_id` (str): User identifier

**Returns:**
```json
[
  {
    "pass_id": "insight_789",
    "wallet_pass": {
      "pass_type": "analytics|alert",
      "title": "Monthly Summary",
      "subtitle": "₹12,450 ↑15.3%",
      "details": {...}
    }
  }
]
```

##  Architecture

### Core Components

1. **ReceiptOCRPipeline** - Handles image processing and data extraction
2. **ReceiptChatAssistant** - Processes natural language queries
3. **ReceiptAnalysisPipeline** - Generates insights and analytics
4. **RaseedAIPipeline** - Main orchestrator class

### Data Models

- `Receipt` - Structured receipt data
- `ReceiptItem` - Individual items in receipts
- `WalletPass` - Response format for all features
- `ReceiptCategory` - Spending categories
- `PassType` - Types of responses

## 🎯 Use Cases

### 1. Receipt Digitization
```python
# Extract data from receipt images
result = pipeline.process_receipt(image_data, "image", user_id)
# Returns: vendor, amount, items, date, category, etc.
```

### 2. Spending Queries
```python
# Natural language questions
result = pipeline.handle_query("How much did I spend on groceries?", user_id)
result = pipeline.handle_query("Show my BigBasket receipts", user_id)
result = pipeline.handle_query("Create shopping list for biryani", user_id)
```

### 3. Automated Insights
```python
# Generate spending insights
insights = pipeline.generate_insights(user_id)
# Returns: monthly summaries, alerts, savings suggestions
```

## 🔒 Security

- API keys are stored in environment variables
- No sensitive data in code
- Optional Firestore integration for data persistence
- Graceful error handling for API failures

## 🚨 Error Handling

The pipeline handles errors gracefully:

- **API Quota Exceeded** - Returns fallback responses
- **Invalid Images** - Returns error information
- **Network Issues** - Retries with exponential backoff
- **Missing Data** - Uses reasonable defaults

## 📈 Performance

- **OCR Processing**: ~2-5 seconds per image
- **Query Processing**: ~1-3 seconds per query
- **Insights Generation**: ~1-2 seconds
- **Memory Usage**: ~50-100MB per process

## 🔧 Troubleshooting

### Common Issues

1. **API Key Error**
   ```
   Error: No API key provided
   ```
   **Solution**: Set `GEMINI_API_KEY` in `.env.local`

2. **Image Processing Error**
   ```
   OCR extraction error: 429 You exceeded your current quota
   ```
   **Solution**: Check API quota or upgrade plan

3. **Import Error**
   ```
   ImportError: cannot import name 'RaseedAIPipeline'
   ```
   **Solution**: Ensure `pipeline.py` is in the same directory

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Test individual components
from pipeline import ReceiptOCRPipeline
ocr = ReceiptOCRPipeline(api_key)
result = ocr.extract_receipt_data(image_data, "image")
```

## 📊 Logging and Test Results

### Logging
The pipeline automatically logs all operations to the `logs/` directory:

- **Daily log files**: `logs/raseed_pipeline_YYYYMMDD.log`
- **Test run logs**: `logs/test_run_YYYYMMDD_HHMMSS.log`
- **Console output**: Real-time logging to terminal

### Test Results
Comprehensive test reports are generated in `data/test_results/`:

- **Report format**: `pipeline_test_report_YYYYMMDD_HHMMSS.json`
- **Includes**: Test summaries, timing, success rates, detailed results
- **Structure**: Matches existing test result format

### Log Levels
- **INFO**: General operations and successful completions
- **DEBUG**: Detailed processing information
- **WARNING**: Non-critical issues
- **ERROR**: Critical failures and exceptions

### Example Test Report
```json
{
  "summary": {
    "test_run_id": "20241115_143022",
    "total_tests": 3,
    "successful_tests": 3,
    "failed_tests": 0,
    "success_rate": 100.0,
    "test_types": ["ocr", "chat", "analytics"],
    "total_processing_time": 8.45,
    "timestamp": "2024-11-15T14:30:22.123456"
  },
  "test_results": [
    {
      "test_type": "ocr",
      "image_path": "data/test_images/receipt.jpg",
      "success": true,
      "processing_time": 3.2,
      "result": {...}
    }
  ]
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the API documentation

##  Version History

- **v1.0.0** - Initial release with core features
- OCR receipt processing
- AI chat assistant
- Analytics pipeline
- Simple testing framework

---

**Built with ❤️ using Google Gemini AI**
