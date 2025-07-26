import os
import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials

class FirebaseClient():
    def __init__(self):
        cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        # Check if Firebase is already initialized
        try:
            app = firebase_admin.get_app()
        except ValueError:
            # Application Default credentials are automatically created.
            app = firebase_admin.initialize_app(cred)
        self.db = firestore.client(database_id="walletagent")

    def add_update_recipt_details(self, user_id = '123', recipt_id = None, recipt_doc = None):
        
        if recipt_id :
            doc_ref = self.db.collection("users").document(user_id).collection("recipts").document(recipt_id)
            doc_dict = doc_ref.get().to_dict()
            for key, value in recipt_doc.items():
                doc_dict[key] = value
            recipt_doc = doc_dict
        else :
            doc_ref = self.db.collection("users").document(user_id).collection("recipts").document()
        doc_ref.set(recipt_doc)
        return doc_ref.id

    def add_update_pass_details(self, user_id = '123', pass_id = None, pass_doc = None):
        if pass_id :
            doc_ref = self.db.collection("users").document(user_id).collection("passes").document(pass_id)
        else :
            doc_ref = self.db.collection("users").document(user_id).collection("passes").document()
        doc_ref.set(pass_doc)
        return doc_ref.id

    def add_(self, user_id = '123', pass_id = None, pass_doc = None):
        if pass_id :
            doc_ref = self.db.collection("users").document(user_id).collection("passes").document(pass_id)
        else :
            doc_ref = self.db.collection("users").document(user_id).collection("passes").document()
        doc_ref.set(pass_doc)
        return doc_ref.id

# Remove the global instance creation to prevent multiple initializations
# firebase_client = FirebaseClient()

# x = firebase_client.add_update_recipt_details(user_id = '123', recipt_doc = {'a':'b', 'b':'c'})
# firebase_client.add_update_recipt_details(user_id = '123', recipt_id = x, recipt_doc = {'b':'reddy', 'c':'shyam'})
