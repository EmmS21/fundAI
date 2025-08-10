"""
Project Generator Service for The Engineer AI Tutor
Uses existing AI infrastructure to generate contextual programming projects
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

from .project_prompts import create_project_generation_prompt

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
        if not self.local_ai:
            return None
        
        try:
            # Use the local AI marker's generation capability
            response = self.local_ai.generate_response(prompt)
            if response and len(response.strip()) > 100:  # Basic validation
                return response
        except Exception as e:
            logger.warning(f"Local AI project generation failed: {e}")
        
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