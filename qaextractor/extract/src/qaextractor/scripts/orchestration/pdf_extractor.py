"""
Module for extracting content from PDF files including text, tables, and images.
"""

import PyPDF2
import json
import sys
import re
import os
import base64
import io
import requests
from PIL import Image, ImageFilter
import traceback
import numpy as np
from pdf2image import convert_from_path
import cv2

def upload_image_to_imgbb(image_data, image_name):
    """
    Upload an image to ImgBB and return the URL.
    
    Args:
        image_data (bytes): Raw image data
        image_name (str): Name for the image
        
    Returns:
        str: URL to the uploaded image or None if upload failed
    """
    try:
        # ImgBB API key - you'll need to get a free API key from https://api.imgbb.com/
        api_key = "9bb6bd78cb6c03a2dfddce20b69cc45c"  # Replace with your actual API key
        
        # Encode the image data
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Prepare the payload
        payload = {
            'key': api_key,
            'image': base64_image,
            'name': image_name
        }
        
        # Make the request
        response = requests.post('https://api.imgbb.com/1/upload', payload)
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                return result['data']['url']
        
        return None
    except Exception as e:
        print(f"Error uploading image: {str(e)}")
        return None

def upload_pil_image_to_imgbb(pil_image, image_name):
    """
    Upload a PIL Image to ImgBB and return the URL.
    
    Args:
        pil_image (PIL.Image): PIL Image object
        image_name (str): Name for the image
        
    Returns:
        str: URL to the uploaded image or None if upload failed
    """
    try:
        # Convert PIL Image to bytes
        img_byte_arr = io.BytesIO()
        pil_image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # Upload using the existing function
        return upload_image_to_imgbb(img_byte_arr, image_name)
    except Exception as e:
        print(f"Error converting/uploading PIL image: {str(e)}")
        return None

def is_likely_graphic(image):
    """
    Advanced analysis to determine if an image section is likely to contain a graphic.
    Uses multiple heuristics to distinguish between text and graphical content.
    
    Args:
        image (PIL.Image): The image section to analyze
        
    Returns:
        bool: True if the section likely contains a graphic, False otherwise
    """
    try:
        # Convert to RGB if not already
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Get image dimensions
        width, height = image.size
        if width < 100 or height < 100:
            return False  # Too small to be a meaningful graphic
        
        
        # 1. Text Density Analysis
        # Convert to grayscale for text analysis
        gray_image = image.convert('L')
        gray_array = np.array(gray_image)
        
        # Calculate text-like pixel density
        # Text typically has a specific density pattern
        text_threshold = 200  # Threshold for what's considered text vs background
        text_pixels = np.sum(gray_array < text_threshold)
        total_pixels = gray_array.size
        text_density = text_pixels / total_pixels
        
        # If extremely sparse or extremely dense, probably not a graphic
        if text_density < 0.01 or text_density > 0.4:
            return False
        
        # 2. Color Diversity Analysis
        # Graphics often have more color diversity than text
        # Downsample image to reduce computation
        small_img = image.resize((50, 50), Image.LANCZOS)
        colors = small_img.getcolors(maxcolors=2500)
        
        if colors:
            unique_colors = len(colors)
            # Text typically has very few colors (often just 2-3)
            if unique_colors > 10:  # More colors suggests a graphic
                return True
        
        # 3. Edge Detection for Lines and Shapes
        # Graphics often have distinct edges, especially straight lines
        edges = gray_image.filter(ImageFilter.FIND_EDGES)
        edge_array = np.array(edges)
        edge_pixels = np.sum(edge_array > 50)  # Count significant edges
        edge_density = edge_pixels / total_pixels
        
        # High edge density in a structured pattern suggests a graphic
        if edge_density > 0.05:
            # 4. Line Detection (for charts, graphs)
            # Convert to OpenCV format
            cv_image = cv2.cvtColor(np.array(gray_image), cv2.COLOR_GRAY2BGR)
            edges_cv = cv2.Canny(cv_image, 50, 150, apertureSize=3)
            
            # Use Hough Transform to detect lines
            lines = cv2.HoughLinesP(edges_cv, 1, np.pi/180, threshold=100, 
                                   minLineLength=100, maxLineGap=10)
            
            # If we detect multiple straight lines, likely a chart/graph
            if lines is not None and len(lines) > 5:
                return True
        
        # 5. Text Line Pattern Analysis
        # Text has regular line spacing patterns
        # Calculate row-wise pixel density
        row_density = np.mean(gray_array < text_threshold, axis=1)
        
        # Calculate variation in density between rows
        # Text has a regular pattern of dense (text) and sparse (space between lines) rows
        density_diff = np.abs(np.diff(row_density))
        
        # High regular variation suggests text, not graphics
        if np.mean(density_diff) > 0.3 and np.std(density_diff) < 0.15:
            return False
        
        # 6. White Space Distribution
        # Graphics and tables have structured white space
        # Calculate the distribution of white space
        white_pixels = gray_array > 240
        white_ratio = np.sum(white_pixels) / total_pixels
        
        # Too much white space is likely just empty space
        if white_ratio > 0.9:
            return False
        
        # Combine all factors for final decision
        # This is a simplified scoring system - you might want to tune these weights
        score = 0
        
        # Color diversity adds to score
        if colors and len(colors) > 10:
            score += 2
        
        # Edge patterns add to score
        if edge_density > 0.05:
            score += 1
        
        # Line detection adds to score
        if lines is not None and len(lines) > 5:
            score += 3
        
        # Moderate text density adds to score
        if 0.05 < text_density < 0.3:
            score += 1
        
        # Return True if the combined score suggests a graphic
        return score >= 3
        
    except Exception as e:
        print(f"Error in graphic detection: {str(e)}")
        # Default to False on error
        return False

def extract_vector_graphics(pdf_path, page_num, text):
    """
    Extract potential vector graphics (graphs, charts) from a PDF page by
    rendering the page and identifying regions that might contain graphics.
    
    Args:
        pdf_path (str): Path to the PDF file
        page_num (int): Page number (0-based)
        text (str): Extracted text from the page to identify potential graphics
        
    Returns:
        list: List of dictionaries with information about extracted graphics
    """
    graphics = []
    
    try:
        # Look for potential figure references in the text
        figure_matches = re.finditer(r'(Figure|Fig\.?|Graph|Chart)\s*(\d+)', text, re.IGNORECASE)
        
        if not any(figure_matches):
            # No figure references found
            return graphics
        
        # Reset the iterator
        figure_matches = re.finditer(r'(Figure|Fig\.?|Graph|Chart)\s*(\d+)', text, re.IGNORECASE)
        
        # Convert the specific page to an image
        images = convert_from_path(pdf_path, first_page=page_num+1, last_page=page_num+1, dpi=200)
        
        if not images:
            return graphics
        
        page_image = images[0]
        width, height = page_image.size
        
        # For each figure reference, try to extract a region around it
        for match in figure_matches:
            figure_type = match.group(1)  # Figure, Fig, Graph, etc.
            figure_num = match.group(2)   # The number
            
            # Create a name for this graphic
            graphic_name = f"{figure_type}_{figure_num}"
            
            # For simplicity, we'll extract a portion of the page
            # In a real implementation, you'd want to use more sophisticated
            # heuristics to determine the exact region of the graphic
            
            # Simple approach: divide the page into quarters and take the quarter
            # where the figure reference appears
            match_pos = match.start() / len(text)  # Approximate position in text
            
            # Determine which quarter of the page to extract
            if match_pos < 0.25:
                # Top quarter
                crop_box = (0, 0, width, height // 2)
            elif match_pos < 0.5:
                # Second quarter
                crop_box = (0, height // 4, width, 3 * height // 4)
            elif match_pos < 0.75:
                # Third quarter
                crop_box = (0, height // 2, width, height)
            else:
                # Bottom quarter
                crop_box = (0, 3 * height // 4, width, height)
            
            # Crop the image
            cropped_image = page_image.crop(crop_box)
            
            # Only proceed if this looks like a graphic
            if is_likely_graphic(cropped_image):
                # Upload the cropped image
                image_name = f"pdf_figure_{page_num+1}_{figure_type}_{figure_num}"
                image_url = upload_pil_image_to_imgbb(cropped_image, image_name)
                
                # Create graphic info
                graphic_info = {
                    "name": graphic_name,
                    "page": page_num + 1,
                    "type": "vector_graphic",
                    "description": f"{figure_type} {figure_num}",
                    "debug": [f"Extracted from page {page_num+1} at position {match_pos:.2f}"]
                }
                
                if image_url:
                    graphic_info["url"] = image_url
                    graphic_info["debug"].append(f"Uploaded to {image_url}")
                else:
                    graphic_info["debug"].append("Failed to upload graphic")
                
                graphics.append(graphic_info)
        
    except Exception as e:
        print(f"Error extracting vector graphics: {str(e)}")
    
    return graphics

def extract_all_potential_graphics(pdf_path, page_num):
    """
    Extract all potential graphics from a PDF page by rendering the entire page
    and dividing it into sections that might contain visual elements.
    
    Args:
        pdf_path (str): Path to the PDF file
        page_num (int): Page number (0-based)
        
    Returns:
        list: List of dictionaries with information about extracted graphics
    """
    graphics = []
    
    try:
        # Convert the specific page to an image
        images = convert_from_path(pdf_path, first_page=page_num+1, last_page=page_num+1, dpi=200)
        
        if not images:
            return graphics
        
        page_image = images[0]
        width, height = page_image.size
        
        # Check if the entire page might be a graphic
        if is_likely_graphic(page_image):
            # Upload the entire page
            image_name = f"pdf_full_page_{page_num+1}"
            image_url = upload_pil_image_to_imgbb(page_image, image_name)
            
            if image_url:
                graphic_info = {
                    "name": f"full_page_{page_num+1}",
                    "page": page_num + 1,
                    "type": "full_page",
                    "description": f"Full page {page_num+1}",
                    "debug": [f"Extracted entire page {page_num+1}"]
                }
                graphic_info["url"] = image_url
                graphics.append(graphic_info)
                
                # If we've captured the full page as a graphic, no need to check sections
                return graphics
        
        # Divide the page into a grid
        num_rows = 3
        num_cols = 2
        
        for row in range(num_rows):
            for col in range(num_cols):
                # Calculate the crop box for this grid cell
                left = col * (width // num_cols)
                upper = row * (height // num_rows)
                right = (col + 1) * (width // num_cols)
                lower = (row + 1) * (height // num_rows)
                
                crop_box = (left, upper, right, lower)
                
                # Crop the image
                cropped_image = page_image.crop(crop_box)
                
                # Check if this section might contain a graphic
                if is_likely_graphic(cropped_image):
                    # Create a name for this graphic
                    graphic_name = f"section_{page_num+1}_{row}_{col}"
                    
                    # Upload the cropped image
                    image_name = f"pdf_graphic_{page_num+1}_{row}_{col}"
                    image_url = upload_pil_image_to_imgbb(cropped_image, image_name)
                    
                    # Create graphic info
                    graphic_info = {
                        "name": graphic_name,
                        "page": page_num + 1,
                        "type": "potential_graphic",
                        "description": f"Potential graphic from page {page_num+1}, section {row+1}x{col+1}",
                        "position": {"row": row, "col": col},
                        "debug": [f"Extracted from page {page_num+1}, grid position {row}x{col}"]
                    }
                    
                    if image_url:
                        graphic_info["url"] = image_url
                        graphic_info["debug"].append(f"Uploaded to {image_url}")
                    else:
                        graphic_info["debug"].append("Failed to upload graphic")
                    
                    graphics.append(graphic_info)
    
    except Exception as e:
        print(f"Error extracting potential graphics: {str(e)}")
    
    return graphics

def extract_pdf_content(pdf_path):
    """
    Extract text, tables, images, and vector graphics from all pages of a PDF file.
    
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
                "images": [],
                "graphics": [],  # Field for vector graphics and other visual elements
                "debug_info": []
            }
            
            # Add overall debug info
            result["debug_info"].append(f"PDF has {len(pdf.pages)} pages")
            
            # Add these variables at the beginning of the function
            last_question_number = None
            
            # Process each page
            for page_num, page in enumerate(pdf.pages):
                page_info = {
                    "page_number": page_num + 1,
                    "text": "",
                    "images": [],
                    "graphics": [],
                    "debug": []
                }
                
                # Debug: Check if Resources and XObject exist
                has_resources = '/Resources' in page
                has_xobject = has_resources and '/XObject' in page['/Resources']
                page_info["debug"].append(f"Has Resources: {has_resources}, Has XObject: {has_xobject}")
                
                # Extract text
                page_text = page.extract_text()
                page_info["debug"].append(f"Extracted text length: {len(page_text)}")
                
                # Check if this is a cover page
                is_cover_page = is_likely_cover_page(page_num, len(page_text))
                
                # Update the last question number if found
                question_number = find_last_question_number(page_text)
                if question_number:
                    last_question_number = question_number
                
                # Clean the text to remove problematic characters
                page_text = re.sub(r'[\\"]', ' ', page_text)
                
                # Add to overall text and page-specific text
                result["text"] += page_text + "\n\n"
                page_info["text"] = page_text
                
                # Extract images if available
                if has_xobject:
                    xobjects = page['/Resources']['/XObject']
                    page_info["debug"].append(f"Found {len(xobjects)} XObjects")
                    
                    for obj_name in xobjects:
                        obj = xobjects[obj_name]
                        is_image = obj['/Subtype'] == '/Image' if '/Subtype' in obj else False
                        page_info["debug"].append(f"XObject {obj_name} is image: {is_image}")
                        
                        if is_image:
                            # Get image info
                            img_info = {
                                "name": obj_name,
                                "width": obj['/Width'] if '/Width' in obj else 'unknown',
                                "height": obj['/Height'] if '/Height' in obj else 'unknown',
                                "page": page_num + 1,
                                "format": "unknown",
                                "debug": []
                            }
                            
                            try:
                                # Try to extract the image data
                                has_get_data = hasattr(obj, "get_data")
                                has_data = hasattr(obj, "_data")
                                img_info["debug"].append(f"Has get_data: {has_get_data}, Has _data: {has_data}")
                                
                                if has_get_data:
                                    raw_data = obj.get_data()
                                    img_info["debug"].append(f"Used get_data(), got {len(raw_data)} bytes")
                                elif has_data:
                                    raw_data = obj._data
                                    img_info["debug"].append(f"Used _data, got {len(raw_data)} bytes")
                                else:
                                    img_info["debug"].append("No data extraction method available")
                                    raw_data = None
                                
                                # Determine image format
                                if '/Filter' in obj:
                                    filter_type = obj['/Filter']
                                    img_info["debug"].append(f"Filter type: {filter_type}")
                                    if filter_type == '/DCTDecode':
                                        img_info["format"] = "jpeg"
                                    elif filter_type == '/FlateDecode':
                                        img_info["format"] = "png"
                                    elif filter_type == '/JPXDecode':
                                        img_info["format"] = "jp2"
                                
                                # Upload image if we have data
                                if raw_data:
                                    # Upload to ImgBB
                                    image_name = f"pdf_image_{page_num+1}_{obj_name.replace('/', '_')}"
                                    image_url = upload_image_to_imgbb(raw_data, image_name)
                                    
                                    if image_url:
                                        img_info["url"] = image_url
                                        img_info["debug"].append(f"Uploaded to {image_url}")
                                    else:
                                        img_info["debug"].append("Failed to upload image")
                                        
                                        # Fallback to base64 (just a small sample)
                                        img_base64 = base64.b64encode(raw_data).decode('utf-8')
                                        img_info["base64_sample"] = img_base64[:100] + "..." if len(img_base64) > 100 else img_base64
                                else:
                                    img_info["debug"].append("No data to upload")
                                
                                # Add image reference to the text
                                if is_cover_page:
                                    img_marker = f"\n[COVER IMAGE: {obj_name} on page {page_num + 1}, {img_info.get('width', '?')}x{img_info.get('height', '?')}]\n"
                                elif last_question_number:
                                    img_marker = f"\n[IMAGE for Q{last_question_number}: {obj_name} on page {page_num + 1}, {img_info.get('width', '?')}x{img_info.get('height', '?')}]\n"
                                else:
                                    img_marker = f"\n[IMAGE: {obj_name} on page {page_num + 1}, {img_info.get('width', '?')}x{img_info.get('height', '?')}]\n"
                                result["text"] += img_marker
                                page_info["text"] += img_marker
                                
                                # Add to images list
                                page_info["images"].append(img_info)
                                result["images"].append(img_info)
                            except Exception as e:
                                img_info["extraction_error"] = str(e)
                                img_info["debug"].append(f"Exception during extraction: {str(e)}")
                                page_info["images"].append(img_info)
                                result["debug_info"].append(f"Error extracting image {obj_name}: {str(e)}")
                
                # Extract all potential graphics from the page
                graphics = extract_all_potential_graphics(pdf_path, page_num)
                
                # Also try the keyword-based approach as a fallback
                keyword_graphics = extract_vector_graphics(pdf_path, page_num, page_text)
                graphics.extend(keyword_graphics)
                
                if graphics:
                    for graphic in graphics:
                        # Add context to the graphic
                        graphic["last_question"] = last_question_number
                        graphic["is_cover"] = is_cover_page
                        
                        # Add graphic reference to the text with context
                        if is_cover_page:
                            graphic_marker = f"\n[COVER GRAPHIC: {graphic['name']} on page {page_num + 1}]\n"
                        elif last_question_number:
                            graphic_marker = f"\n[GRAPHIC for Q{last_question_number}: {graphic['name']} on page {page_num + 1}]\n"
                        else:
                            graphic_marker = f"\n[GRAPHIC: {graphic['name']} on page {page_num + 1}]\n"
                        result["text"] += graphic_marker
                        page_info["text"] += graphic_marker
                        
                        # Add to graphics lists
                        page_info["graphics"].append(graphic)
                        result["graphics"].append(graphic)
                
                # Look for potential tables in the text
                table_markers = re.findall(r'(Table|Tab\.?)\s*\d+', page_text, re.IGNORECASE)
                if table_markers:
                    page_info["potential_tables"] = table_markers
                
                # Add page info to result
                result["pages"].append(page_info)
            
            # Detect potential figures and tables in the overall text
            result["figure_references"] = re.findall(r'(Figure|Fig\.?)\s*\d+', result["text"], re.IGNORECASE)
            result["table_references"] = re.findall(r'(Table|Tab\.?)\s*\d+', result["text"], re.IGNORECASE)
            
            # Return the extracted content as JSON
            return json.dumps(result)
            
    except Exception as e:
        return json.dumps({"error": str(e), "traceback": traceback.format_exc()})

# Add this function to detect question numbers in text
def find_last_question_number(text):
    """
    Find the last question number in the text.
    
    Args:
        text (str): Text to search for question numbers
        
    Returns:
        str or None: The last question number found, or None if no questions found
    """
    # Look for common question patterns
    question_matches = re.findall(r'(?:Question|Q\.?)\s*(\d+)', text, re.IGNORECASE)
    numbered_matches = re.findall(r'^\s*(\d+)\.\s', text, re.MULTILINE)
    
    # Combine all matches
    all_matches = question_matches + numbered_matches
    
    # Return the last match if any were found
    if all_matches:
        return all_matches[-1]
    return None

# Add this function to detect if a page is likely a cover page
def is_likely_cover_page(page_num, text_length):
    """
    Determine if a page is likely to be a cover page.
    
    Args:
        page_num (int): Page number (0-based)
        text_length (int): Length of text on the page
        
    Returns:
        bool: True if the page is likely a cover page
    """
    # First page with minimal text is likely a cover
    return page_num == 0 and text_length < 500

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
    result = extract_pdf_content(pdf_path)
    print(result) 