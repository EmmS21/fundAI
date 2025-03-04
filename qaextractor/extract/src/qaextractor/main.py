import dagger
from dagger import dag, function, object_type, Secret
import os
import json
import pymongo
from pymongo.errors import AutoReconnect, OperationFailure
import pathlib
import re
from .tools.pdf_tools_module import PdfTools

@object_type
class Qaextractor:
    @function
    # def hello(self, credentials_json: Secret) -> str:
    #     """Simple test function"""
    #     return str(credentials_json)
    
    @function
    async def getlevel(self, credentials_json: Secret) -> str:
        """Lists folders in root directory to identify education levels"""
        
        script_path = pathlib.Path(__file__).parent / "scripts" / "drive" / "list_levels.py"
        with open(script_path, "r") as f:
            script_content = f.read()
        
        return await (
            dag.container()
            .from_("python:3.12-slim")
            .with_exec(["pip", "install", "google-api-python-client", "google-auth"])
            .with_new_file("/app/credentials.json", contents=credentials_json)
            .with_new_file("/app/list_levels.py", contents=script_content)
            .with_workdir("/app")
            .with_exec(["python", "list_levels.py"])
            .stdout()
        )

    @function
    async def extract(self, credentials_json: Secret) -> str:
        """Maps out complete folder structure and parses paper names"""
        
        script_path = pathlib.Path(__file__).parent / "scripts" / "drive" / "map_structure.py"
        with open(script_path, "r") as f:
            script_content = f.read()
        
        return await (
            dag.container()
            .from_("python:3.12-slim")
            .with_exec(["pip", "install", "google-api-python-client", "google-auth"])
            .with_new_file("/app/credentials.json", contents=credentials_json)
            .with_new_file("/app/map_structure.py", contents=script_content)
            .with_workdir("/app")
            .with_exec(["python", "map_structure.py"])
            .stdout()
        )

    @function
    def test(self, string_arg: str) -> dagger.Container:
        """Returns a container that echoes whatever string argument is provided"""
        return dag.container().from_("alpine:latest").with_exec(["echo", string_arg])

    @function
    async def grep_dir(self, directory_arg: dagger.Directory, pattern: str) -> str:
        """Returns lines that match a pattern in the files of the provided Directory"""
        return await (
            dag.container()
            .from_("alpine:latest")
            .with_mounted_directory("/mnt", directory_arg)
            .with_workdir("/mnt")
            .with_exec(["grep", "-R", pattern, "."])
            .stdout()
        )

    @function
    async def authenticate(self, collection: str, connection_string: Secret) -> str:
        """Authenticates with MongoDB and returns success message."""
        database = "fundaAI" 
        
        if not connection_string:
            return "Error: MONGODB_URI environment variable not set"
        
        # Get the plaintext value from the Secret - note the await
        connection_string_value = await connection_string.plaintext()
        
        max_retries = 3
        retries = 0
        while retries < max_retries:
            try:
                client = pymongo.MongoClient(connection_string_value)
                db = client[database]
                collection = db[collection]
                # Test the connection
                client.admin.command('ping')
                return f"Success: Connected to MongoDB collection '{collection}'"
            except AutoReconnect as e:
                retries += 1
                if retries == max_retries:
                    return f"Failed to connect to MongoDB after {max_retries} retries: {e}"
            except OperationFailure as e:
                return f"Failed to authenticate with MongoDB: {e}"

    @function
    def design_document_structure(self) -> str:
        """Returns the document structure design for pp-questions collection"""
        
        script_path = pathlib.Path(__file__).parent / "scripts" / "mongodb" / "document.py"
        with open(script_path, "r") as f:
            document_module = {}
            exec(f.read(), document_module)
        
        document_structure = document_module["get_document_structure"]()
        example = document_module["get_example_document"]()
        indexes = document_module["get_recommended_indexes"]()
        
        return f"""
# MongoDB Document Structure for pp-questions Collection

## Base Document Structure
```json
{document_structure}
```

## Example Document
```json
{example}
```

## Recommended Indexes
```json
{indexes}
```

## Notes:
1. The 'Questions' array will be populated during processing
2. 'FolderStructure' maintains the full path for reference
3. 'Processed' flag helps track extraction progress
4. 'Status' field allows for more detailed processing state
5. 'Metadata' section stores extraction statistics
6. 'ErrorLog' captures any issues during processing
"""

    @function
    async def process_education_level(self, credentials_json: Secret, connection_string: Secret, level_name: str, level_id: str) -> str:
        """Process a single education level and create MongoDB documents for both questions and answers"""
        
        # Get plaintext value from the Secret
        credentials_json_value = await credentials_json.plaintext()
        connection_string_value = await connection_string.plaintext()
        
        # Load scripts
        script_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "process_level.py"
        constants_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "constants.py"
        
        with open(script_path, "r") as f:
            script_content = f.read()
            
        with open(constants_path, "r") as f:
            constants_content = f.read()
        
        return await (
            dag.container()
            .from_("python:3.12-slim")
            .with_exec(["pip", "install", "google-api-python-client", "google-auth", "pymongo"])
            .with_new_file("/app/credentials.json", contents=credentials_json_value)
            .with_new_file("/app/process_level.py", contents=script_content)
            .with_new_file("/app/constants.py", contents=constants_content)
            .with_env_variable("MONGODB_URI", connection_string_value)
            .with_workdir("/app")
            .with_exec(["python", "process_level.py", level_name, level_id, connection_string_value])
            .stdout()
        )


    # @function
    # def hello(self) -> str:
    #     """Simple test function"""
    #     return "hello world"

    @function
    async def orchestrate(self, credentials_json: Secret, connection_string: Secret) -> str:
        """Main orchestrator function that processes all education levels"""
        # Load constants
        constants_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "constants.py"
        constants_module = {}
        with open(constants_path, "r") as f:
            exec(f.read(), constants_module)
        
        # Get education levels from constants
        education_levels = constants_module["EDUCATION_LEVELS"]
        create_level_result = constants_module["create_level_result"]
        
        # First verify MongoDB connection
        auth_result = await self.authenticate("pp-questions", connection_string)
        if not auth_result.startswith("Success"):
            return f"Failed to connect to MongoDB: {auth_result}"
        
        # Process each education level
        results = []
        total_documents = 0
        total_errors = 0
        
        for level_name, level_id in education_levels.items():
            try:
                # Process this level
                level_result_json = await self.process_education_level(
                    credentials_json, 
                    connection_string, 
                    level_name, 
                    level_id
                )
                
                # Parse the result
                level_result = json.loads(level_result_json)
                
                # Add to totals
                total_documents += level_result.get("documents_created", 0)
                total_errors += level_result.get("errors", 0)
                
                # Add to results using helper function from constants
                results.append(create_level_result(
                    level_name,
                    level_result.get("documents_created", 0),
                    level_result.get("errors", 0),
                    level_result.get("error_details", [])
                ))
                
            except Exception as e:
                # Add error result using helper function from constants
                results.append(create_level_result(
                    level_name, 
                    0, 
                    1, 
                    [f"Failed to process level: {str(e)}"]
                ))
                total_errors += 1
        
        # Create summary
        summary = {
            "total_documents_created": total_documents,
            "total_errors": total_errors,
            "level_results": results
        }
        
        return json.dumps(summary, indent=2)

    @function
    async def single(self, credentials_json: Secret, file_id: str) -> str:
        """Extract a single question from a PDF file using LLM processing"""
        
        # Get plaintext value from the Secret
        credentials_json_value = await credentials_json.plaintext()
        
        # Load the llm_extraction.py script
        llm_extraction_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "llm_extraction.py"
        
        with open(llm_extraction_path, "r") as f:
            script_content = f.read()
        
        # Download the PDF
        download_container = (
            dag.container()
            .from_("python:3.12-slim")
            .with_exec(["pip", "install", "google-api-python-client", "google-auth"])
            .with_new_file("/app/credentials.json", contents=credentials_json_value)
            .with_new_file("/app/llm_extraction.py", contents=script_content)
            .with_workdir("/app")
            .with_exec(["python", "llm_extraction.py", file_id])
        )
        
        # Get the download result
        download_result_json = await download_container.stdout()
        
        # Debug: Print the download result
        print(f"DEBUG: Download result: {download_result_json[:200]}...")
        
        try:
            download_result = json.loads(download_result_json)
            
            if not download_result.get("success", False):
                return json.dumps({
                    "success": False,
                    "error": download_result.get("error", "Unknown error during PDF download")
                })
            
            # Important: Export the file from the container
            pdf_file = (
                download_container
                .file("/app/exam.pdf")
            )
            
            # Extract text from the PDF first to avoid passing raw PDF content
            # First, read the content of the pdf_extractor.py file
            pdf_extractor_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "pdf_extractor.py"
            with open(pdf_extractor_path, "r") as f:
                pdf_extractor_content = f.read()

            # Now use the content with with_new_file instead of with_file
            pdf_text_container = (
                dag.container()
                .from_("python:3.12-slim")
                .with_exec(["pip", "install", "PyPDF2", "Pillow"])
                .with_file("/app/exam.pdf", pdf_file)
                .with_new_file("/app/pdf_extractor.py", contents=pdf_extractor_content)
                .with_workdir("/app")
                .with_exec(["python", "pdf_extractor.py", "exam.pdf"])
            )
            
            # Get the PDF text extraction result
            pdf_text_json = await pdf_text_container.stdout()

            # Parse the PDF text extraction result
            pdf_text_data = json.loads(pdf_text_json)

            # Create a pdfextractor instance
            pdf_extractor = dag.pdfextractor()

            # Now use the LLM with the pdfextractor module
            question_extractor = (
                dag.llm()
                .with_pdfextractor(pdf_extractor)
                .with_prompt(f"""
                The following text is from an exam paper:
                
                {pdf_text_data['text']}
                
                Analyze this text and extract ALL questions in the exam paper, including their full context. For each question:
                
                You have access to a PDF extraction tool that can help you analyze the document:
                - Use the extract(pdf_path, page_number) function to extract a specific page from the PDF as a base64-encoded image
                  - pdf_path should be the path to the PDF file (use "/src/test.pdf")
                  - page_number is the page number to extract (1-based index, so the first page is 1)
                
                For example, to extract the first page of the PDF:
                ```
                extract("/src/test.pdf", 1)
                ```
                
                This will return a base64-encoded string of the page image, which you can analyze to identify visual elements.
                
                1. Identify the question number
                2. Extract the complete question text
                3. Extract any associated texts, passages, or materials that are part of the question (like Text A, B, C)
                4. Note any sub-questions
                5. Identify tables (describe their content)
                6. Note any images or visual elements that you can detect
                7. Determine how many marks the question is worth
                
                IMPORTANT: Many exam questions include associated texts, passages, or materials that students need to analyze. These are part of the question and should be included in your extraction.
                                
                IMPORTANT: When extracting context materials, be careful to distinguish between:
                - Actual text passages that should be included in "content"
                - Images, charts, or graphs that should be identified as images, not treated as text
                
                For example, if "Text C" is actually a graph or chart, it should be categorized as an image in the "images" array, not as text in "context_materials".
                
                Return ONLY a JSON object with this structure:
                {{
                  "total_questions": 5,
                  "questions": [
                    {{
                      "question_number": 1,
                      "question_text": "Full text of the question prompt",
                      "context_materials": [
                        {{
                          "label": "Text A",
                          "content": "Full text of passage A...",
                          "description": "An extract from a book of recipes from 1739",
                          "type": "text"  // Use "text" for text passages
                        }}
                      ],
                      "sub_questions": [
                        {{
                          "sub_number": "a",
                          "text": "Text of sub-question a",
                          "marks": 5
                        }}
                      ],
                      "tables": [
                        {{
                          "description": "Table showing data about X"
                        }}
                      ],
                      "images": [
                        {{
                          "label": "Text C",  // If a "Text" label refers to an image, include it here
                          "description": "Graph showing relationship between X and Y",
                          "base64_data": "Optional: Include the base64 data if you extracted it"
                        }}
                      ],
                      "marks": 15
                    }}
                  ]
                }}
                
                No other text or formatting.
                """)
            )
            
            # Get the extracted questions
            questions_json = await question_extractor.last_reply()
            
            # Clean the response to ensure it's valid JSON
            cleaned_json = questions_json.strip()

            # Extract JSON from markdown code blocks if present
            json_pattern = r'```(?:json)?\s*([\s\S]*?)```'
            json_matches = re.findall(json_pattern, cleaned_json)
            if json_matches:
                cleaned_json = json_matches[0].strip()
            else:
                # If no code blocks, try to find JSON object directly
                json_object_pattern = r'(\{[\s\S]*\})'
                object_matches = re.findall(json_object_pattern, cleaned_json)
                if object_matches:
                    cleaned_json = object_matches[0].strip()

            # Parse the JSON response
            questions_data = json.loads(cleaned_json)
            
            # Return the result
            return json.dumps({
                "success": True,
                "file_id": file_id,
                "file_name": download_result.get("file_name", ""),
                "total_questions": questions_data.get("total_questions", 0),
                "extracted_questions": questions_data.get("questions", [])
            }, indent=2)
            
        except Exception as e:
            # Catch all exceptions for better debugging
            import traceback
            error_traceback = traceback.format_exc()
            
            return json.dumps({
                "success": False,
                "error": f"Error during LLM processing: {str(e)}",
                "traceback": error_traceback,
                "raw_response": questions_json if 'questions_json' in locals() else "No response"
            })
            