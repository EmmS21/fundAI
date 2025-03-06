import unittest
import pymongo
import os
import datetime
from unittest.mock import patch, MagicMock

# Import the module to test
from src.qaextractor.scripts.orchestration.extraction_pipeline import (
    connect_to_mongodb,
    find_unprocessed_documents,
    process_document,
    process_batch
)

class TestExtractionPipeline(unittest.TestCase):
    """Test cases for the extraction pipeline"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock MongoDB connection
        self.mock_db = MagicMock()
        self.mock_collection = MagicMock()
        self.mock_db.__getitem__.return_value = self.mock_collection
        
        # Sample document
        self.sample_document = {
            "_id": "sample_id",
            "FileID": "sample_file_id",
            "FileName": "sample.pdf",
            "Level": "ASLevel",
            "Subject": "Mathematics",
            "Year": "2021",
            "Paper": 1,
            "Term": "June",
            "Processed": False,
            "Status": "pending"
        }
        
        # Sample extracted data
        self.sample_extracted_data = {
            "extracted_questions": [
                {
                    "question_id": "Q1-1",
                    "question_number": 1,
                    "question_text": "Sample question text",
                    "marks": 10
                }
            ]
        }
    
    @patch('pymongo.MongoClient')
    def test_connect_to_mongodb(self, mock_client):
        """Test MongoDB connection"""
        mock_client.return_value = {"fundaAI": "db_instance"}
        db = connect_to_mongodb("mongodb://localhost")
        self.assertEqual(db, "db_instance")
        mock_client.assert_called_once_with("mongodb://localhost")
    
    def test_find_unprocessed_documents(self):
        """Test finding unprocessed documents"""
        self.mock_collection.find.return_value.limit.return_value = [self.sample_document]
        
        documents = find_unprocessed_documents(self.mock_db)
        
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0], self.sample_document)
        self.mock_collection.find.assert_called_once()
    
    @patch('src.qaextractor.scripts.orchestration.extraction_pipeline.download_pdf')
    @patch('src.qaextractor.scripts.orchestration.extraction_pipeline.extract_pdf_content')
    @patch('src.qaextractor.scripts.orchestration.extraction_pipeline.extract_questions_with_llm')
    def test_process_document_success(self, mock_extract_llm, mock_extract_content, mock_download):
        """Test successful document processing"""
        # Setup mocks
        mock_download.return_value = "path/to/pdf"
        mock_extract_content.return_value = "PDF content"
        mock_extract_llm.return_value = self.sample_extracted_data
        
        self.mock_collection.insert_one.return_value = MagicMock(inserted_id="new_id")
        
        # Call function
        result = process_document(self.mock_db, self.sample_document, "temp_dir")
        
        # Assertions
        self.assertTrue(result["success"])
        self.assertEqual(result["document_id"], "sample_id")
        self.assertEqual(result["extracted_id"], "new_id")
        self.assertEqual(result["question_count"], 1)
        
        # Verify MongoDB operations
        self.mock_collection.insert_one.assert_called_once()
        self.mock_collection.update_one.assert_called_once()
    
    @patch('src.qaextractor.scripts.orchestration.extraction_pipeline.download_pdf')
    def test_process_document_error(self, mock_download):
        """Test document processing with error"""
        # Setup mock to raise exception
        mock_download.side_effect = Exception("Test error")
        
        # Call function
        result = process_document(self.mock_db, self.sample_document, "temp_dir")
        
        # Assertions
        self.assertFalse(result["success"])
        self.assertEqual(result["document_id"], "sample_id")
        self.assertEqual(result["error"], "Test error")
        
        # Verify MongoDB operations
        self.mock_collection.update_one.assert_called_once()

if __name__ == '__main__':
    unittest.main() 