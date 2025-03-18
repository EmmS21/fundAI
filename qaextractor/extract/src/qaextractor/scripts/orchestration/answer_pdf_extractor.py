"""
Simplified PDF extractor for answer sheets - focuses on text extraction
without complex image/graphic analysis
"""

import PyPDF2
import json
import sys
import re
import os
import base64
import traceback
from PIL import Image
import io
from pdf2image import convert_from_path

def extract_answer_pdf(pdf_path):
    """
    Extract text and minimal metadata from an answer sheet PDF.
    Optimized for faster processing with minimal image analysis.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: JSON string with extracted content or error
    """    
    try:
        with open(pdf_path, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)
            
            result = {
                "text": "",
                "pages": [],
                "total_pages": len(pdf.pages),
                "has_cover_page": False,
                "metadata": {
                    "filename": os.path.basename(pdf_path)
                }
            }
            
            # Process each page
            for page_num, page in enumerate(pdf.pages):
                page_info = {
                    "page_number": page_num + 1,
                    "text": ""
                }
                
                # Extract text
                try:
                    page_text = page.extract_text()
                except Exception as e:
                    page_text = f"[ERROR EXTRACTING TEXT: {str(e)}]"
                
                # Clean the text to remove problematic characters
                page_text = re.sub(r'[\\"]', ' ', page_text)
                
                # Add to overall text and page-specific text
                result["text"] += page_text + "\n\n"
                page_info["text"] = page_text
                
                # Check if this is a cover page (simple heuristic: first page with little text)
                if page_num == 0:
                    is_cover_page = len(page_text) < 500
                    result["has_cover_page"] = is_cover_page
                    page_info["is_cover_page"] = is_cover_page
                    
                    if is_cover_page:
                        try:
                            # Only convert cover page to image for reference
                            images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=150)
                            if images:
                                # Just note we have a cover image but don't try to upload it
                                result["cover_page_detected"] = True
                                # Add a marker in the text
                                cover_marker = "\n[COVER PAGE IMAGE AVAILABLE]\n"
                                result["text"] = cover_marker + result["text"]
                        except Exception as e:
                            print(f"  Error capturing cover image: {str(e)}")
                
                # Extract question/answer numbers
                answer_numbers = find_answer_references(page_text)
                if answer_numbers:
                    page_info["answer_numbers"] = answer_numbers
                
                # Add page info to result
                result["pages"].append(page_info)
            
            # Look for structural elements that might indicate answers
            result["answer_references"] = find_all_answer_references(result["text"])
            result["mark_allocations"] = find_mark_allocations(result["text"])
            result["grade_boundaries"] = find_grade_boundaries(result["text"])
            
            return json.dumps(result)
            
    except Exception as e:
        error_msg = f"Error in PDF extraction: {str(e)}"
        return json.dumps({
            "error": error_msg, 
            "traceback": traceback.format_exc()
        })

def find_answer_references(text):
    """Find answer numbers/references in text"""
    # Common patterns in answer sheets
    patterns = [
        r'(?:Answer|Ans\.?|A\.?)\s*(\d+[a-z]?)',  # Answer 1, Ans. 2, A.3
        r'(?:Question|Q\.?)\s*(\d+[a-z]?)',       # Question references
        r'^\s*(\d+[a-z]?)\.\s',                   # Numbered lines like "1. Answer text"
        r'\[(\d+)\s*marks\]'                      # Mark allocations
    ]
    
    all_references = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        all_references.extend(matches)
    
    return sorted(set(all_references))  # Remove duplicates and sort

def find_all_answer_references(text):
    """Find all answer references in the entire document"""
    return find_answer_references(text)

def find_mark_allocations(text):
    """Find mark allocations in the text"""
    # Look for patterns like [5 marks], (10 marks), etc.
    mark_patterns = [
        r'\[(\d+)\s*marks?\]',
        r'\((\d+)\s*marks?\)',
        r'(\d+)\s*marks? allocated',
        r'worth\s*(\d+)\s*marks?'
    ]
    
    all_marks = []
    for pattern in mark_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                all_marks.append(int(match))
            except ValueError:
                pass
    
    return all_marks

def find_grade_boundaries(text):
    """Find any grade boundaries mentioned in the text"""
    # Common grade boundary patterns
    grade_patterns = [
        r'Grade\s+([A-F])[:\s]+(\d+)',
        r'([A-F])\s*:\s*(\d+)',
        r'(\d+)\s*-\s*(\d+)\s*:\s*grade\s+([A-F])',
        r'(\d+)%\s*or\s*above\s*[:=]\s*([A-F])'
    ]
    
    boundaries = {}
    for pattern in grade_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if len(match) == 2:  # Grade: Score format
                grade, score = match
                try:
                    boundaries[grade.upper()] = int(score)
                except ValueError:
                    pass
            elif len(match) == 3:  # Score range: Grade format
                try:
                    if match[2].isalpha():  # Third value is the grade
                        boundaries[match[2].upper()] = (int(match[0]), int(match[1]))
                    else:  # First value is the grade
                        boundaries[match[0].upper()] = (int(match[1]), int(match[2]))
                except ValueError:
                    pass
    
    return boundaries

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
    
    # Extract content and print the result
    result = extract_answer_pdf(pdf_path)
    print(result)
