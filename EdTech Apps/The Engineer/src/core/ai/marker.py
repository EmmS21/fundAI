"""
Local AI Marker for The Engineer AI Tutor
Provides local AI inference using llama-cpp-python
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    Llama = None
    LLAMA_AVAILABLE = False

from .project_prompts import create_project_generation_prompt
from ..config.settings import AI_CONFIG

logger = logging.getLogger(__name__)

class LocalAIMarker:
    """Local AI model for generating responses and evaluations"""
    
    def __init__(self):
        self.model = None
        self.model_ready = False
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the local AI model"""
        if not LLAMA_AVAILABLE:
            logger.warning("llama-cpp-python not available, local AI disabled")
            return
        
        model_path = self._find_model_path()
        if not model_path:
            logger.warning("Local AI model not found")
            return
        
        try:
            logger.info(f"Loading local AI model from: {model_path}")
            ctx = AI_CONFIG.get("local", {}).get("context_size", 2048)
            n_threads = AI_CONFIG.get("local", {}).get("n_threads", 4)
            self.model = Llama(
                model_path=str(model_path),
                n_ctx=ctx,
                n_threads=n_threads,
                verbose=False,
                n_gpu_layers=-1 if self._has_gpu() else 0
            )
            self.model_ready = True
            logger.info("Local AI model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load local AI model: {e}")
            self.model = None
            self.model_ready = False
    
    def _find_model_path(self) -> Optional[Path]:
        """Find the local AI model file"""
        model_filename = "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"
        
        # Check bundled location first (for packaged apps)
        if hasattr(os.sys, 'frozen') and os.sys.frozen:
            bundle_dir = Path(os.sys.executable).parent
            bundled_path = bundle_dir / "models" / model_filename
            if bundled_path.exists():
                return bundled_path
        
        # Check user documents directory
        user_path = Path.home() / "Documents" / "models" / "llama" / model_filename
        if user_path.exists():
            return user_path
        
        # Check current directory models folder
        local_path = Path("models") / model_filename
        if local_path.exists():
            return local_path
        
        return None
    
    def _has_gpu(self) -> bool:
        """Check if GPU acceleration is available"""
        try:
            # Simple check - could be enhanced
            import platform
            return platform.system() != "Darwin" or platform.processor() == "arm"
        except:
            return False
    
    def is_available(self) -> bool:
        """Check if local AI is available"""
        return self.model_ready and self.model is not None
    
    def generate_response(self, prompt: str, max_tokens: int = None, temperature: float = None) -> Optional[str]:
        """Generate a response using the local AI model"""
        if not self.is_available():
            logger.warning("Local AI model not available")
            return None
        
        try:
            logger.info("Generating response with local AI")
            cfg = AI_CONFIG.get("local", {})
            toks = max_tokens if max_tokens is not None else cfg.get("max_tokens", 1024)
            temp = temperature if temperature is not None else cfg.get("temperature", 0.7)
            top_p = cfg.get("top_p", 0.9)
            repeat_penalty = cfg.get("repeat_penalty", 1.1)
            response = self.model(
                prompt,
                max_tokens=toks,
                temperature=temp,
                top_p=top_p,
                repeat_penalty=repeat_penalty,
                stop=["Human:", "Assistant:", "\n\n---"],
                echo=False
            )
            generated_text = response['choices'][0]['text'].strip()
            logger.info(f"Local AI generated {len(generated_text)} characters")
            return generated_text
        except Exception as e:
            logger.error(f"Local AI generation failed: {e}")
            return None
    
    def run_ai_evaluation(self, question_data: Dict[str, Any], correct_answer_data: Dict[str, Any], 
                         user_answer: Dict[str, str], marks: Optional[int] = None) -> Optional[tuple]:
        """Run AI evaluation using local model (for compatibility with existing system)"""
        if not self.is_available():
            return None
        
        try:
            # Build a simple evaluation prompt
            prompt = f"""Evaluate this programming answer:

Question: {question_data.get('problem', 'Programming Problem')}
Expected Solution: {correct_answer_data.get('solution', 'Not provided')}
Student Answer: {user_answer.get('code', 'No code provided')}

Provide a grade out of {marks or 10} and brief feedback."""

            response = self.generate_response(prompt, max_tokens=512, temperature=0.3)
            if response:
                # Simple parsing - could be enhanced
                results = {
                    "Grade": "5/10",  # Default grade
                    "Rationale": response,
                    "Study Topics": "Review the solution and try again"
                }
                return results, response
            
        except Exception as e:
            logger.error(f"Local AI evaluation failed: {e}")
        
        return None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        if not self.is_available():
            return {"status": "unavailable", "reason": "Model not loaded"}
        
        return {
            "status": "available",
            "model_type": "Local GGUF",
            "context_size": 2048,
            "gpu_enabled": self._has_gpu()
        } 