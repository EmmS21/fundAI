"""
metadata_parser.py

Purpose: Parse book filenames to extract metadata (title, author)
Handles various filename patterns:
- Title - Author.pdf
- Title_with_underscores - Author.pdf
- Title (Year) - Author.pdf
"""

import re
from typing import Dict

class BookMetadataParser:
    def __init__(self):
        # Common patterns for book filenames
        self.patterns = [
            # Basic pattern without year
            r'^(.+?)\s*-\s*([^.(]+)\.pdf$',                         # Title - Author.pdf
            
            # Year in title patterns
            r'^(.+?)\s*\((\d{4})\)\s*-\s*([^.]+)\.pdf$',           # Title (Year) - Author.pdf
            r'^(.+?)\s*-\s*([^(]+)\s*\((\d{4})\)\.pdf$',           # Title - Author (Year).pdf
            r'^(.+?)\s*\((\d{4})\)\s*-\s*([^.]+)\.pdf$',           # Title (Year) - Author.pdf
            r'^(.+?)\[.+?\]\s*\((\d{4})\)\.pdf$',                  # LLM papers: Title[Tag] (Year).pdf
        ]
        
        # Additional pattern to find year anywhere in the filename
        self.year_pattern = r'\((\d{4})\)'

    def parse_filename(self, filename: str) -> Dict[str, str]:
        """
        Parse a filename to extract book metadata.
        
        Args:
            filename: String containing the book filename
            
        Returns:
            Dictionary containing extracted metadata:
            {
                'title': str,
                'author': str,
                'year': Optional[str],
                'original_filename': str
            }
            
        Raises:
            ValueError: If filename doesn't match expected patterns
        """
        # First try to match the full patterns
        for pattern in self.patterns:
            match = re.match(pattern, filename)
            if match:
                groups = match.groups()
                
                # Extract components based on pattern
                if len(groups) == 2:  # Basic pattern
                    title, author = groups
                    # Look for year separately
                    year_match = re.search(self.year_pattern, filename)
                    year = year_match.group(1) if year_match else None
                elif '[' in groups[0]:  # LLM papers
                    title, year = groups
                    author = None
                else:  # Patterns with year
                    if '(' in groups[0]:  # Year in title
                        title, year, author = groups
                    else:  # Year in author
                        title, author, year = groups
                
                # Clean up title and author
                title = re.sub(r'\s*\(\d{4}\)', '', title).replace('_', ' ').strip()
                if author:
                    author = re.sub(r'\s*\(\d{4}\)', '', author).replace('_', ' ').strip()
                
                return {
                    'title': title,
                    'author': author,
                    'year': year,
                    'original_filename': filename
                }
        
        # If no pattern matches, try to extract basic title-author and find year separately
        basic_match = re.match(r'^(.+?)\s*-\s*([^.]+)\.pdf$', filename)
        if basic_match:
            title, author = basic_match.groups()
            year_match = re.search(self.year_pattern, filename)
            year = year_match.group(1) if year_match else None
            
            # Clean up title and author
            title = re.sub(r'\s*\(\d{4}\)', '', title).replace('_', ' ').strip()
            author = re.sub(r'\s*\(\d{4}\)', '', author).replace('_', ' ').strip()
            
            return {
                'title': title,
                'author': author,
                'year': year,
                'original_filename': filename
            }
        
        raise ValueError(f"Filename '{filename}' doesn't match expected patterns")

    def parse_drive_file(self, file_metadata: Dict) -> Dict:
        """
        Parse Google Drive file metadata and extract book information.
        
        Args:
            file_metadata: Dictionary containing Google Drive file metadata
            
        Returns:
            Dictionary containing combined metadata:
            {
                'title': str,
                'author': str,
                'year': Optional[str],
                'drive_id': str,
                'drive_link': str,
                'created_time': str,
                'modified_time': str,
                'original_filename': str
            }
        """
        filename = file_metadata.get('name', '')
        book_metadata = self.parse_filename(filename)
        
        return {
            **book_metadata,
            'drive_id': file_metadata.get('id'),
            'drive_link': f"https://drive.google.com/file/d/{file_metadata.get('id')}/view",
            'created_time': file_metadata.get('createdTime'),
            'modified_time': file_metadata.get('modifiedTime')
        }


def main():
    """Test the parser with sample filenames"""
    parser = BookMetadataParser()
    
    # Test cases
    test_files = [
        "3D_Game_Programming_for_Kids_Create_Interactive_Worlds_with_JavaScript - Chris Strom.pdf",
        "A History of Transhumanist Thought (2005) - Nick Bostrom.pdf",
        "Atlas_Shrugged-Ayn_Rand.pdf",
        "Godel_Escher_Bach_An Eternal Golden Braid (1979) - Douglas Hofstadter.pdf",
        "attentionisallyouneed[LLM] (2017).pdf",
        "3D_Game_Programming_for_Kids_Create_Interactive_Worlds_with_JavaScript (2013)- Chris Strom.pdf",
        "Atlas_Shrugged-Ayn_Rand (1957).pdf"
    ]
    
    for filename in test_files:
        try:
            metadata = parser.parse_filename(filename)
            print(f"\nParsed: {filename}")
            print("Metadata:", metadata)
        except ValueError as e:
            print(f"\nError parsing {filename}: {str(e)}")

if __name__ == "__main__":
    main()
