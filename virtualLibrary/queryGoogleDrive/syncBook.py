"""
drive_scanner.py

Purpose: Connect to Google Drive and scan a specific folder for files
Requires: Google Drive API credentials and folder ID
"""

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from typing import List, Dict
import pickle
from pathlib import Path
from ..config import Config

# If modifying these scopes, delete the token.pickle file
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class DriveScanner:
    def __init__(self, folder_id: str):
        self.folder_id = folder_id
        self.service = self._initialize_drive_service()

    def _initialize_drive_service(self):
        """Initialize and return Google Drive service"""
        creds = None
        
        # Get the directory where this script is located
        current_dir = Path(__file__).parent
        
        # Load existing token if it exists
        if (current_dir / 'token.pickle').exists():
            with open(current_dir / 'token.pickle', 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials available, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(current_dir / 'googleOAuth.json'), SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(current_dir / 'token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        return build('drive', 'v3', credentials=creds)

    def list_files(self) -> List[Dict]:
        """
        List all files in the specified folder
        Returns: List of dictionaries containing file information
        """
        try:
            # Define which fields we want to retrieve
            fields = "files(id, name, mimeType, createdTime, modifiedTime)"
            
            # Query for files in the specified folder
            results = self.service.files().list(
                q=f"'{self.folder_id}' in parents and trashed=false",
                pageSize=100,
                fields=fields
            ).execute()
            
            return results.get('files', [])

        except Exception as e:
            raise Exception(f"Error listing files: {str(e)}")

    def get_file_details(self, file_id: str) -> Dict:
        """Get detailed information about a specific file"""
        try:
            return self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, createdTime, modifiedTime"
            ).execute()
        except Exception as e:
            raise Exception(f"Error getting file details: {str(e)}")


def main():
    scanner = DriveScanner(Config.GOOGLE_DRIVE_FOLDER_ID)
    
    try:
        # List all files in the folder
        files = scanner.list_files()
        
        # Print file information
        for file in files:
            print(f"Found file: {file['name']} ({file['id']})")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()