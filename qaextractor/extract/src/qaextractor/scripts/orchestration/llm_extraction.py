"""
Simple module to download a PDF from Google Drive for LLM processing.
"""

import os
import sys
import json
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

def get_drive_service():
    """Create and return an authorized Google Drive service instance"""
    credentials = service_account.Credentials.from_service_account_file(
        "credentials.json",
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=credentials)

def download_pdf(service, file_id, output_dir):
    """Download a PDF file from Google Drive and save it to the specified directory"""
    request = service.files().get_media(fileId=file_id)
    
    file_content = io.BytesIO()
    downloader = MediaIoBaseDownload(file_content, request)
    
    done = False
    while not done:
        status, done = downloader.next_chunk()
    
    file_content.seek(0)
    
    # Debug: Print the actual output directory path
    print(f"DEBUG: Output directory path is: {output_dir}", file=sys.stderr)
    
    # Make sure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Save to the output directory with a predictable name
    pdf_path = os.path.join(output_dir, "exam.pdf")
    
    # Debug: Print the full PDF path we're about to write to
    print(f"DEBUG: Will save PDF to: {pdf_path}", file=sys.stderr)
    
    with open(pdf_path, "wb") as f:
        f.write(file_content.getbuffer())
    
    # Debug: Verify the file was created
    if os.path.exists(pdf_path):
        print(f"DEBUG: File was created successfully at {pdf_path}", file=sys.stderr)
        print(f"DEBUG: File size: {os.path.getsize(pdf_path)} bytes", file=sys.stderr)
    else:
        print(f"DEBUG: File creation failed! {pdf_path} does not exist", file=sys.stderr)
    
    # Debug: List all files in the output directory
    print(f"DEBUG: Contents of {output_dir}:", file=sys.stderr)
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        print(f"DEBUG: - {item} ({os.path.getsize(item_path)} bytes)", file=sys.stderr)
    
    return pdf_path

def get_file_info(service, file_id):
    """Get file metadata from Google Drive"""
    file_info = service.files().get(fileId=file_id, fields="name,mimeType").execute()
    return file_info

if __name__ == "__main__":
    # Get arguments
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Missing required argument: file_id"
        }))
        sys.exit(1)
    
    file_id = sys.argv[1]
    
    # Get output directory (default to current directory if not specified)
    output_dir = os.getcwd()
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
    
    # Debug: Print all arguments
    print(f"DEBUG: Script arguments: {sys.argv}", file=sys.stderr)
    print(f"DEBUG: Using output directory: {output_dir}", file=sys.stderr)
    
    try:
        # Get Drive service
        service = get_drive_service()
        
        # Get file info
        file_info = get_file_info(service, file_id)
        
        # Download the PDF directly to the output directory
        pdf_path = download_pdf(service, file_id, output_dir)
        
        # Return the result
        print(json.dumps({
            "success": True,
            "file_id": file_id,
            "file_name": file_info.get("name", ""),
            "pdf_path": pdf_path
        }))
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Exception occurred: {str(e)}", file=sys.stderr)
        print(f"DEBUG: {traceback.format_exc()}", file=sys.stderr)
        print(json.dumps({
            "success": False,
            "file_id": file_id,
            "error": str(e),
            "traceback": traceback.format_exc()
        }))
