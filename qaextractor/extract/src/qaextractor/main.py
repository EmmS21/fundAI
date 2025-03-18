import dagger
from dagger import dag, function, object_type, Secret
import json
import pymongo
from pymongo.errors import AutoReconnect, OperationFailure
import pathlib
import re
from typing import Optional
import os
import time

# Increase timeout to 10 minutes (600 seconds)
dagger.Config(timeout=600)

@object_type
class Qaextractor:
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
    async def single(self, credentials_json: Secret, file_id: str, file_name: Optional[str] = None, document_type: str = "questions") -> str:
        """Extract questions or answers from a PDF file using LLM processing
        
        Args:
            credentials_json: Google credentials for accessing Drive
            file_id: The Google Drive file ID
            file_name: Optional file name
            document_type: Type of document to process ("questions" or "answers")
        """
        
        # Get plaintext value from the Secret
        credentials_json_value = await credentials_json.plaintext()
        
        # Load the llm_extraction.py script
        llm_extraction_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "llm_extraction.py"
        
        with open(llm_extraction_path, "r") as f:
            script_content = f.read()
        
        # Use a default filename if none provided
        if file_name is None:
            file_name = f"document_{file_id[-8:]}"
        
        # Download the PDF
        download_container = (
            dag.container()
            .from_("python:3.12-slim")
            .with_exec(["pip", "install", "google-api-python-client", "google-auth"])
            .with_new_file("/app/credentials.json", contents=credentials_json_value)
            .with_new_file("/app/llm_extraction.py", contents=script_content)
            .with_workdir("/app")
            .with_exec(["python", "llm_extraction.py", file_id, "/app", file_name])
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
            pdf_path = download_result.get("pdf_path")
            pdf_file = await download_container.file(pdf_path)
            
            # Extract text from the PDF based on document type
            if document_type.lower() == "answers":
                # Use our specialized answer_pdf_extractor.py for answer documents
                answer_extractor_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "answer_pdf_extractor.py"
                with open(answer_extractor_path, "r") as f:
                    answer_extractor_content = f.read()
                
                # Create a container with the answer extractor
                pdf_text_container = (
                    dag.container()
                    .from_("python:3.12-slim")
                    .with_exec(["apt-get", "update"])
                    .with_exec(["apt-get", "install", "-y", "poppler-utils"])  # Minimal dependencies
                    .with_exec(["pip", "install", "PyPDF2", "pdf2image", "pillow"])
                    .with_file("/app/exam.pdf", pdf_file)
                    .with_new_file("/app/answer_pdf_extractor.py", contents=answer_extractor_content)
                    .with_workdir("/app")
                    .with_exec(["python", "answer_pdf_extractor.py", "exam.pdf"])
                )
            else:
                # For question documents, use the original pdf_extractor.py
                pdf_extractor_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "pdf_extractor.py"
                with open(pdf_extractor_path, "r") as f:
                    pdf_extractor_content = f.read()
                
                # Now use the content with with_new_file instead of with_file
                pdf_text_container = (
                    dag.container()
                    .from_("python:3.12-slim")
                    .with_exec(["apt-get", "update"])
                    .with_exec(["apt-get", "install", "-y", "libgl1-mesa-glx", "libglib2.0-0", "poppler-utils"])
                    .with_exec(["pip", "install", "PyPDF2", "pdf2image", "pillow", "numpy", "opencv-python", "requests"])
                    .with_file("/app/exam.pdf", pdf_file)
                    .with_new_file("/app/pdf_extractor.py", contents=pdf_extractor_content)
                    .with_workdir("/app")
                    .with_exec(["python", "pdf_extractor.py", "exam.pdf"])
                )
            
            # Get the PDF text extraction result
            pdf_text_json = await pdf_text_container.stdout()
            print(f"DEBUG: Raw output from answer_pdf_extractor.py: {repr(pdf_text_json[:500])}...")

            # Then try to parse it:
            try:
                pdf_text_data = json.loads(pdf_text_json)
            except json.JSONDecodeError as e:
                print(f"DEBUG: JSON parsing error: {str(e)}")
                print(f"DEBUG: First 100 characters of raw output: {repr(pdf_text_json[:100])}")
                return json.dumps({
                    "success": False,
                    "error": f"Error during PDF extraction: {str(e)}",
                    "pdf_text": pdf_text_json[:1000] if len(pdf_text_json) > 0 else "Empty string"
                })
            
            if "error" in pdf_text_data:
                return json.dumps({
                    "success": False,
                    "error": f"Error extracting PDF content: {pdf_text_data['error']}"
                })
            
            # Add these lines before the LLM call
            print(f"DEBUG: PDF text data keys: {list(pdf_text_data.keys())}")
            print(f"DEBUG: Text length: {len(pdf_text_data.get('text', ''))}")
            print(f"DEBUG: Text first 100 chars: {pdf_text_data.get('text', '')[:100]}")

            # After PDF text extraction, switch based on document type
            if document_type.lower() == "answers":
                # Use the enhanced answer extraction prompt that captures all required information
                extractor = (
                    dag.llm()
                    .with_prompt(f"""
                    The following text is from an exam marking scheme/answer paper:
                    
                    {pdf_text_data['text']}
                    
                    Analyze this text and extract ALL answers in the marking scheme, maintaining the question numbering from the original exam paper. For each answer:
                    
                    1. Identify the question/sub-question number (must match the original exam paper)
                    2. Extract the complete answer text/marking criteria
                    3. Note the marks allocated for each part of the answer
                    4. Include any alternative acceptable answers
                    5. Note any specific instructions for markers
                    6. Include any additional contextual information that helps understand the answer
                    
                    IMPORTANT: Many marking schemes include explanatory notes, worked examples, or sample answers that should be preserved in full.
                    
                    Return ONLY a JSON object with this structure:
                    {{
                      "total_answers": 5,
                      "answers": [
                        {{
                          "question_number": 1,
                          "answer_text": "Full text of the model answer/marking criteria",
                          "marking_scheme": {{
                            "total_marks": 15,
                            "grade_boundaries": {{
                              "description": "Description of how marks correspond to grades if provided"
                            }}
                          }},
                          "sub_answers": [
                            {{
                              "sub_number": "a",
                              "text": "Text of answer to sub-question a",
                              "marks": 5,
                              "alternatives": ["Alternative acceptable answer 1", "Alternative acceptable answer 2"],
                              "marking_notes": "Any specific notes for markers about this question"
                            }}
                          ],
                          "additional_info": "Any extra context, guidelines, or information relevant to this answer"
                        }}
                      ]
                    }}
                    
                    No other text or formatting.
                    """)
                )
                
                # Use the answer-specific field names
                extraction_json = await extractor.last_reply()
                # Clean the response to ensure it's valid JSON
                cleaned_json = extraction_json.strip()

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
                extraction_data = json.loads(cleaned_json)
                
                # Extract path components from the file path
                file_path = download_result.get("file_path", "")
                path_components = file_path.split("/")
                
                # Extract level, subject, and year
                level = ""
                subject = ""
                year = ""
                
                # Load constants to get the correct level names
                constants_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "constants.py"
                constants_module = {}
                with open(constants_path, "r") as f:
                    exec(f.read(), constants_module)
                
                # Get education levels from constants
                education_levels = constants_module.get("EDUCATION_LEVELS", {})
                
                # Find level by checking if any component matches a key in education_levels
                for component in path_components:
                    if component in education_levels:
                        level = component
                        break
                    # Special case for "Primary School" which might appear as just "Primary" in the path
                    elif component == "Primary" and "Primary School" in education_levels:
                        level = "Primary School"
                        break
                
                # Subject is typically the component after the level
                if level and level in path_components:
                    level_index = path_components.index(level)
                    if len(path_components) > level_index + 1:
                        subject = path_components[level_index + 1]
                # Special case for "Primary School" which might appear as just "Primary" in the path
                elif "Primary" in path_components and level == "Primary School":
                    primary_index = path_components.index("Primary")
                    if len(path_components) > primary_index + 1:
                        subject = path_components[primary_index + 1]
                
                # Find year (component that matches 4-digit pattern)
                year_pattern = re.compile(r'\d{4}')
                for component in path_components:
                    if year_pattern.match(component):
                        year = component
                        break
                
                # Get file name
                file_name = download_result.get("file_name", "")
                
                # Create collection name by concatenating components
                # Only include components that were successfully extracted
                collection_name = ""
                if level:
                    collection_name += level
                if subject:
                    collection_name += subject
                if year:
                    collection_name += year
                if file_name:
                    collection_name += file_name
                
                # If we couldn't extract any components, use the file_name as a fallback
                if not collection_name and file_name:
                    collection_name = file_name
                
                # Return the result with collection_name added
                return json.dumps({
                    "success": True,
                    "file_id": file_id,
                    "file_name": file_name,
                    "collection_name": collection_name,
                    "total_answers": extraction_data.get("total_answers", 0),
                    "extracted_answers": extraction_data.get("answers", [])
                }, indent=2)
            else:
                # Use the existing question extraction code exactly as is
                question_extractor = (
                    dag.llm()
                    .with_prompt(f"""
                    The following text is from an exam paper:
                    
                    {pdf_text_data['text']}
                    
                    Analyze this text and extract ALL questions in the exam paper, including their full context. For each question:
                    
                    IMPORTANT: The text includes image and graphic markers in the following formats:
                    - [COVER IMAGE: name on page X, WxH] - Images on the cover page
                    - [IMAGE for Q5: name on page X, WxH] - Images for specific questions
                    - [GRAPHIC for Q3: name on page Y] - Graphics for specific questions
                    - [IMAGE: name on page Z, WxH] - General images
                    
                    These markers contain the image URL in the "url" field of the corresponding object in the PDF data. 
                    To find the URL for an image marker, look for the matching image object in this data:
                    {json.dumps([img for img in pdf_text_data['images'] if 'url' in img])}
                    
                    To find the URL for a graphic marker, look for the matching graphic object in this data:
                    {json.dumps([graphic for graphic in pdf_text_data['graphics'] if 'url' in graphic])}
                    
                    Match the image name and page number from the marker to find the correct URL.
                    
                    1. Identify the question number
                    2. Extract the complete question text
                    3. Extract any associated texts, passages, or materials that are part of the question (like Text A, B, C)
                    4. Note any sub-questions
                    5. Identify tables (describe their content)
                    6. Note any images or visual elements that are associated with the question
                    7. Determine how many marks the question is worth
                    8. Classify the question by topic and subtopic
                    9. Assess the difficulty level of the question based on the level (this is following the Cambridge curriculum).
                    
                    IMPORTANT: Many exam questions include associated texts, passages, or materials that students need to analyze. These are part of the question and should be included in your extraction.
                                    
                    IMPORTANT: When extracting context materials, be careful to distinguish between:
                    - Actual text passages that should be included in "content"
                    - Images, charts, or graphs that should be identified as images, not treated as text
                    
                    For example, if "Text C" is actually a graph or chart, it should be categorized as an image in the "images" array, not as text in "context_materials".
                    
                    TOPIC CLASSIFICATION: For each question, identify:
                    - The main topic (e.g., "Algebra", "Thermodynamics", "Shakespeare", "Cell Biology")
                    - Specific subtopics (e.g., "Quadratic Equations", "Heat Transfer", "Macbeth", "Mitosis")
                    
                    DIFFICULTY ASSESSMENT: Rate each question's difficulty on a scale:
                    - Easy: Straightforward application of basic concepts
                    - Medium: Requires some analysis and multiple steps
                    - Hard: Complex problem requiring deep understanding
                    - Very Hard: Challenging problem requiring synthesis of multiple concepts
                    
                    Base your difficulty assessment on:
                    - Complexity of the question
                    - Number of marks allocated
                    - Number of steps required to solve
                    - Presence of advanced concepts
                    
                    Return ONLY a JSON object with this structure:
                    {{
                      "cover_image": {{  // Include if a cover image
                        "url": "The actual URL from the matching image object in the data",
                        "description": "Brief description of the cover image"
                      }},
                      "total_questions": 5,
                      "questions": [
                        {{
                          "question_number": 1,
                          "question_text": "Full text of the question prompt",
                          "topic": "Main topic area",
                          "subtopic": "Specific subtopic",
                          "difficulty": {{
                            "level": "Medium",
                            "justification": "Requires multiple steps and application of X concept"
                          }},
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
                              "url": "The actual URL from the matching image or graphic object"
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
                
                # Extract path components from the file path
                file_path = download_result.get("file_path", "")
                path_components = file_path.split("/")
                
                # Extract level, subject, and year
                level = ""
                subject = ""
                year = ""
                
                # Load constants to get the correct level names
                constants_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "constants.py"
                constants_module = {}
                with open(constants_path, "r") as f:
                    exec(f.read(), constants_module)
                
                # Get education levels from constants
                education_levels = constants_module.get("EDUCATION_LEVELS", {})
                
                # Find level by checking if any component matches a key in education_levels
                for component in path_components:
                    if component in education_levels:
                        level = component
                        break
                    # Special case for "Primary School" which might appear as just "Primary" in the path
                    elif component == "Primary" and "Primary School" in education_levels:
                        level = "Primary School"
                        break
                
                # Subject is typically the component after the level
                if level and level in path_components:
                    level_index = path_components.index(level)
                    if len(path_components) > level_index + 1:
                        subject = path_components[level_index + 1]
                # Special case for "Primary School" which might appear as just "Primary" in the path
                elif "Primary" in path_components and level == "Primary School":
                    primary_index = path_components.index("Primary")
                    if len(path_components) > primary_index + 1:
                        subject = path_components[primary_index + 1]
                
                # Find year (component that matches 4-digit pattern)
                year_pattern = re.compile(r'\d{4}')
                for component in path_components:
                    if year_pattern.match(component):
                        year = component
                        break
                
                # Get file name
                file_name = download_result.get("file_name", "")
                
                # Create collection name by concatenating components
                # Only include components that were successfully extracted
                collection_name = ""
                if level:
                    collection_name += level
                if subject:
                    collection_name += subject
                if year:
                    collection_name += year
                if file_name:
                    collection_name += file_name
                
                # If we couldn't extract any components, use the file_name as a fallback
                if not collection_name and file_name:
                    collection_name = file_name
                
                # Return the result with collection_name added
                return json.dumps({
                    "success": True,
                    "file_id": file_id,
                    "file_name": file_name,
                    "collection_name": collection_name,
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

    @function
    async def run(self, mongodb_uri: Secret, credentials_json: Secret, source_dir: dagger.Directory, process_all: bool = False) -> str:
        """
        Runs the extraction pipeline to process unprocessed documents in MongoDB one by one
        """
        
        # Get plaintext values
        mongodb_uri_value = await mongodb_uri.plaintext()
        
        # First, find unprocessed documents
        find_unprocessed_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "find_unprocessed.py"
        with open(find_unprocessed_path, "r") as f:
            find_unprocessed_script = f.read()
        
        # Load the new split scripts
        insert_questions_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "insert_questions.py"
        mark_processed_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "mark_processed.py"
        
        with open(insert_questions_path, "r") as f:
            insert_questions_script = f.read()
        
        with open(mark_processed_path, "r") as f:
            mark_processed_script = f.read()
        
        # Track total processing statistics
        all_results = []
        total_processed = 0
        total_success = 0
        total_failures = 0
        total_retries = 0
        
        # Add a set to track processed document IDs in this run
        processed_doc_ids = set()

        try:
            # Debug the credentials to see if they're accessible
            credentials_value = await credentials_json.plaintext()
            print(f"DEBUG: Credentials available, length: {len(credentials_value)} chars")
        except Exception as e:
            print(f"ERROR: Could not access credentials: {str(e)}")
        
        # Process documents one by one until no more are found
        while True:
            print(f"Finding next unprocessed document (processed so far: {total_processed})...")
            
            # Create a container for finding documents using skip
            find_container = (
                dag.container()
                .from_("python:3.12-slim")
                .with_exec(["pip", "install", "pymongo"])
                .with_new_file("/app/find_unprocessed.py", contents=find_unprocessed_script)
                .with_workdir("/app")
                .with_env_variable("MONGODB_URI", mongodb_uri_value)
            )
            
            # Command to run the script with skip parameter
            find_command = ["python", "find_unprocessed.py"]
            
            # Add the all argument if process_all is True
            if process_all:
                find_command.append("all")
            
            # Add the skip parameter based on documents processed so far
            find_command.extend(["--skip", str(total_processed)])
            
            # Execute the find script
            find_result_json = await find_container.with_exec(find_command).stdout()
            
            # Debug output right before parsing
            print(f"RAW OUTPUT LENGTH: {len(find_result_json)}")
            print(f"RAW OUTPUT FIRST 100 CHARS: {repr(find_result_json[:100])}")
            print(f"COMMAND EXECUTED: {' '.join(find_command)}")

            # Try to get stderr if stdout is empty
            if not find_result_json.strip():
                stderr = await find_container.with_exec(find_command).stderr()
                print(f"STDERR OUTPUT: {stderr}")

            # Parse the JSON response
            try:
                find_result = json.loads(find_result_json)
            except json.JSONDecodeError as e:
                print(f"JSON PARSE ERROR: {e}")
                print(f"ERROR POSITION: {e.pos}")
                print(f"ERROR LINE: {e.lineno}, ERROR COLUMN: {e.colno}")
            
            if "error" in find_result:
                return json.dumps({
                    "success": False,
                    "error": find_result["error"]
                })
            
            # Check if we have documents to process
            if not find_result["documents"]:
                print("No more unprocessed documents found.")
                break
            
            # Process each document returned
            for document in find_result["documents"]:
                doc_id = document["_id"]
                
                # Skip documents we've already processed in this run
                if doc_id in processed_doc_ids:
                    print(f"Document {doc_id} was already processed in this run, skipping...")
                    continue
                
                print(f"Processing document {doc_id}, file ID: {document['FileID']}")
                
                # Process this document
                try:
                    # Extract data from the document
                    extraction_result = await self.single(
                        credentials_json, 
                        document["FileID"], 
                        document.get("FileName", f"document_{doc_id}")
                    )
                    print(f"DEBUG: Extraction result type: {type(extraction_result)}, length: {len(extraction_result) if isinstance(extraction_result, str) else 'not a string'}")
                    print(f"DEBUG: First 100 chars of extraction result: {extraction_result[:100]}")
                    print(f"DEBUG: Last 100 chars of extraction result: {extraction_result[-100:] if len(extraction_result) > 100 else extraction_result}")

                    # Validate JSON and show specific error info
                    try:
                        parsed = json.loads(extraction_result)
                        print(f"DEBUG: Successfully parsed extraction JSON with {len(parsed.get('extracted_questions', []))} questions")
                        print(f"DEBUG: JSON structure keys: {list(parsed.keys())}")
                    except json.JSONDecodeError as e:
                        print(f"DEBUG: CRITICAL JSON ERROR: {str(e)}")
                        error_position = e.pos
                        context_start = max(0, error_position - 50)
                        context_end = min(len(extraction_result), error_position + 50)
                        error_context = extraction_result[context_start:context_end]
                        print(f"DEBUG: Error context (position {error_position}): {repr(error_context)}")
                        print(f"DEBUG: Character at error position: {repr(extraction_result[error_position:error_position+1]) if error_position < len(extraction_result) else 'EOF'}")
                    
                    # Before insert container creation
                    print(f"DEBUG: Creating container with file of size {len(extraction_result)} bytes")
                    print(f"DEBUG: Writing extraction result to file in container...")

                    # Count JSON objects to verify integrity
                    try:
                        json_obj = json.loads(extraction_result)
                        num_questions = len(json_obj.get("extracted_questions", []))
                        print(f"DEBUG: JSON contains {num_questions} questions")
                    except Exception as e:
                        print(f"DEBUG: Failed to count JSON objects: {str(e)}")
                    
                    # FIRST: Insert the extracted questions into the database
                    insert_container = (
                        dag.container()
                        .from_("python:3.12-slim")
                        .with_exec(["pip", "install", "pymongo"])
                        .with_new_file("/app/insert_questions.py", contents=insert_questions_script)
                        .with_workdir("/app")
                        .with_env_variable("MONGODB_URI", mongodb_uri_value)
                        .with_new_file("/app/extraction_data.json", contents=extraction_result)
                        # Run verification as a SEPARATE command
                        .with_exec(["sh", "-c", "echo 'FILE CONTENTS:' && cat /app/extraction_data.json | head -10"])
                        # Then run the script in another command
                        .with_exec(["python", "insert_questions.py", doc_id, "/app/extraction_data.json", "--file"])
                    )
                    
                    # Get the insert result
                    insert_result_json = await insert_container.stdout()
                    print(f"DEBUG: Raw insert_result_json: {repr(insert_result_json)}")  # This will show the actual string including any whitespace or special characters
                    try:
                        insert_result = json.loads(insert_result_json)
                    except json.JSONDecodeError as e:
                        print(f"DEBUG: JSON decode error: {str(e)}")
                        print(f"DEBUG: First 100 chars of raw result: {repr(insert_result_json[:100])}")
                        # Continue with error handling
                    
                    if insert_result.get("success", False):
                        print(f"SUCCESS: Inserted {insert_result.get('total_questions', 0)} questions for document {doc_id}")
                        
                        # SECOND: Mark the document as processed
                        extraction_id = insert_result.get("extraction_id", "")
                        total_questions = insert_result.get("total_questions", 0)
                        
                        mark_container = (
                            dag.container()
                            .from_("python:3.12-slim")
                            .with_exec(["pip", "install", "pymongo"])
                            .with_new_file("/app/mark_processed.py", contents=mark_processed_script)
                            .with_workdir("/app")
                            .with_env_variable("MONGODB_URI", mongodb_uri_value)
                            .with_exec(["python", "mark_processed.py", doc_id, extraction_id, str(total_questions)])
                        )
                        
                        # Get the mark result
                        mark_result_json = await mark_container.stdout()
                        mark_result = json.loads(mark_result_json)
                        
                        if mark_result.get("success", False):
                            print(f"SUCCESS: Document {doc_id} marked as processed")
                            total_success += 1
                            
                            # Combine results for reporting
                            combined_result = {
                                "success": True,
                                "document_id": doc_id,
                                "total_questions": total_questions,
                                "extraction_id": extraction_id
                            }
                            all_results.append(combined_result)
                        else:
                            print(f"WARNING: Failed to mark document {doc_id} as processed: {mark_result.get('error', 'Unknown error')}")
                            total_failures += 1
                            all_results.append(mark_result)
                    else:
                        print(f"WARNING: Failed to insert questions for document {doc_id}: {insert_result.get('error', 'Unknown error')}")
                        total_failures += 1
                        
                    # After successfully processing a document, add its ID to our set
                    processed_doc_ids.add(doc_id)
                    total_processed += 1
                    time.sleep(2)  # Keep the delay for safety
                    
                except Exception as e:
                    error_message = f"Error processing document {doc_id}: {str(e)}"
                    print(f"ERROR: {error_message}")
                    all_results.append({
                        "success": False,
                        "document_id": doc_id,
                        "error": error_message
                    })
                    total_failures += 1
        
        # Return the overall results
        return json.dumps({
            "success": True,
            "processed_count": total_processed,
            "success_count": total_success,
            "failure_count": total_failures,
            "retry_count": total_retries,
            "results": all_results
        })
    
    @function
    async def answer(self, credentials_json: Secret, file_id: str) -> str:
        """Extract answers from a marking scheme PDF using LLM processing"""
        
        # Get plaintext value from the Secret
        credentials_json_value = await credentials_json.plaintext()
        
        # Load the llm_extraction.py script
        llm_extraction_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "llm_extraction.py"
        
        with open(llm_extraction_path, "r") as f:
            script_content = f.read()
        
        # Set a default filename based on the file_id
        file_name = f"document_{file_id[-8:]}"
        
        # Download the PDF
        download_container = (
            dag.container()
            .from_("python:3.12-slim")
            .with_exec(["pip", "install", "google-api-python-client", "google-auth"])
            .with_new_file("/app/credentials.json", contents=credentials_json_value)
            .with_new_file("/app/llm_extraction.py", contents=script_content)
            .with_workdir("/app")
            .with_exec(["python", "llm_extraction.py", file_id, "/app", file_name])
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
            pdf_path = download_result.get("pdf_path")
            pdf_file = await download_container.file(pdf_path)
            
            # Extract text from the PDF first to avoid passing raw PDF content
            # First, read the content of the pdf_extractor.py file
            pdf_extractor_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "pdf_extractor.py"
            with open(pdf_extractor_path, "r") as f:
                pdf_extractor_content = f.read()
            
            # Now use the content with with_new_file instead of with_file
            pdf_text_container = (
                dag.container()
                .from_("python:3.12-slim")
                .with_exec(["apt-get", "update"])
                .with_exec(["apt-get", "install", "-y", "libgl1-mesa-glx", "libglib2.0-0", "poppler-utils"])
                .with_exec(["pip", "install", "PyPDF2", "pdf2image", "pillow", "numpy", "opencv-python", "requests"])
                .with_file("/app/exam.pdf", pdf_file)
                .with_new_file("/app/pdf_extractor.py", contents=pdf_extractor_content)
                .with_workdir("/app")
                .with_exec(["python", "pdf_extractor.py", "exam.pdf"])
            )
            
            # Get the PDF text extraction result
            pdf_text_json = await pdf_text_container.stdout()
            print(f"DEBUG: Raw output from answer_pdf_extractor.py: {repr(pdf_text_json[:500])}...")

            # Then try to parse it:
            try:
                pdf_text_data = json.loads(pdf_text_json)
            except json.JSONDecodeError as e:
                print(f"DEBUG: JSON parsing error: {str(e)}")
                print(f"DEBUG: First 100 characters of raw output: {repr(pdf_text_json[:100])}")
                return json.dumps({
                    "success": False,
                    "error": f"Error during PDF extraction: {str(e)}",
                    "pdf_text": pdf_text_json[:1000] if len(pdf_text_json) > 0 else "Empty string"
                })
            
            if "error" in pdf_text_data:
                return json.dumps({
                    "success": False,
                    "error": f"Error extracting PDF content: {pdf_text_data['error']}"
                })
            
            # Add these lines before the LLM call
            print(f"DEBUG: PDF text data keys: {list(pdf_text_data.keys())}")
            print(f"DEBUG: Text length: {len(pdf_text_data.get('text', ''))}")
            print(f"DEBUG: Text first 100 chars: {pdf_text_data.get('text', '')[:100]}")

            # Now use the LLM directly without the pdfextractor tool
            answer_extractor = (
                dag.llm()
                .with_prompt(f"""
                The following text is from an exam marking scheme/answer paper:
                
                {pdf_text_data['text']}
                
                Analyze this text and extract ALL answers in the marking scheme, maintaining the question numbering from the original exam paper. For each answer:
                
                1. Identify the question/sub-question number (must match the original exam paper)
                2. Extract the complete answer text/marking criteria
                3. Note the marks allocated for each part of the answer
                4. Include any alternative acceptable answers
                5. Identify marking rubrics or grading schemes
                6. Note any specific instructions for markers
                
                IMPORTANT: Many marking schemes include explanatory notes, worked examples, or sample answers that should be preserved in full.
                
                Return ONLY a JSON object with this structure:
                {{
                  "total_answers": 5,
                  "answers": [
                    {{
                      "question_number": 1,
                      "answer_text": "Full text of the model answer/marking criteria",
                      "marking_scheme": {{
                        "total_marks": 15,
                        "grade_boundaries": {{
                          "description": "Description of how marks correspond to grades if provided"
                        }}
                      }},
                      "sub_answers": [
                        {{
                          "sub_number": "a",
                          "text": "Text of answer to sub-question a",
                          "marks": 5,
                          "alternatives": ["Alternative acceptable answer 1", "Alternative acceptable answer 2"],
                          "marking_notes": "Any specific notes for markers about this question"
                        }}
                      ]
                    }}
                  ]
                }}
                
                No other text or formatting.
                """)
            )
            
            # Get the extracted answers
            answers_json = await answer_extractor.last_reply()
            
            # Clean the response to ensure it's valid JSON
            cleaned_json = answers_json.strip()

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
            answers_data = json.loads(cleaned_json)
            
            # Extract path components from the file path
            file_path = download_result.get("file_path", "")
            path_components = file_path.split("/")
            
            # Extract level, subject, and year
            level = ""
            subject = ""
            year = ""
            
            # Load constants to get the correct level names
            constants_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "constants.py"
            constants_module = {}
            with open(constants_path, "r") as f:
                exec(f.read(), constants_module)
            
            # Get education levels from constants
            education_levels = constants_module.get("EDUCATION_LEVELS", {})
            
            # Find level by checking if any component matches a key in education_levels
            for component in path_components:
                if component in education_levels:
                    level = component
                    break
                # Special case for "Primary School" which might appear as just "Primary" in the path
                elif component == "Primary" and "Primary School" in education_levels:
                    level = "Primary School"
                    break
            
            # Subject is typically the component after the level
            if level and level in path_components:
                level_index = path_components.index(level)
                if len(path_components) > level_index + 1:
                    subject = path_components[level_index + 1]
            # Special case for "Primary School" which might appear as just "Primary" in the path
            elif "Primary" in path_components and level == "Primary School":
                primary_index = path_components.index("Primary")
                if len(path_components) > primary_index + 1:
                    subject = path_components[primary_index + 1]
            
            # Find year (component that matches 4-digit pattern)
            year_pattern = re.compile(r'\d{4}')
            for component in path_components:
                if year_pattern.match(component):
                    year = component
                    break
            
            # Get file name
            file_name = download_result.get("file_name", "")
            
            # Create collection name by concatenating components
            # Only include components that were successfully extracted
            collection_name = ""
            if level:
                collection_name += level
            if subject:
                collection_name += subject
            if year:
                collection_name += year
            if file_name:
                collection_name += file_name
            
            # If we couldn't extract any components, use the file_name as a fallback
            if not collection_name and file_name:
                collection_name = file_name
            
            # Return the result with collection_name added
            return json.dumps({
                "success": True,
                "file_id": file_id,
                "file_name": file_name,
                "collection_name": collection_name,
                "total_answers": answers_data.get("total_answers", 0),
                "extracted_answers": answers_data.get("answers", [])
            }, indent=2)
            
        except Exception as e:
            # Catch all exceptions for better debugging
            import traceback
            error_traceback = traceback.format_exc()
            
            return json.dumps({
                "success": False,
                "error": f"Error during LLM processing: {str(e)}",
                "traceback": error_traceback,
                "raw_response": answers_json if 'answers_json' in locals() else "No response"
            })

    @function
    async def answers(self, mongodb_uri: Secret, credentials_json: Secret, include_processed: bool = False) -> str:
        """
        Runs the answer extraction pipeline to process answer documents in MongoDB
        that have matching processed question documents
        
        Args:
            mongodb_uri: MongoDB connection string
            credentials_json: Google API credentials
            include_processed: Whether to include documents already marked as processed
        """
        
        # Get plaintext values
        mongodb_uri_value = await mongodb_uri.plaintext()
        
        # Load the scripts we need
        find_matching_answers_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "find_matching_answer.py"
        insert_answers_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "insert_answers.py"
        mark_processed_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "mark_processed.py"
        
        with open(find_matching_answers_path, "r") as f:
            find_matching_answers_script = f.read()
        
        with open(insert_answers_path, "r") as f:
            insert_answers_script = f.read()
        
        with open(mark_processed_path, "r") as f:
            mark_processed_script = f.read()
        
        # Track total processing statistics
        all_results = []
        total_processed = 0
        total_success = 0
        total_failures = 0
        total_retries = 0
        
        # Add a set to track processed document IDs in this run
        processed_doc_ids = set()

        try:
            # Debug the credentials to see if they're accessible
            credentials_value = await credentials_json.plaintext()
            print(f"DEBUG: Credentials available, length: {len(credentials_value)} chars")
        except Exception as e:
            print(f"ERROR: Could not access credentials: {str(e)}")
        
        # Process documents one by one until no more are found
        while True:
            print(f"Finding next unprocessed answer document with matching questions (processed so far: {total_processed})...")
            
            # Create a container for finding documents using skip
            find_container = (
                dag.container()
                .from_("python:3.12-slim")
                .with_exec(["pip", "install", "pymongo"])
                .with_new_file("/app/find_matching_answer.py", contents=find_matching_answers_script)
                .with_workdir("/app")
                .with_env_variable("MONGODB_URI", mongodb_uri_value)
            )
            
            # Command to run the script with skip parameter
            find_command = ["python", "find_matching_answer.py", "--skip", str(total_processed)]
            
            # Add include_processed flag if specified
            if include_processed:
                find_command.append("--include-processed")
            
            # Execute the find script
            find_result_json = await find_container.with_exec(find_command).stdout()
            
            # Debug output right before parsing
            print(f"RAW OUTPUT LENGTH: {len(find_result_json)}")
            print(f"RAW OUTPUT FIRST 100 CHARS: {repr(find_result_json[:100])}")
            print(f"COMMAND EXECUTED: {' '.join(find_command)}")

            # Try to get stderr if stdout is empty
            if not find_result_json.strip():
                stderr = await find_container.with_exec(find_command).stderr()
                print(f"STDERR OUTPUT: {stderr}")

            # Parse the JSON response
            try:
                find_result = json.loads(find_result_json)
            except json.JSONDecodeError as e:
                print(f"JSON PARSE ERROR: {e}")
                print(f"ERROR POSITION: {e.pos}")
                print(f"ERROR LINE: {e.lineno}, ERROR COLUMN: {e.colno}")

            # Check if we have documents to process
            if not find_result.get("documents", []):
                print("No more unprocessed answer documents with matching questions found.")
                break
            
            # Process each document returned
            for document in find_result.get("documents", []):
                doc_id = document["_id"]
                file_id = document["FileID"]  # Use the correct FileID from the document
                
                # Skip documents we've already processed in this run
                if doc_id in processed_doc_ids:
                    print(f"Document {doc_id} was already processed in this run, skipping...")
                    continue
                
                print(f"Processing answer document {doc_id}, file ID: {file_id}, matching question ID: {document['matching_question_id']}")
                
                # Process this document
                try:
                    # Extract data from the document using single with document_type="answers"
                    extraction_result = await self.single(
                        credentials_json, 
                        file_id,  # Use the correct file_id
                        document.get("FileName", f"document_{doc_id}"),
                        "answers"
                    )
                    
                    # Validate JSON and show specific error info
                    try:
                        parsed = json.loads(extraction_result)
                        print(f"DEBUG: Successfully parsed extraction JSON with {len(parsed.get('extracted_answers', []))} answers")
                        print(f"DEBUG: JSON structure keys: {list(parsed.keys())}")
                    except json.JSONDecodeError as e:
                        print(f"DEBUG: CRITICAL JSON ERROR: {str(e)}")
                        error_position = e.pos
                        context_start = max(0, error_position - 50)
                        context_end = min(len(extraction_result), error_position + 50)
                        error_context = extraction_result[context_start:context_end]
                        print(f"DEBUG: Error context (position {error_position}): {repr(error_context)}")
                        
                    # FIRST: Insert the extracted answers into the database
                    insert_container = (
                        dag.container()
                        .from_("python:3.12-slim")
                        .with_exec(["pip", "install", "pymongo"])
                        .with_new_file("/app/insert_answers.py", contents=insert_answers_script)
                        .with_workdir("/app")
                        .with_env_variable("MONGODB_URI", mongodb_uri_value)
                        .with_new_file("/app/extraction_data.json", contents=extraction_result)
                        # Verify file contents
                        .with_exec(["sh", "-c", "echo 'FILE CONTENTS:' && cat /app/extraction_data.json | head -10"])
                        # Run the script with matching question ID
                        .with_exec(["python", "insert_answers.py", doc_id, "/app/extraction_data.json", "--file"])
                    )
                    
                    # Get the insert result
                    insert_result_json = await insert_container.stdout()
                    print(f"DEBUG: Raw insert_result_json: {repr(insert_result_json)}")
                    
                    try:
                        insert_result = json.loads(insert_result_json)
                    except json.JSONDecodeError as e:
                        print(f"DEBUG: JSON decode error: {str(e)}")
                        print(f"DEBUG: First 100 chars of raw result: {repr(insert_result_json[:100])}")
                        # Continue with error handling
                    
                    if insert_result.get("success", False):
                        print(f"SUCCESS: Inserted {insert_result.get('total_answers', 0)} answers for document {doc_id}")
                        
                        # SECOND: Mark the document as processed in pp-answers collection
                        extraction_id = insert_result.get("extraction_id", "")
                        total_answers = insert_result.get("total_answers", 0)
                        
                        mark_container = (
                            dag.container()
                            .from_("python:3.12-slim")
                            .with_exec(["pip", "install", "pymongo"])
                            .with_new_file("/app/mark_processed.py", contents=mark_processed_script)
                            .with_workdir("/app")
                            .with_env_variable("MONGODB_URI", mongodb_uri_value)
                            # Use the generalized mark_processed with pp-answers collection
                            .with_exec(["python", "mark_processed.py", doc_id, 
                                    "--extraction-id", extraction_id, 
                                    "--total-items", str(total_answers),
                                    "--collection", "pp-answers"])
                        )
                        
                        # Get the mark result
                        mark_result_json = await mark_container.stdout()
                        mark_result = json.loads(mark_result_json)
                        
                        if mark_result.get("success", False):
                            print(f"SUCCESS: Answer document {doc_id} marked as processed")
                            total_success += 1
                            
                            # Combine results for reporting
                            combined_result = {
                                "success": True,
                                "document_id": doc_id,
                                "total_answers": total_answers,
                                "extraction_id": extraction_id
                            }
                            all_results.append(combined_result)
                        else:
                            print(f"WARNING: Failed to mark answer document {doc_id} as processed: {mark_result.get('error', 'Unknown error')}")
                            total_failures += 1
                            all_results.append(mark_result)
                    else:
                        print(f"WARNING: Failed to insert answers for document {doc_id}: {insert_result.get('error', 'Unknown error')}")
                        total_failures += 1
                        
                    # After processing document, add its ID to our set
                    processed_doc_ids.add(doc_id)
                    total_processed += 1
                    time.sleep(2)  # Keep the delay for safety
                    
                except Exception as e:
                    error_message = f"Error processing answer document {doc_id}: {str(e)}"
                    print(f"ERROR: {error_message}")
                    all_results.append({
                        "success": False,
                        "document_id": doc_id,
                        "error": error_message
                    })
                    total_failures += 1
        
        # Return the overall results
        return json.dumps({
            "success": True,
            "processed_count": total_processed,
            "success_count": total_success,
            "failure_count": total_failures,
            "retry_count": total_retries,
            "results": all_results
        })

    @function
    async def update(self, 
                     mongodb_uri: Secret, 
                     credentials_json: Secret, 
                     collection_name: str, 
                     batch_size: int = 50, 
                     skip: int = 0, 
                     clean_database: bool = True) -> str:
        """
        Update paper metadata for extracted documents missing metadata.
        Also cleans database by removing duplicates and empty entries.
        
        Args:
            mongodb_uri: MongoDB connection string
            credentials_json: Google Drive API credentials
            collection_name: Name of the collection to update ('extracted-questions' or 'extracted-answers')
            batch_size: Maximum number of documents to process in each batch
            skip: Number of documents to skip initially
            clean_database: Whether to clean the database by removing duplicates and empty entries
        """
        # Get plaintext values
        mongodb_uri_value = await mongodb_uri.plaintext()
        credentials_json_value = await credentials_json.plaintext()
        
        # Load the scripts we need
        update_path = pathlib.Path(__file__).parent.parent / "meta" / "update.py"
        extract_cover_path = pathlib.Path(__file__).parent.parent / "meta" / "extract_cover.py"
        update_mongo_path = pathlib.Path(__file__).parent.parent / "meta" / "update_mongo.py"
        cleanup_path = pathlib.Path(__file__).parent.parent / "meta" / "cleanup.py"
        llm_extraction_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "llm_extraction.py"
        
        with open(update_path, "r") as f:
            update_script = f.read()
        
        with open(extract_cover_path, "r") as f:
            extract_cover_script = f.read()
        
        with open(update_mongo_path, "r") as f:
            update_mongo_script = f.read()
        
        with open(cleanup_path, "r") as f:
            cleanup_script = f.read()
        
        with open(llm_extraction_path, "r") as f:
            llm_extraction_script = f.read()
        
        # Track statistics
        total_documents = 0
        successful_updates = 0
        deleted_duplicates = 0
        deleted_empty_entries = 0
        all_results = []
        current_skip = skip
        
        # First, if clean_database is enabled, run the cleanup operation
        if clean_database:
            cleanup_container = (
                dag.container()
                .from_("python:3.12-slim")
                .with_exec(["pip", "install", "pymongo"])
                .with_new_file("/app/cleanup.py", contents=cleanup_script)
                .with_env_variable("MONGODB_URI", mongodb_uri_value)
                .with_workdir("/app")
                .with_exec(["python", "cleanup.py"])
            )
            
            cleanup_result_json = await cleanup_container.stdout()
            cleanup_result = json.loads(cleanup_result_json)
            
            if not cleanup_result.get("success", False):
                return json.dumps({
                    "success": False,
                    "error": cleanup_result.get("error", "Unknown error during database cleanup")
                })
            
            deleted_duplicates = cleanup_result.get("duplicates_removed", 0)
            deleted_empty_entries = cleanup_result.get("empty_entries_removed", 0)
        
        # Process documents in batches until none are left
        while True:
            # Find documents missing metadata
            find_container = (
                dag.container()
                .from_("python:3.12-slim")
                .with_exec(["pip", "install", "pymongo"])
                .with_new_file("/app/update.py", contents=update_script)
                .with_env_variable("MONGODB_URI", mongodb_uri_value)
                .with_env_variable("BATCH_SIZE", str(batch_size))
                .with_env_variable("SKIP", str(current_skip))
                .with_env_variable("COLLECTION_NAME", collection_name)  # Pass collection name
                .with_workdir("/app")
                .with_exec(["python", "update.py"])
            )
            
            # Get the list of documents needing updates
            find_result_json = await find_container.stdout()
            
            try:
                find_result = json.loads(find_result_json)
                if not find_result.get("success", False):
                    return json.dumps({
                        "success": False,
                        "error": find_result.get("error", "Unknown error during document search")
                    })
                
                documents = find_result.get("documents", [])
                if not documents:
                    # No more documents to process
                    break
                
                print(f"Found {len(documents)} documents missing metadata (batch starting at {current_skip})")
                
                # Process each document in this batch
                batch_processed = 0
                batch_successful = 0
                
                for doc in documents:
                    doc_id = doc["_id"]
                    file_id = doc.get("file_id", "")
                    file_name = doc.get("file_name", "")
                    
                    print(f"Processing document {doc_id}, file ID: {file_id}")
                    
                    if not file_id:
                        all_results.append({
                            "success": False,
                            "document_id": doc_id,
                            "error": "Missing file_id in document"
                        })
                        continue
                    
                    try:
                        # Download the PDF
                        download_container = (
                            dag.container()
                            .from_("python:3.12-slim")
                            .with_exec(["pip", "install", "google-api-python-client", "google-auth"])
                            .with_new_file("/app/credentials.json", contents=credentials_json_value)
                            .with_new_file("/app/llm_extraction.py", contents=llm_extraction_script)
                            .with_workdir("/app")
                            .with_exec(["python", "llm_extraction.py", file_id, "/app", file_name or f"document_{file_id[-8:]}"])
                        )
                        
                        # Get the download result
                        download_result_json = await download_container.stdout()
                        download_result = json.loads(download_result_json)
                        
                        if not download_result.get("success", False):
                            all_results.append({
                                "success": False,
                                "document_id": doc_id,
                                "error": download_result.get("error", "Unknown error during PDF download")
                            })
                            continue
                        
                        # Export the PDF file from the container
                        pdf_path = download_result.get("pdf_path")
                        pdf_file = await download_container.file(pdf_path)
                        
                        # Extract cover page text
                        extract_container = (
                            dag.container()
                            .from_("python:3.12-slim")
                            .with_exec(["pip", "install", "PyPDF2"])
                            .with_file("/app/exam.pdf", pdf_file)
                            .with_new_file("/app/extract_cover.py", contents=extract_cover_script)
                            .with_workdir("/app")
                            .with_exec(["python", "extract_cover.py", "/app/exam.pdf"])
                        )
                        
                        # Get the extraction result
                        extract_result_json = await extract_container.stdout()
                        extract_result = json.loads(extract_result_json)
                        
                        if not extract_result.get("success", False):
                            all_results.append({
                                "success": False,
                                "document_id": doc_id,
                                "error": extract_result.get("error", "Unknown error during cover page extraction")
                            })
                            continue
                        
                        cover_text = extract_result.get("cover_text", "")
                        if not cover_text:
                            all_results.append({
                                "success": False,
                                "document_id": doc_id,
                                "error": "No text extracted from cover page"
                            })
                            continue
                        
                        # Use LLM to extract metadata with improved prompt
                        extractor = (
                            dag.llm()
                            .with_prompt(f"""
The following text is from the cover page of an exam paper.

COVER PAGE TEXT:
{cover_text}

Analyze this text and extract the following metadata about the exam paper:

1. Level - Use EXACTLY one of these formats: "ASLevel", "OLevel", or "Primary School". 
   If you see "AS & A Level" or "AS and A Level" or similar variations, use "ASLevel".

2. Subject (e.g., "Mathematics", "Physics", "English")

3. Year (the year of the exam, e.g., "2022")

4. Paper (the paper number, e.g., "1", "2", "3")

5. Term (e.g., "Summer", "Winter", "Spring", "May/June", "Oct/Nov")

6. Version (if available, e.g., "21", "31", "42")

Return ONLY a JSON object with this structure:
{{
  "Level": "ASLevel",
  "Subject": "Mathematics",
  "Year": "2022",
  "Paper": "1",
  "Term": "Summer",
  "Version": "21"
}}

Provide the most accurate values based on the cover page text. If a field cannot be determined, leave it as an empty string.
No other text or formatting.
                            """)
                        )
                        
                        metadata_json = await extractor.last_reply()
                        
                        # Clean the response to ensure it's valid JSON
                        cleaned_json = metadata_json.strip()
                        
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
                        try:
                            metadata = json.loads(cleaned_json)
                        except json.JSONDecodeError:
                            all_results.append({
                                "success": False,
                                "document_id": doc_id,
                                "error": f"Failed to parse LLM output as JSON: {metadata_json[:200]}..."
                            })
                            continue
                        
                        # Ensure Level is standardized format
                        if "Level" in metadata:
                            # Normalize to ASLevel regardless of format variations
                            if "AS" in metadata["Level"] and ("&" in metadata["Level"] or "and" in metadata["Level"]):
                                metadata["Level"] = "ASLevel"
                        
                        # Extract metadata from filename if available
                        filename_metadata = {}
                        if file_name:
                            # Check for Paper-{number}:{version}.pdf pattern
                            paper_pattern = r'Paper-(\d+)(?::(\d+))?\.pdf'
                            match = re.search(paper_pattern, file_name)
                            if match:
                                filename_metadata["Paper"] = match.group(1)
                                if match.group(2):
                                    filename_metadata["Version"] = match.group(2)
                        
                        # Merge metadata - prioritize LLM extraction over filename extraction
                        paper_meta = {
                            "Level": metadata.get("Level", ""),
                            "Subject": metadata.get("Subject", ""),
                            "Year": metadata.get("Year", ""),
                            "Paper": metadata.get("Paper", filename_metadata.get("Paper", "")),
                            "Term": metadata.get("Term", "")
                        }
                        
                        # Add Version if available from either source
                        if "Version" in metadata or "Version" in filename_metadata:
                            paper_meta["Version"] = metadata.get("Version", filename_metadata.get("Version", ""))
                        
                        # Update MongoDB using the dedicated script
                        update_container = (
                            dag.container()
                            .from_("python:3.12-slim")
                            .with_exec(["pip", "install", "pymongo"])
                            .with_new_file("/app/update.py", contents=update_script)
                            .with_new_file("/app/update_mongo.py", contents=update_mongo_script)
                            .with_new_file("/app/metadata.json", contents=json.dumps(paper_meta))
                            .with_env_variable("MONGODB_URI", mongodb_uri_value)
                            .with_env_variable("COLLECTION_NAME", collection_name)
                            .with_workdir("/app")
                            .with_exec(["python", "update_mongo.py", doc_id, "/app/metadata.json"])
                        )
                        
                        update_result_json = await update_container.stdout()
                        update_result = json.loads(update_result_json)
                        
                        if update_result.get("success", False):
                            batch_successful += 1
                            print(f"Updated metadata for document {doc_id}")
                        else:
                            print(f"Failed to update metadata for document {doc_id}: {update_result.get('error', 'Unknown error')}")
                        
                        # Add metadata to result for statistics
                        update_result["metadata"] = paper_meta
                        all_results.append(update_result)
                        batch_processed += 1
                        
                    except Exception as e:
                        import traceback
                        error_traceback = traceback.format_exc()
                        all_results.append({
                            "success": False,
                            "document_id": doc_id,
                            "error": f"Error processing document: {str(e)}",
                            "traceback": error_traceback
                        })
                
                # Update counters for this batch
                total_documents += batch_processed
                successful_updates += batch_successful
                
                # Move to the next batch
                current_skip += len(documents)
                
            except json.JSONDecodeError as e:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to parse find result: {str(e)}",
                    "raw_output": find_result_json[:500]
                })
        
        # Return the overall results with statistics
        return json.dumps({
            "success": True,
            "total_documents_processed": total_documents,
            "successful_updates": successful_updates,
            "deleted_duplicates": deleted_duplicates,
            "deleted_empty_entries": deleted_empty_entries,
            "results": all_results[:50]  # Limit to first 50 results to avoid excessive response size
        })

    @function
    async def cleanup(self, mongodb_uri: Secret, update_metadata: bool = True, remove_duplicates: bool = True, dry_run: bool = True) -> str:
        """
        Cleanup the database by standardizing metadata and removing duplicates
        
        Args:
            mongodb_uri: MongoDB connection string
            update_metadata: Whether to standardize metadata fields
            remove_duplicates: Whether to remove duplicate documents
            dry_run: If True, only report changes but don't apply them
        """
        
        # Get plaintext values
        mongodb_uri_value = await mongodb_uri.plaintext()
        
        # Load the script
        remove_duplicates_path = pathlib.Path(__file__).parent / "scripts" / "orchestration" / "remove_duplicates.py"
        
        with open(remove_duplicates_path, "r") as f:
            remove_duplicates_script = f.read()
        
        # Build command based on parameters
        command = ["python", "remove_duplicates.py"]
        
        if update_metadata:
            command.append("--update-metadata")
        
        if remove_duplicates:
            command.append("--remove-duplicates")
        
        if dry_run:
            command.append("--dry-run")
        
        # Create container to run cleanup
        cleanup_container = (
            dag.container()
            .from_("python:3.12-slim")
            .with_exec(["pip", "install", "pymongo"])
            .with_new_file("/app/remove_duplicates.py", contents=remove_duplicates_script)
            .with_workdir("/app")
            .with_env_variable("MONGODB_URI", mongodb_uri_value)
            .with_exec(command)
        )
        
        # Get the result
        cleanup_result = await cleanup_container.stdout()
        
        return cleanup_result
            