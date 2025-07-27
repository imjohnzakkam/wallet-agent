import os
import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials
from dotenv import load_dotenv
from google.oauth2 import service_account
from datetime import timezone

# Load environment variables from .env file
load_dotenv()

# Constants for collection names
USERS = "users"
RECEIPTS = "receipts"
PASSES = "passes"
TIMESTAMP = "date_time"
QUERIES = "queries"

class FirebaseClient():
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(FirebaseClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not firebase_admin._apps:
            # Get credentials from environment variable
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/backend/config/service-account.json")
            print(credentials_path)
            
            # Credentials for Firebase Admin SDK
            self.cred = credentials.Certificate(credentials_path)
            print(self.cred)
            firebase_admin.initialize_app(self.cred)
            
            # Credentials for other Google Cloud SDKs (like Vertex AI)
            self.google_cloud_creds = service_account.Credentials.from_service_account_file(credentials_path)
        
        self.db = firestore.client(database_id="walletagent")

    def add_or_update_document(self, collection_path: list, document_id: str = None, data: dict = None):
        """
        Adds or updates a document in a specified collection.

        Args:
            collection_path (list): A list of collection and document names.
            document_id (str): The ID of the document to update. If None, a new document is created.
            data (dict): The data to set in the document.

        Returns:
            str: The ID of the document.
        """
        collection_ref = self.db.collection(collection_path[0])
        for i in range(1, len(collection_path)):
            if i % 2 == 1:
                collection_ref = collection_ref.document(collection_path[i])
            else:
                collection_ref = collection_ref.collection(collection_path[i])

        if document_id:
            doc_ref = collection_ref.document(document_id)
            doc_snapshot = doc_ref.get()
            if doc_snapshot.exists:
                existing_data = doc_snapshot.to_dict()
                existing_data.update(data)
                doc_ref.set(existing_data)
            else:
                doc_ref.set(data)
        else:
            doc_ref = collection_ref.document()
            doc_ref.set(data)
        
        return doc_ref.id

    def add_update_receipt_details(self, user_id: str, receipt_id: str = None, receipt_doc: dict = None):
        return self.add_or_update_document([USERS, user_id, RECEIPTS], receipt_id, receipt_doc)

    def add_update_pass_details(self, user_id: str, pass_id: str = None, pass_doc: dict = None):
        return self.add_or_update_document([USERS, user_id, PASSES], pass_id, pass_doc)

    def add_user_query(self, user_id: str, query: str, llm_response: str):
        """
        Stores user query and its LLM response in Firestore.
        """
        from datetime import datetime
        query_data = {
            'query': query,
            'llm_response': llm_response,
            'timestamp': datetime.now(timezone.utc)
        }
        return self.add_or_update_document([USERS, user_id, QUERIES], data=query_data)

    def get_user_queries(self, user_id: str):
        """
        Retrieves all queries for a user, sorted by timestamp in ascending order.
        """
        queries_ref = self.db.collection(USERS).document(user_id).collection(QUERIES)
        docs = queries_ref.order_by('timestamp', direction=firestore.Query.ASCENDING).stream()
        
        queries = []
        for doc in docs:
            query_data = doc.to_dict()
            query_data['query_id'] = doc.id
            # Convert timestamp to ISO 8601 string format
            query_data['timestamp'] = query_data['timestamp'].isoformat()
            queries.append(query_data)
            
        return queries

    def get_receipts_by_timerange(self, user_id='123', start_timestamp=None, end_timestamp=None):
        from datetime import datetime

        receipts_ref = self.db.collection(USERS).document(user_id).collection(RECEIPTS)
        
        query = receipts_ref
        
        # if start_timestamp:   
        #     if isinstance(start_timestamp, str):
        #         start_timestamp = datetime.fromisoformat(start_timestamp.replace('Z', '+00:00'))
        #     query = query.where(TIMESTAMP, '>=', start_timestamp) 
            
        # if end_timestamp:
        #     if isinstance(end_timestamp, str):
        #         end_timestamp = datetime.fromisoformat(end_timestamp.replace('Z', '+00:00'))
        #     query = query.where(TIMESTAMP, '<=', end_timestamp)
        
        docs = query.stream()
        
        receipts = []
        for doc in docs:
            receipt_data = doc.to_dict()
            receipt_data['receipt_id'] = doc.id
            receipts.append(receipt_data)
        
        return receipts
    
    def get_receipt_by_user_id_receipt_id(self,receipt_id , user_id='123'):
        return self.db.collection(USERS).document(user_id).collection(RECEIPTS).document(receipt_id).get().to_dict()

# firebase_client = FirebaseClient()
# x = firebase_client.add_update_receipt_details(user_id = 'prahladha', receipt_doc = {'a':'bb', 'b':'c'})
# firebase_client.add_update_receipt_details(user_id = 'prahladha', receipt_id = x, receipt_doc = {'a':'bbbbb', 'd':'cc'})
# print(firebase_client.get_receipts_by_timerange(user_id = 'prahladha'))

# print(x)