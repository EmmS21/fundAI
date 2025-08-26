"""
Project Generator Service for The Engineer AI Tutor
Uses existing AI infrastructure to generate contextual programming projects
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from .project_prompts import create_project_generation_prompt, create_task_headers_prompt, create_task_detail_prompt

# Try to import local AI first, then cloud AI
try:
    from .marker import LocalAIMarker
    LOCAL_AI_AVAILABLE = True
except ImportError:
    LOCAL_AI_AVAILABLE = False

try:
    from .groq_client import GroqProgrammingClient
    CLOUD_AI_AVAILABLE = True
    print(f"[DEBUG IMPORT] ✅ Successfully imported GroqProgrammingClient")
except ImportError as e:
    CLOUD_AI_AVAILABLE = False
    print(f"[DEBUG IMPORT] ❌ Failed to import GroqProgrammingClient: {e}")
except Exception as e:
    CLOUD_AI_AVAILABLE = False
    print(f"[DEBUG IMPORT] ❌ Other exception importing GroqProgrammingClient: {e}")

logger = logging.getLogger(__name__)

class ProjectGenerator:
    """Generates programming projects using AI based on user context and scores"""
    
    def __init__(self):
        self.local_ai = None
        self.cloud_ai = None
        
        # Initialize available AI services
        if LOCAL_AI_AVAILABLE:
            try:
                self.local_ai = LocalAIMarker()
                logger.info("Local AI initialized for project generation")
            except Exception as e:
                logger.warning(f"Failed to initialize local AI: {e}")
        
        if CLOUD_AI_AVAILABLE:
            print(f"[DEBUG GROQ] CLOUD_AI_AVAILABLE is True, attempting to initialize GroqProgrammingClient")
            try:
                self.cloud_ai = GroqProgrammingClient()
                print(f"[DEBUG GROQ] GroqProgrammingClient created, checking if available...")
                if self.cloud_ai and self.cloud_ai.is_available():
                    print(f"[DEBUG GROQ] ✅ Cloud AI initialized and available")
                    logger.info("Cloud AI initialized for project generation")
                else:
                    print(f"[DEBUG GROQ] ❌ Cloud AI created but not available")
                    print(f"[DEBUG GROQ] self.cloud_ai: {self.cloud_ai}")
                    if self.cloud_ai:
                        print(f"[DEBUG GROQ] self.cloud_ai.client: {self.cloud_ai.client}")
                        print(f"[DEBUG GROQ] self.cloud_ai.api_key set: {bool(self.cloud_ai.api_key)}")
            except Exception as e:
                print(f"[DEBUG GROQ] ❌ Exception during GroqProgrammingClient init: {e}")
                logger.warning(f"Failed to initialize cloud AI: {e}")
        else:
            print(f"[DEBUG GROQ] CLOUD_AI_AVAILABLE is False")
    
    def generate_project(self, user_scores: Dict[str, Any], selected_language: str, 
                        user_data: Dict[str, Any], use_local_only: bool = False, project_theme: str = None) -> Optional[str]:
        """
        Generate a contextual programming project for the user
        
        Args:
            user_scores: Dictionary containing assessment and project scores
            selected_language: Programming language chosen by user
            user_data: User profile information
            use_local_only: Force local AI usage (overrides cloud preference)
            
        Returns:
            Generated project description or None if generation failed
        """
        
        # Create the prompt with theme for variety
        prompt = create_project_generation_prompt(user_scores, selected_language, user_data, project_theme)
        
        if use_local_only:
            project_description = self._try_local_generation(prompt, getattr(self, '_streaming_callback', None))
            if project_description:
                logger.info("Project generated successfully using local AI (forced)")
                return project_description
            logger.error("Failed to generate project using local AI")
            return None
        
        # Smart routing: Cloud first when online, local fallback
        if self._should_use_cloud_first():
            project_description = self._try_cloud_generation(prompt)
            if project_description:
                logger.info("Project generated successfully using cloud AI (preferred when online)")
                return project_description
            logger.info("Cloud AI failed, falling back to local AI")
        
        # Fallback to local AI with streaming callback
        project_description = self._try_local_generation(prompt, getattr(self, '_streaming_callback', None))
        if project_description:
            logger.info("Project generated successfully using local AI")
            return project_description
        
        logger.error("Failed to generate project using both cloud and local AI")
        return None
    
    def _try_cloud_generation(self, prompt: str) -> Optional[str]:
        """Try to generate project using cloud AI"""
        if not self.cloud_ai:
            return None
        
        try:
            response = self.cloud_ai.generate_response(prompt)
            if response and len(response.strip()) > 100:  # Basic validation
                return response
        except Exception as e:
            logger.warning(f"Cloud AI project generation failed: {e}")
        
        return None
    
    def _should_use_cloud_first(self) -> bool:
        """
        Determine if we should try cloud AI first based on connectivity
        
        Returns:
            True if cloud AI should be preferred, False otherwise
        """
        # Default to cloud AI (Groq) when available and online
        if not self.cloud_ai or not self.cloud_ai.is_available():
            return False
        
        # Import here to avoid circular imports
        from src.utils.network_utils import is_online, can_reach_groq
        
        try:
            return is_online() and can_reach_groq()
        except Exception as e:
            logger.warning(f"Network check failed: {e}")
            return False
    
    def _try_local_generation(self, prompt: str, streaming_callback=None) -> Optional[str]:
        """Try to generate project using local AI"""
        logger.info(f"🏠 _try_local_generation() CALLED")
        logger.info(f"📏 Prompt length: {len(prompt)} characters")
        print(f"[DEBUG] _try_local_generation called with streaming_callback: {streaming_callback}")
        print(f"[DEBUG] streaming_callback type: {type(streaming_callback)}")
        
        if not self.local_ai:
            logger.error(f"❌ No local AI instance available")
            return None
        
        logger.info(f"✅ Local AI instance available")
        
        try:
            max_tokens = 16384  # Use a much higher limit for detailed task generation
            temperature = 0.3  
            
            logger.info(f"⚙️ Generation parameters: max_tokens={max_tokens}, temp={temperature}")
            logger.info(f"📤 Calling local_ai.generate_response()")
            
            # Use the local AI marker's generation capability
            response = self.local_ai.generate_response(
                prompt, 
                max_tokens=max_tokens, 
                temperature=temperature,
                streaming_callback=streaming_callback
            )
            
            logger.info(f"📥 local_ai.generate_response() RETURNED")
            logger.info(f"📏 Response length: {len(response) if response else 0} characters")
            logger.info(f"📄 Response content: {response[:300] if response else 'None'}...")
            
            if response and len(response.strip()) > 50:  
                logger.info(f"✅ Local AI generated response: {len(response)} characters")
                
                # Save the full AI response to a file for debugging
                with open("ai_output_debug.md", "w") as f:
                    f.write("# Full AI Response Debug Output\n\n")
                    f.write(f"**Timestamp:** {datetime.now()}\n")
                    f.write(f"**Response Length:** {len(response)} characters\n\n")
                    f.write("## Full Response:\n")
                    f.write("```\n")
                    f.write(response)
                    f.write("\n```\n")
                
                # Extract only the JSON part for the UI
                from .project_prompts import extract_json_from_reasoning_response
                json_only = extract_json_from_reasoning_response(response)
                logger.info(f"📄 Extracted JSON: {len(json_only)} characters")
                
                # Also save the extracted JSON
                with open("ai_output_debug.md", "a") as f:
                    f.write("\n## Extracted JSON:\n")
                    f.write("```json\n")
                    f.write(json_only)
                    f.write("\n```\n")
                
                return json_only
            else:
                logger.warning(f"⚠️ Local AI response too short or empty: {len(response) if response else 0} characters")
        except Exception as e:
            logger.error(f"💥 EXCEPTION in _try_local_generation: {str(e)}")
            logger.error(f"🔍 Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"📜 Full traceback: {traceback.format_exc()}")
        
        logger.info(f"❌ _try_local_generation() returning None")
        return None
    

    def set_streaming_callback(self, callback):
        """Set callback for streaming updates"""
        print(f"[DEBUG] ProjectGenerator.set_streaming_callback called with: {callback}")
        print(f"[DEBUG] Callback type: {type(callback)}")
        self._streaming_callback = callback
        print(f"[DEBUG] self._streaming_callback set to: {self._streaming_callback}")
    
    def is_available(self) -> bool:
        """Check if any AI service is available for project generation"""
        return self.local_ai is not None or self.cloud_ai is not None
    
    def get_available_services(self) -> list:
        """Get list of available AI services"""
        services = []
        if self.local_ai:
            services.append("Local AI")
        if self.cloud_ai:
            services.append("Cloud AI")
        return services
    
    def generate_task_headers(self, project_description: str, selected_language: str, 
                             use_local_only: bool = False) -> Optional[str]:
        """
        Generate just the task headers/titles for the given project
        
        Args:
            project_description: The full project description to break down
            selected_language: Programming language for the project
            use_local_only: Whether to use only local AI
            
        Returns:
            Generated task headers or None if generation failed
        """
        logger.info(f"🚀 ProjectGenerator.generate_task_headers() CALLED")
        logger.info(f"📝 Project description length: {len(project_description)} chars")
        logger.info(f"🔧 Language: {selected_language}")
        logger.info(f"🏠 Use local only: {use_local_only}")
        
        # Create the simple task headers prompt
        logger.info(f"📝 Creating task headers prompt")
        prompt = create_task_headers_prompt(project_description, selected_language)
        logger.info(f"Task headers prompt length: {len(prompt)} characters")
        logger.info(f"📄 Prompt content: {prompt[:300]}...")
        
        if use_local_only:
            logger.info(f"🏠 Using LOCAL AI ONLY for task headers")
            # Use only local AI with streaming callback
            task_headers = self._try_local_generation(prompt, getattr(self, '_streaming_callback', None))
            if task_headers:
                logger.info("✅ Task headers generated successfully using local AI")
                return task_headers
            logger.error("❌ Failed to generate task headers using local AI")
            return None
        
        # Smart routing: Cloud first when online, local fallback
        if self._should_use_cloud_first():
            logger.info(f"☁️ Using CLOUD AI first for task headers (preferred when online)")
            task_headers = self._try_cloud_generation(prompt)
            if task_headers:
                logger.info("✅ Task headers generated successfully using cloud AI")
                return task_headers
            logger.info(f"🔄 Cloud AI failed, falling back to LOCAL AI")
        
        task_headers = self._try_local_generation(prompt, getattr(self, '_streaming_callback', None))
        if task_headers:
            logger.info("Task headers generated successfully using local AI")
            return task_headers
        
        logger.error("Failed to generate task headers using both cloud and local AI")
        return None
    
    def generate_task_detail(self, task_name: str, task_number: int, project_description: str, 
                            selected_language: str, use_local_only: bool = False, completed_tasks_summary: str = "") -> Optional[str]:
        """
        Generate detailed content for a specific task
        
        Args:
            task_name: Name of the task to generate details for
            task_number: Number of the task (1-4)
            project_description: The full project description
            selected_language: Programming language for the project
            use_local_only: Whether to use only local AI
            
        Returns:
            Generated task details or None if generation failed
        """
        from .project_prompts import extract_json_from_reasoning_response
        prompt = create_task_detail_prompt(task_name, task_number, project_description, selected_language, completed_tasks_summary)
        logger.info(f"Task detail prompt length: {len(prompt)} characters")
        
        if use_local_only:
            task_detail = self._try_local_generation(prompt, getattr(self, '_streaming_callback', None))
            if task_detail:
                logger.info(f"Task {task_number} details generated successfully using local AI")
                return task_detail
            logger.error(f"Failed to generate task {task_number} details using local AI")
            return None
        
        # Smart routing: Cloud first when online, local fallback
        if self._should_use_cloud_first():
            task_detail = self._try_cloud_generation(prompt)
            if task_detail:
                logger.info(f"Task {task_number} details generated successfully using cloud AI")
                return task_detail
            logger.info(f"Task {task_number} cloud AI failed, falling back to local AI")
        
        # Fallback to local AI
        task_detail = self._try_local_generation(prompt, getattr(self, '_streaming_callback', None))
        if task_detail:
            logger.info(f"Task {task_number} details generated successfully using local AI")
            return task_detail
        
        logger.error(f"Failed to generate task {task_number} details using both cloud and local AI")
        return None 