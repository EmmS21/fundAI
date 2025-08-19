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
    
    def _try_cloud_generation(self, prompt: str, streaming_callback=None) -> Optional[str]:
        """Try generating using cloud AI"""
        if not self.cloud_ai or not self.cloud_ai.is_available():
            return None
        
        try:
            # Cloud AI doesn't support streaming callback yet, so just generate normally
            result = self.cloud_ai.generate_report_from_prompt(prompt)
            if isinstance(result, dict) and "content" in result:
                return result["content"]
            elif isinstance(result, dict) and "error" not in result:
                return str(result)
            return None
        except Exception as e:
            logger.error(f"Cloud AI generation failed: {e}")
            return None
    
    def _try_local_generation(self, prompt: str, streaming_callback=None) -> Optional[str]:
        """Try generating using local AI"""
        if not self.local_ai or not self.local_ai.is_available():
            return None
        
        try:
            return self.local_ai.generate_response(prompt, streaming_callback=streaming_callback)
        except Exception as e:
            logger.error(f"Local AI generation failed: {e}")
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
                            selected_language: str, use_local_only: bool = False, completed_tasks_summary: str = "", 
                            streaming_callback=None) -> Optional[str]:
        """
        Generate detailed content for a specific task
        
        Args:
            task_name: Name of the task to generate details for
            task_number: Number of the task (1-4)
            project_description: The full project description
            selected_language: Programming language for the project
            use_local_only: Whether to use only local AI
            streaming_callback: Optional callback for streaming updates
            
        Returns:
            Generated task details or None if generation failed
        """
        prompt = create_task_detail_prompt(task_name, task_number, project_description, selected_language, completed_tasks_summary)
        logger.info(f"Task detail prompt length: {len(prompt)} characters")
        
        if use_local_only:
            task_detail = self._try_local_generation(prompt, streaming_callback)
            if task_detail:
                logger.info(f"Task {task_number} details generated successfully using local AI")
                return task_detail
            logger.error(f"Failed to generate task {task_number} details using local AI")
            return None
        else:
            task_detail = self._try_cloud_generation(prompt, streaming_callback)
            if task_detail:
                logger.info(f"Task {task_number} details generated successfully using cloud AI")
                return task_detail
            
            task_detail = self._try_local_generation(prompt, streaming_callback)
            if task_detail:
                logger.info(f"Task {task_number} details generated successfully using local AI")
                return task_detail
            
            logger.error(f"Failed to generate task {task_number} details using both cloud and local AI")
            return None 