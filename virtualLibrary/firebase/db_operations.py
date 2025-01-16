"""
db_operations.py

Purpose: Handle all Firebase database operations for book metadata
Requires: Firebase Admin SDK credentials from environment variables
"""

import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict, Optional
from datetime import datetime
from ..config import Config

class FirebaseManager:
    def __init__(self):
        """Initialize Firebase connection with credentials"""
        # Replace \n with actual newlines in the private key
        private_key = Config.FIREBASE_PRIVATE_KEY.replace('\\n', '\n')
        
        print("\nDebug - Config values:")
        print(f"Project ID: {Config.FIREBASE_PROJECT_ID}")
        print(f"Private Key (first 50 chars): {private_key[:50] if private_key else 'None'}")
        print(f"Client Email: {Config.FIREBASE_CLIENT_EMAIL}")
        
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": Config.FIREBASE_PROJECT_ID,
            "private_key_id": Config.FIREBASE_PRIVATE_KEY_ID,
            "private_key": private_key,
            "client_email": Config.FIREBASE_CLIENT_EMAIL,
            "client_id": Config.FIREBASE_CLIENT_ID,
            "auth_uri": Config.FIREBASE_AUTH_URI,
            "token_uri": Config.FIREBASE_TOKEN_URI,
            "auth_provider_x509_cert_url": Config.FIREBASE_AUTH_PROVIDER_CERT_URL,
            "client_x509_cert_url": Config.FIREBASE_CLIENT_CERT_URL
        })
        firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        self.books_collection = self.db.collection('books')

    def get_existing_books(self) -> Dict[str, Dict]:
        """
        Retrieve all books from Firebase
        
        Returns:
            Dictionary mapping Drive IDs to book metadata
            
        Raises:
            Exception: If retrieving books fails
        """
        try:
            books = {}
            docs = self.books_collection.stream()
            for doc in docs:
                book_data = doc.to_dict()
                drive_id = book_data.get('drive_id')
                if drive_id:
                    books[drive_id] = {**book_data, 'doc_id': doc.id}
            return books
        except Exception as e:
            raise Exception(f"Error retrieving books: {str(e)}")

    def add_book(self, book_metadata: Dict) -> str:
        """
        Add a new book to Firebase
        
        Args:
            book_metadata: Dictionary containing book metadata
            
        Returns:
            Document ID of the newly added book
            
        Raises:
            Exception: If adding book fails
        """
        try:
            # Add timestamps
            book_metadata['added_date'] = datetime.now()
            book_metadata['updated_date'] = datetime.now()

            book_metadata['vector_embedding_link'] = ''
            book_metadata['is_embedded'] = False

            # Add to Firestore
            doc_ref = self.books_collection.add(book_metadata)
            return doc_ref[1].id
        except Exception as e:
            raise Exception(f"Error adding book: {str(e)}")

    def update_book(self, doc_id: str, book_metadata: Dict) -> None:
        """
        Update existing book metadata
        
        Args:
            doc_id: Firestore document ID
            book_metadata: Updated book metadata
            
        Raises:
            Exception: If update fails
        """
        try:
            # Add update timestamp
            book_metadata['updated_date'] = datetime.utcnow()
            
            # Update in Firestore
            self.books_collection.document(doc_id).update(book_metadata)
        except Exception as e:
            raise Exception(f"Error updating book: {str(e)}")

    def find_book_by_drive_id(self, drive_id: str) -> Optional[Dict]:
        """
        Find a book by its Google Drive ID
        
        Args:
            drive_id: Google Drive file ID
            
        Returns:
            Book metadata dictionary if found, None otherwise
            
        Raises:
            Exception: If query fails
        """
        try:
            query = self.books_collection.where('drive_id', '==', drive_id).limit(1)
            docs = query.stream()
            
            for doc in docs:
                return {**doc.to_dict(), 'doc_id': doc.id}
            return None
        except Exception as e:
            raise Exception(f"Error finding book: {str(e)}")


def main():
    """Test Firebase operations"""
    firebase = FirebaseManager()
    
    try:
        # Test retrieving books
        books = firebase.get_existing_books()
        print(f"\nFound {len(books)} existing books")
        
        # Print first book as example
        if books:
            first_book = next(iter(books.values()))
            print("\nExample book:")
            print(f"Title: {first_book.get('title')}")
            print(f"Author: {first_book.get('author')}")
            print(f"Year: {first_book.get('year')}")
            print(f"Added: {first_book.get('added_date')}")
            print(f"Updated: {first_book.get('updated_date')}")
            print(f"Drive ID: {first_book.get('drive_id')}")
            print(f"Document ID: {first_book.get('doc_id')}")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
