"""
Module for extracting text from PDF files.
"""

import PyPDF2
import json
import sys
import re
import os

def extract_pdf_text(pdf_path):
    """
    Extract text from all pages of a PDF file.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: JSON string with extracted text or error
    """
    try:
        with open(pdf_path, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)
            text = ""
            
            # Extract text from all pages
            for i in range(len(pdf.pages)):
                page_text = pdf.pages[i].extract_text()
                # Clean the text to remove problematic characters
                page_text = re.sub(r'[\\"]', ' ', page_text)  # Replace backslashes and quotes
                text += page_text + "\n\n"
            
            # Return the extracted text as JSON
            return json.dumps({"text": text})
            
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    # Get the PDF path from command line arguments
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing required argument: pdf_path"}))
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # Check if the file exists
    if not os.path.exists(pdf_path):
        print(json.dumps({"error": f"PDF file not found: {pdf_path}"}))
        sys.exit(1)
    
    # Extract text and print the result
    result = extract_pdf_text(pdf_path)
    print(result) 