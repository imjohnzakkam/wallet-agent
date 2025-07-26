import os
import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials

class FirebaseClient():
    def __init__(self):
        cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        # Application Default credentials are automatically created.
        app = firebase_admin.initialize_app(cred)
        self.db = firestore.client(database_id="walletagent")

    def add_update_recipt_details(self, user_id = '123', recipt_id = None, recipt_doc = None):
        if recipt_id :
            doc_ref = self.db.collection("users").document(user_id).collection("recipts").document(recipt_id)
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

firebase_client = FirebaseClient()
print (firebase_client.add_update_recipt_details(recipt_doc = {'a':'b'}))