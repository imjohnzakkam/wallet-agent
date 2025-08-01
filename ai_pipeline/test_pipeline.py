#!/usr/bin/env python3
"""
Simple Test Pipeline for Wallet AI
Tests the 3 core features: OCR, Chat Assistant, Analytics
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Load environment variables
def load_env():
    """Load environment variables from .env file"""
    env_vars = {}
    
    # Try to load from .env file
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    
    # Override with system environment variables
    for key in ['FIRESTORE_CREDENTIALS_PATH', 'FIRESTORE_PROJECT_ID']:
        if key in os.environ:
            env_vars[key] = os.environ[key]
    
    return env_vars

def setup_test_logging():
    """Setup logging for test runs"""
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Create test results directory
    Path("data/test_results").mkdir(parents=True, exist_ok=True)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'logs/test_run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def test_ocr_feature(pipeline, image_path: str, user_id: str, logger):
    """Test OCR feature"""
    logger.info(f"Starting OCR test with image: {image_path}")
    
    print(f"\n{'='*50}")
    print("TESTING OCR FEATURE")
    print(f"{'='*50}")
    
    if not os.path.exists(image_path):
        error_msg = f"Image file not found at {image_path}"
        logger.error(error_msg)
        print(f"Error: {error_msg}")
        return None
    
    # Read image
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    print(f"Processing image: {image_path}")
    print(f"Image size: {len(image_data)} bytes")
    logger.info(f"Image loaded: {len(image_data)} bytes")
    
    # Process receipt
    start_time = datetime.now()
    result = pipeline.process_receipt(image_data, "image", user_id)
    processing_time = (datetime.now() - start_time).total_seconds()
    
    # Display results
    receipt_data = result['receipt_data']
    wallet_pass = result['wallet_pass']
    
    print(f"\nReceipt ID: {result['receipt_id']}")
    print(f"Vendor: {receipt_data['vendor_name']}")
    print(f"Category: {receipt_data['category']}")
    print(f"Date: {receipt_data['date_time']}")
    print(f"Amount: ₹{receipt_data['amount']:.2f}")
    print(f"Items: {len(receipt_data['items'])}")
    print(f"Processing time: {processing_time:.2f} seconds")
    
    # Display items
    if receipt_data['items']:
        print(f"\nItems:")
        for i, item in enumerate(receipt_data['items'], 1):
            print(f"  {i}. {item['name']} - {item['quantity']} {item['unit']} - ₹{item['price']:.2f}")
    else:
        print(f"\nNo items extracted")
    
    # Log results
    logger.info(f"OCR test completed - Vendor: {receipt_data['vendor_name']}, Amount: ₹{receipt_data['amount']:.2f}, Processing time: {processing_time:.2f}s")
    
    return {
        'test_type': 'ocr',
        'image_path': image_path,
        'success': True,
        'result': result,
        'processing_time': processing_time,
        'timestamp': datetime.now().isoformat()
    }

def test_chat_feature(pipeline, user_id: str, logger):
    """Test Chat Assistant feature"""
    logger.info("Starting Chat Assistant test")
    
    print(f"\n{'='*50}")
    print("TESTING CHAT ASSISTANT")
    print(f"{'='*50}")
    
    test_queries = [
        "How much did I spend on groceries this month?",
        "Create a shopping list for making biryani",
        "Show my BigBasket receipt from yesterday",
        "What's my total spending this week?",
        "Suggest ways to save money"
    ]
    
    results = []
    total_time = 0
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nQuery {i}: {query}")
        logger.info(f"Testing query {i}: {query}")
        
        start_time = datetime.now()
        result = pipeline.handle_query(query, user_id)
        query_time = (datetime.now() - start_time).total_seconds()
        total_time += query_time
        
        wallet_pass = result['wallet_pass']
        
        print(f"Pass Type: {wallet_pass['pass_type']}")
        print(f"Title: {wallet_pass['title']}")
        print(f"Subtitle: {wallet_pass['subtitle']}")
        print(f"Query time: {query_time:.2f} seconds")
        
        results.append({
            'query': query,
            'success': True,
            'result': result,
            'query_time': query_time,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"Query {i} completed - Type: {wallet_pass['pass_type']}, Time: {query_time:.2f}s")
    
    print(f"\nTotal chat testing time: {total_time:.2f} seconds")
    logger.info(f"Chat Assistant test completed - {len(results)} queries, Total time: {total_time:.2f}s")
    
    return {
        'test_type': 'chat',
        'queries_count': len(results),
        'success': True,
        'results': results,
        'total_time': total_time,
        'timestamp': datetime.now().isoformat()
    }

def test_chat_assistant_with_db(pipeline, user_id: str, logger):
    """Test Chat Assistant feature with database integration"""
    logger.info("Starting Chat Assistant test with DB")

    print(f"\n{'='*50}")
    print("TESTING CHAT ASSISTANT WITH FIRESTORE")
    print(f"{'='*50}")

    test_queries = [
        # "What is the weather in Mumbai?",
        "How much did I spend on groceries in the last 30 days?",
        "Show me all my receipts from 'Test Vendor'",
        "Create a shopping list for pasta.",
        "What was my total spending last week?",
        "Find receipts over 100"
    ]

    # First, let's add a dummy receipt to ensure our queries have something to find
    try:
        logger.info("Adding a dummy receipt for testing purposes.")
        dummy_receipt_data = {
            'user_id': user_id,
            'vendor_name': 'Test Vendor',
            'category': 'grocery',
            'date_time': datetime.now() - timedelta(days=5),
            'amount': 150.0,
            'subtotal': 140.0,
            'tax': 10.0,
            'currency': 'INR',
            'payment_method': 'card',
            'language': 'en',
            'items': [{'name': 'Test Item', 'quantity': 1, 'unit': 'pcs', 'price': 140.0}],
            'created_at': datetime.now()
        }
        pipeline.db.add_update_recipt_details(user_id=user_id, recipt_doc=dummy_receipt_data)
        logger.info("Dummy receipt added successfully.")
    except Exception as e:
        logger.error(f"Failed to add dummy receipt: {e}")


    results = []
    total_time = 0

    for i, query in enumerate(test_queries, 1):
        print(f"\nQuery {i}: {query}")
        logger.info(f"Testing query {i}: {query}")

        start_time = datetime.now()
        result = pipeline.handle_query(query, user_id)
        query_time = (datetime.now() - start_time).total_seconds()
        total_time += query_time

        wallet_pass = result['wallet_pass']

        print(f"Pass Type: {wallet_pass['pass_type']}")
        print(f"Title: {wallet_pass['title']}")
        print(f"Subtitle: {wallet_pass['subtitle']}")
        print(f"Query time: {query_time:.2f} seconds")

        # You can add more detailed checks on the results here if needed
        print("Details:", json.dumps(wallet_pass.get('details', {}), indent=2, default=str))


        results.append({
            'query': query,
            'success': True, # Add more robust success criteria
            'result': result,
            'query_time': query_time,
            'timestamp': datetime.now().isoformat()
        })

        logger.info(f"Query {i} completed - Type: {wallet_pass['pass_type']}, Time: {query_time:.2f}s")

    print(f"\nTotal chat testing time with DB: {total_time:.2f} seconds")
    logger.info(f"Chat Assistant test with DB completed - {len(results)} queries, Total time: {total_time:.2f}s")

    return {
        'test_type': 'chat_with_db',
        'queries_count': len(results),
        'success': True,
        'results': results,
        'total_time': total_time,
        'timestamp': datetime.now().isoformat()
    }


def test_analytics_feature(pipeline, user_id: str, logger):
    """Test Analytics feature"""
    logger.info("Starting Analytics test")
    
    print(f"\n{'='*50}")
    print("TESTING ANALYTICS FEATURE")
    print(f"{'='*50}")
    
    start_time = datetime.now()
    insights = pipeline.generate_insights(user_id)
    processing_time = (datetime.now() - start_time).total_seconds()
    
    print(f"Generated {len(insights)} insight passes:")
    
    results = []
    for i, insight in enumerate(insights, 1):
        wallet_pass = insight['wallet_pass']
        print(f"\nInsight {i}:")
        print(f"Type: {wallet_pass['pass_type']}")
        print(f"Title: {wallet_pass['title']}")
        print(f"Subtitle: {wallet_pass['subtitle']}")
        
        details = wallet_pass.get('details', {})
        if details:
            print(f"Details: {len(details)} fields")
        
        results.append({
            'insight_id': insight['pass_id'],
            'pass_type': wallet_pass['pass_type'],
            'title': wallet_pass['title'],
            'subtitle': wallet_pass['subtitle'],
            'details_count': len(details)
        })
    
    print(f"\nAnalytics processing time: {processing_time:.2f} seconds")
    logger.info(f"Analytics test completed - {len(insights)} insights, Processing time: {processing_time:.2f}s")
    
    return {
        'test_type': 'analytics',
        'insights_count': len(insights),
        'success': True,
        'results': results,
        'processing_time': processing_time,
        'timestamp': datetime.now().isoformat()
    }

def generate_test_report(test_results, logger):
    """Generate comprehensive test report"""
    logger.info("Generating test report")
    
    # Create test results directory
    Path("data/test_results").mkdir(parents=True, exist_ok=True)
    
    # Generate report filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"data/test_results/pipeline_test_report_{timestamp}.json"
    
    # Prepare report data
    report = {
        'summary': {
            'test_run_id': timestamp,
            'total_tests': len(test_results),
            'successful_tests': sum(1 for r in test_results if r.get('success', False)),
            'failed_tests': sum(1 for r in test_results if not r.get('success', False)),
            'test_types': [r.get('test_type', 'unknown') for r in test_results],
            'total_processing_time': sum(r.get('processing_time', 0) for r in test_results),
            'timestamp': datetime.now().isoformat()
        },
        'test_results': test_results
    }
    
    # Calculate success rate
    if report['summary']['total_tests'] > 0:
        report['summary']['success_rate'] = (report['summary']['successful_tests'] / report['summary']['total_tests']) * 100
    else:
        report['summary']['success_rate'] = 0
    
    # Save report
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    # Print summary
    print(f"\n{'='*60}")
    print("TEST REPORT SUMMARY")
    print(f"{'='*60}")
    print(f"Test Run ID: {timestamp}")
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Successful: {report['summary']['successful_tests']}")
    print(f"Failed: {report['summary']['failed_tests']}")
    print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
    print(f"Total Processing Time: {report['summary']['total_processing_time']:.2f} seconds")
    print(f"Test Types: {', '.join(report['summary']['test_types'])}")
    print(f"\nDetailed report saved to: {report_file}")
    
    logger.info(f"Test report generated: {report_file}")
    return report_file

def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Wallet Agent AI Pipeline')
    parser.add_argument('--image', type=str, help='Path to test image')
    parser.add_argument('--test', choices=['ocr', 'chat', 'analytics', 'all', 'chat_db'], 
                       default='all', help='Which features to test')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_test_logging()
    logger.info("Starting Wallet Agent AI Pipeline test run")
    
    # Load environment
    env = load_env()
    
    # Get Project ID - This is required for Vertex AI
    project_id = env.get('FIRESTORE_PROJECT_ID')
    if not project_id:
        error_msg = "No Project ID provided. Set FIRESTORE_PROJECT_ID in your .env file."
        logger.error(error_msg)
        print(f"Error: {error_msg}")
        sys.exit(1)

    # Get Firestore credentials (optional)
    firestore_creds_path = env.get('FIRESTORE_CREDENTIALS_PATH')
    credentials = None
    use_db = False
    
    if firestore_creds_path:
        if os.path.exists(firestore_creds_path):
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                firestore_creds_path,
                scopes=[
                    'https://www.googleapis.com/auth/cloud-platform',
                    'https://www.googleapis.com/auth/generative-language'
                ]
            )
            use_db = True
            logger.info("Using service account credentials with proper scopes.")
        else:
            logger.warning(f"Firestore credentials file not found at {firestore_creds_path}. DB tests will be skipped.")
            firestore_creds_path = None # Ensure it's None if not found
    else:
        logger.warning("FIRESTORE_CREDENTIALS_PATH not set. Using Application Default Credentials for Vertex AI. DB tests will be skipped.")

    # Get test directories
    test_input_dir = env.get('TEST_INPUT_DIR', 'data/test_images')
    test_user_id = env.get('TEST_USER_ID', 'test_user_123')
    
    # Initialize pipeline
    print("Initializing Wallet Agent AI Pipeline...")
    logger.info("Initializing pipeline")
    
    from ai_pipeline.pipeline import AIPipeline
    
    try:
        if use_db:
            from backend.firestudio.firebase import FirebaseClient
            firebase_client = FirebaseClient()
            pipeline = AIPipeline(
                project_id=project_id,
                location="us-central1",
                credentials=credentials,
                firebase_client=firebase_client
            )
        else:
            pipeline = AIPipeline(
                project_id=project_id,
                location="us-central1",
                credentials=credentials
            )
        logger.info("Pipeline initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize AI Pipeline: {e}", exc_info=True)
        print(f"Error: Could not initialize AI Pipeline. Please check your GCP authentication and project setup.")
        sys.exit(1)
    
    # Run tests
    test_results = []
    
    if args.test in ['ocr', 'all']:
        image_path = args.image or os.path.join(test_input_dir, 'img_0.jpeg')
        result = test_ocr_feature(pipeline, image_path, test_user_id, logger)
        if result:
            test_results.append(result)
    
    if args.test in ['chat', 'all']:
        # Run the non-DB chat test regardless
        result = test_chat_feature(pipeline, test_user_id, logger)
        if result:
            test_results.append(result)

    if args.test in ['chat_db', 'all']:
        if use_db:
            result = test_chat_assistant_with_db(pipeline, test_user_id, logger)
            if result:
                test_results.append(result)
        else:
            logger.warning("Skipping DB-dependent chat test ('chat_db') as Firestore is not configured.")

    if args.test in ['analytics', 'all']:
        result = test_analytics_feature(pipeline, test_user_id, logger)
        if result:
            test_results.append(result)
    
    # Generate test report
    if test_results:
        report_file = generate_test_report(test_results, logger)
        logger.info(f"Test run completed. Report: {report_file}")
    else:
        logger.warning("No test results to report")
    
    print(f"\n{'='*50}")
    print("TESTING COMPLETE")
    print(f"{'='*50}")

if __name__ == "__main__":
    main() 