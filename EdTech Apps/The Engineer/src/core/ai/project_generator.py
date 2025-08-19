"""
Project Generator Service for The Engineer AI Tutor
Uses existing AI infrastructure to generate contextual programming projects
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

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
except ImportError:
    CLOUD_AI_AVAILABLE = False

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
            try:
                self.cloud_ai = GroqProgrammingClient()
                logger.info("Cloud AI initialized for project generation")
            except Exception as e:
                logger.warning(f"Failed to initialize cloud AI: {e}")
    
    def generate_project(self, user_scores: Dict[str, Any], selected_language: str, 
                        user_data: Dict[str, Any], use_local_only: bool = False) -> Optional[str]:
        """
        Generate a contextual programming project for the user
        
        Args:
            user_scores: Dictionary containing assessment and project scores
            selected_language: Programming language chosen by user
            user_data: User profile information
            
        Returns:
            Generated project description or None if generation failed
        """
        
        # Create the prompt
        prompt = create_project_generation_prompt(user_scores, selected_language, user_data)
        
        if use_local_only:
            # Use only local AI
            project_description = self._try_local_generation(prompt)
            if project_description:
                logger.info("Project generated successfully using local AI")
                return project_description
            logger.error("Failed to generate project using local AI")
            return None
        else:
            # Try cloud AI first for better quality, then fallback to local
            project_description = self._try_cloud_generation(prompt)
            if project_description:
                logger.info("Project generated successfully using cloud AI")
                return project_description
            
            project_description = self._try_local_generation(prompt)
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
    
    def _try_local_generation(self, prompt: str) -> Optional[str]:
        """Try to generate project using local AI"""
        logger.info(f"🏠 _try_local_generation() CALLED")
        logger.info(f"📏 Prompt length: {len(prompt)} characters")
        
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
                temperature=temperature
            )
            
            logger.info(f"📥 local_ai.generate_response() RETURNED")
            logger.info(f"📏 Response length: {len(response) if response else 0} characters")
            logger.info(f"📄 Response content: {response[:300] if response else 'None'}...")
            
            if response and len(response.strip()) > 50:  
                logger.info(f"✅ Local AI generated valid response: {len(response)} characters")
                return response
            else:
                logger.warning(f"⚠️ Local AI response too short or empty: {len(response) if response else 0} characters")
        except Exception as e:
            logger.error(f"💥 EXCEPTION in _try_local_generation: {str(e)}")
            logger.error(f"🔍 Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"📜 Full traceback: {traceback.format_exc()}")
        
        logger.info(f"❌ _try_local_generation() returning None")
        return None
    
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
            # Use only local AI
            task_headers = self._try_local_generation(prompt)
            if task_headers:
                logger.info("✅ Task headers generated successfully using local AI")
                return task_headers
            logger.error("❌ Failed to generate task headers using local AI")
            return None
        else:
            logger.info(f"☁️ Trying CLOUD AI first for task headers")
            # Try cloud AI first for better quality, then fallback to local
            task_headers = self._try_cloud_generation(prompt)
            if task_headers:
                logger.info("✅ Task headers generated successfully using cloud AI")
                return task_headers
            
            logger.info(f"🔄 Cloud AI failed, falling back to LOCAL AI")
            task_headers = self._try_local_generation(prompt)
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
        prompt = create_task_detail_prompt(task_name, task_number, project_description, selected_language, completed_tasks_summary)
        logger.info(f"Task detail prompt length: {len(prompt)} characters")
        
        if use_local_only:
            task_detail = self._try_local_generation(prompt)
            if task_detail:
                logger.info(f"Task {task_number} details generated successfully using local AI")
                return task_detail
            logger.error(f"Failed to generate task {task_number} details using local AI")
            return None
        else:
            task_detail = self._try_cloud_generation(prompt)
            if task_detail:
                logger.info(f"Task {task_number} details generated successfully using cloud AI")
                return task_detail
            
            task_detail = self._try_local_generation(prompt)
            if task_detail:
                logger.info(f"Task {task_number} details generated successfully using local AI")
                return task_detail
            
            logger.error(f"Failed to generate task {task_number} details using both cloud and local AI")
            return None 