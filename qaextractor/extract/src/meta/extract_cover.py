"""
Script to extract text from the cover page of a PDF file.
"""

import sys
import json
import PyPDF2

def extract_cover_page(pdf_path):
    """Extract text from the first page of a PDF"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            if len(reader.pages) > 0:
                cover_text = reader.pages[0].extract_text()
                return {
                    "success": True,
                    "cover_text": cover_text
                }
            else:
                return {
                    "success": False,
                    "error": "PDF has no pages"
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Missing PDF path argument"
        }))
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    result = extract_cover_page(pdf_path)
    print(json.dumps(result))
