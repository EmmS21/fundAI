"""
Update Embedding Access Script

Purpose: 
1. Make existing embedding folders publicly accessible
2. Update Firebase records to mark books as properly embedded
"""

import firebase_admin
from firebase_admin import credentials, firestore
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from config import Config

class EmbeddingAccessManager:
    def __init__(self):
        """Initialize Firebase and Drive connections"""
        # Initialize Firebase
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": Config.FIREBASE_PROJECT_ID,
            "private_key_id": Config.FIREBASE_PRIVATE_KEY_ID,
            "private_key": Config.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
            "client_email": Config.FIREBASE_CLIENT_EMAIL,
            "client_id": Config.FIREBASE_CLIENT_ID,
            "auth_uri": Config.FIREBASE_AUTH_URI,
            "token_uri": Config.FIREBASE_TOKEN_URI,
            "auth_provider_x509_cert_url": Config.FIREBASE_AUTH_PROVIDER_CERT_URL,
            "client_x509_cert_url": Config.FIREBASE_CLIENT_CERT_URL
        })
        firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        
        # Initialize Drive service
        drive_creds = service_account.Credentials.from_service_account_info({
            "type": "service_account",
            "project_id": Config.FIREBASE_PROJECT_ID,
            "private_key": Config.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
            "client_email": Config.FIREBASE_CLIENT_EMAIL,
            "token_uri": "https://oauth2.googleapis.com/token",
        }, scopes=['https://www.googleapis.com/auth/drive'])
        
        self.drive_service = build('drive', 'v3', credentials=drive_creds)

    def make_folder_public(self, folder_id: str) -> bool:
        """Make a Drive folder and its contents publicly accessible"""
        try:
            # Make the folder accessible to anyone with the link
            self.drive_service.permissions().create(
                fileId=folder_id,
                body={
                    'type': 'anyone',
                    'role': 'reader'
                }
            ).execute()
            
            # Get all files in the folder
            files = self.drive_service.files().list(
                q=f"'{folder_id}' in parents",
                fields="files(id, name)"
            ).execute().get('files', [])
            
            # Make each file accessible
            for file in files:
                self.drive_service.permissions().create(
                    fileId=file['id'],
                    body={
                        'type': 'anyone',
                        'role': 'reader'
                    }
                ).execute()
                print(f"Made {file['name']} publicly accessible")
            
            return True
            
        except Exception as e:
            print(f"Error updating permissions for folder {folder_id}: {str(e)}")
            return False

    def update_embedded_books(self):
        """Update all successfully embedded books"""
        try:
            # Get books with completed embeddings
            query = self.db.collection('books').where(
                'embedding_status', '==', 'completed'
            ).where(
                'is_embedded', '==', False
            )
            
            books = query.stream()
            
            for book in books:
                book_data = book.to_dict()
                embedding_link = book_data.get('embedding_link', '')
                
                if not embedding_link:
                    continue
                    
                # Extract folder ID from Drive link
                folder_id = embedding_link.split('/')[-1]
                
                # Make folder public
                if self.make_folder_public(folder_id):
                    # Update Firebase record
                    self.db.collection('books').document(book.id).update({
                        'is_embedded': True,
                        'updated_date': datetime.utcnow()
                    })
                    print(f"Successfully updated access for book: {book_data.get('title')}")
                else:
                    print(f"Failed to update access for book: {book_data.get('title')}")
            
        except Exception as e:
            print(f"Error updating embedded books: {str(e)}")

def main():
    manager = EmbeddingAccessManager()
    manager.update_embedded_books()

if __name__ == "__main__":
    main()
