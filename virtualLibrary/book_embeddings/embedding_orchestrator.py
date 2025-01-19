"""
embedding_orchestrator.py

Purpose: Orchestrate the embedding generation process using Modal for compute
Requires: Modal compute, Firebase access, and Google Drive API credentials
"""

import modal
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config  
import time
from pathlib import Path


project_mount = modal.Mount.from_local_dir(
    str(Path(__file__).parent.parent), 
    remote_path="/root/virtualLibrary"  
)

# Define Modal app and image
app = modal.App(name="embedding-orchestrator")

image = modal.Image.debian_slim(python_version="3.10").run_commands(
    "pip uninstall -y pydantic",
    "pip uninstall -y fastapi",
).pip_install(
    "google-auth-oauthlib",
    "google-auth",
    "google-api-python-client",
    "firebase-admin==6.6.0",
    "python-dotenv",
    "google-cloud-firestore",
    "pydantic>=2.0.0",
    "nomic==3.2.0",  
    "PyPDF2",
    "numpy"
)

@app.function(
    image=image,
    mounts=[project_mount],
    schedule=modal.Period(hours=4),
    secrets=[
        modal.Secret.from_dict({
            "GOOGLE_CLIENT_ID": Config.GOOGLE_CLIENT_ID,
            "GOOGLE_CLIENT_SECRET": Config.GOOGLE_CLIENT_SECRET,
            "FIREBASE_PRIVATE_KEY": Config.FIREBASE_PRIVATE_KEY,
            "GOOGLE_DRIVE_FOLDER_ID": Config.GOOGLE_DRIVE_FOLDER_ID,
            "FIREBASE_PROJECT_ID": Config.FIREBASE_PROJECT_ID,
            "FIREBASE_CLIENT_EMAIL": Config.FIREBASE_CLIENT_EMAIL,
            "FIREBASE_PRIVATE_KEY_ID": Config.FIREBASE_PRIVATE_KEY_ID,
            "FIREBASE_CLIENT_ID": Config.FIREBASE_CLIENT_ID,
            "FIREBASE_AUTH_URI": Config.FIREBASE_AUTH_URI,
            "FIREBASE_TOKEN_URI": Config.FIREBASE_TOKEN_URI,
            "FIREBASE_AUTH_PROVIDER_CERT_URL": Config.FIREBASE_AUTH_PROVIDER_CERT_URL,
            "FIREBASE_CLIENT_CERT_URL": Config.FIREBASE_CLIENT_CERT_URL,
            "NOMIC_API_KEY": Config.NOMIC_API_KEY
        })
    ],
    timeout=18000  # 1 hour timeout for long-running processes
)
def process_embeddings():
    """Process books that need embedding generation"""
    import sys
    sys.path.append("/root/virtualLibrary")
    from firebase.db_operations import FirebaseManager 
    from book_embeddings.embedder import BookEmbedder  
    from book_embeddings.drive_storage import DriveEmbeddingStorage  
    
    try:
        # Initialize services
        firebase = FirebaseManager()
        storage = DriveEmbeddingStorage()
        embedder = BookEmbedder()
        
        # Get all books and filter for ones needing embedding
        all_books = firebase.get_existing_books()
        books_to_process = [
            book for book in all_books.values()
            if not book.get('embedding_status') or  
            book.get('embedding_status') == 'failed'  
        ][:5]  

        for book in books_to_process:
            try:
                # Mark as processing
                firebase.update_book(book['doc_id'], {
                    'embedding_status': 'processing',
                    'embedding_started_at': time.time()
                })
                
                # Process embeddings
                embedding_path = storage.get_temp_path(book['title'])
                embedder.process_drive_book(book['drive_id'], embedding_path)
                
                # Upload to Drive
                embedding_link = storage.store_embedding(
                    embedding_path, 
                    book['title']
                )
                
                # Update Firebase
                firebase.update_book(book['doc_id'], {
                    'embedding_status': 'completed',
                    'embedding_link': embedding_link,
                    'embedding_completed_at': time.time()
                })
                
                print(f"Successfully processed embeddings for: {book['title']}")
                
            except Exception as e:
                print(f"Error processing book {book['title']}: {str(e)}")
                firebase.update_book(book['doc_id'], {
                    'embedding_status': 'failed',
                    'embedding_error': str(e)
                })
                
        print("Embedding processing completed")
        
    except Exception as e:
        print(f"Embedding orchestration failed: {str(e)}")
        raise

@app.local_entrypoint()
def main():
    process_embeddings.remote()

if __name__ == "__main__":
    main()
