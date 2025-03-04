import PyPDF2
import io
import json
import base64
import sys
import os
from PIL import Image

def extract_image_from_page(pdf_path, page_number):
    """
    Extract the first image from a specific page in a PDF file and return it as a base64-encoded string.
    
    Args:
        pdf_path (str): Path to the PDF file.
        page_number (int): Page number to extract the image from (0-indexed).
        
    Returns:
        str: JSON string with base64-encoded image data.
    """
    try:
        with open(pdf_path, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)
            if page_number >= len(pdf.pages):
                return json.dumps({"error": "Page number out of range"})
            
            page = pdf.pages[page_number]
            if '/Resources' in page and '/XObject' in page['/Resources']:
                xobjects = page['/Resources']['/XObject']
                for obj_name in xobjects:
                    obj = xobjects[obj_name]
                    if obj['/Subtype'] == '/Image':
                        # Extract raw image data
                        try:
                            raw_data = obj.get_data() if hasattr(obj, "get_data") else obj._data
                        except Exception:
                            continue
                        
                        # Convert to base64
                        img_str = base64.b64encode(raw_data).decode()
                        return json.dumps({"image_data": img_str, "format": "raw"})
            
            return json.dumps({"error": "No image found on the specified page"})
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    # Simple command-line interface for the tool
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Missing required arguments. Usage: pdf_tools.py <command> <pdf_path> [args]"}))
        sys.exit(1)
    
    command = sys.argv[1]
    pdf_path = sys.argv[2]
    
    if not os.path.exists(pdf_path):
        print(json.dumps({"error": f"PDF file not found: {pdf_path}"}))
        sys.exit(1)
    
    if command == "extract_images":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Missing page number for extract_images command"}))
            sys.exit(1)
        page_number = int(sys.argv[3])
        print(extract_image_from_page(pdf_path, page_number))
    else:
        print(json.dumps({"error": f"Unknown command: {command}"}))
        sys.exit(1)
