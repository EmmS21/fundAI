"""
orchestrator.py

Purpose: Orchestrate file synchronization between Google Drive and Firebase using Modal
"""
import modal
from ..config import Config

# Define Modal stub and image
app = modal.App(name="orchestrator")

image = modal.Image.debian_slim(python_version="3.10").pip_install(
    "google-auth-oauthlib",
    "google-auth",
    "google-api-python-client",
    "firebase-admin==6.6.0",
    "python-dotenv",
    "google-cloud-firestore",  
    "google-cloud-storage",
    "cachecontrol",
    "google-api-core",
    "pyjwt"
)

@app.function(
    image=image,
    schedule=modal.Period(hours=1),  
    secrets=[
        modal.Secret.from_dict({
            "GOOGLE_CLIENT_ID": Config.GOOGLE_CLIENT_ID,
            "GOOGLE_CLIENT_SECRET": Config.GOOGLE_CLIENT_SECRET,
            "FIREBASE_PRIVATE_KEY": Config.FIREBASE_PRIVATE_KEY,
            "GOOGLE_DRIVE_FOLDER_ID": Config.GOOGLE_DRIVE_FOLDER_ID,
            "FIREBASE_PROJECT_ID": Config.FIREBASE_PROJECT_ID,
            "FIREBASE_CLIENT_EMAIL": Config.FIREBASE_CLIENT_EMAIL
        })
    ]
)
def sync_files():
    """Synchronize files between Google Drive and Firebase"""
    from ..queryGoogleDrive.syncBook import DriveScanner
    from ..firebase.db_operations import FirebaseManager

    try:
        # Initialize services
        drive_scanner = DriveScanner(Config.GOOGLE_DRIVE_FOLDER_ID)
        firebase = FirebaseManager()
        
        # Get existing books from Firebase
        existing_books = firebase.get_existing_books()
        
        # Scan Google Drive for files
        drive_files = drive_scanner.list_files()
        
        for file in drive_files:
            try:
                # Parse metadata
                metadata = drive_scanner.parser.parse_drive_file(file)
                drive_id = metadata['drive_id']
                
                if drive_id not in existing_books:
                    # New book - add to Firebase
                    firebase.add_book(metadata)
                    print(f"Added new book: {metadata['title']}")
                else:
                    # Existing book - check for updates
                    existing = existing_books[drive_id]
                    if existing.get('updated_date') != metadata.get('updated_date'):
                        firebase.update_book(existing['doc_id'], metadata)
                        print(f"Updated book: {metadata['title']}")
                        
            except ValueError as e:
                print(f"Error parsing file {file['name']}: {str(e)}")
                
        print("Synchronization completed successfully")
        
    except Exception as e:
        print(f"Synchronization failed: {str(e)}")
        raise

@app.local_entrypoint()
def main():
    sync_files.remote()

if __name__ == "__main__":
    main()
