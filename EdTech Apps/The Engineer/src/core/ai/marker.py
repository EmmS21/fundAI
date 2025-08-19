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
from config.settings import AI_CONFIG

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
        import psutil
        import gc
        import time
        import threading
        
        logger.info(f"🤖 LocalAIMarker.generate_response() CALLED")
        logger.info(f"📏 Prompt length: {len(prompt)} characters")
        logger.info(f"⚙️ max_tokens param: {max_tokens}")
        logger.info(f"⚙️ temperature param: {temperature}")
        
        # SYSTEM RESOURCE MONITORING
        process = psutil.Process()
        memory_info = process.memory_info()
        print(f"[DEBUG] BEFORE GENERATION - Memory RSS: {memory_info.rss / 1024 / 1024:.1f} MB")
        print(f"[DEBUG] BEFORE GENERATION - Memory VMS: {memory_info.vms / 1024 / 1024:.1f} MB")
        print(f"[DEBUG] BEFORE GENERATION - CPU percent: {process.cpu_percent():.1f}%")
        print(f"[DEBUG] BEFORE GENERATION - System memory: {psutil.virtual_memory().percent:.1f}% used")
        print(f"[DEBUG] BEFORE GENERATION - Available memory: {psutil.virtual_memory().available / 1024 / 1024:.1f} MB")
        
        # GARBAGE COLLECTION STATUS
        gc_stats = gc.get_stats()
        print(f"[DEBUG] BEFORE GENERATION - GC stats: {gc_stats}")
        print(f"[DEBUG] BEFORE GENERATION - GC count: {gc.get_count()}")
        
        if not self.is_available():
            logger.error("❌ Local AI model not available")
            return None
        
        logger.info(f"✅ Local AI model is available")
        print(f"[DEBUG] Model object id: {id(self.model)}")
        print(f"[DEBUG] Model object type: {type(self.model)}")
        
        try:
            logger.info("🔧 Setting up generation parameters")
            cfg = AI_CONFIG.get("local", {})
            toks = max_tokens if max_tokens is not None else cfg.get("max_tokens", 1024)
            temp = temperature if temperature is not None else cfg.get("temperature", 0.7)
            top_p = cfg.get("top_p", 0.9)
            repeat_penalty = cfg.get("repeat_penalty", 1.1)
            
            print(f"[DEBUG] Generation params: max_tokens={toks}, temp={temp}, top_p={top_p}")
            print(f"[DEBUG] Prompt length: {len(prompt)} characters")
            print(f"[DEBUG] Prompt first 200 chars: {prompt[:200]}")
            print(f"[DEBUG] Prompt last 200 chars: {prompt[-200:]}")
            
            logger.info(f"⚙️ Final generation params: max_tokens={toks}, temp={temp}, top_p={top_p}")
            logger.info(f"📏 Final prompt length: {len(prompt)} characters")
            
            # Add timeout monitoring thread
            timeout_occurred = threading.Event()
            
            def timeout_monitor():
                time.sleep(30)  # 30 second timeout
                if not timeout_occurred.is_set():
                    print(f"[DEBUG] TIMEOUT WARNING: Model call has been running for 30+ seconds")
                    memory_info_timeout = process.memory_info()
                    print(f"[DEBUG] TIMEOUT - Memory RSS: {memory_info_timeout.rss / 1024 / 1024:.1f} MB")
                    print(f"[DEBUG] TIMEOUT - CPU percent: {process.cpu_percent():.1f}%")
            
            timeout_thread = threading.Thread(target=timeout_monitor, daemon=True)
            timeout_thread.start()
            
            # Use streaming to see content as it's generated
            logger.info("🚀 Starting streaming generation with self.model()")
            logger.info(f"🔍 Model object: {type(self.model)}")
            print(f"[DEBUG] ABOUT TO CALL self.model() - this is where it might hang")
            print(f"[DEBUG] Current time: {time.time()}")
            
            # Memory snapshot right before model call
            memory_before_call = process.memory_info()
            print(f"[DEBUG] JUST BEFORE MODEL CALL - Memory RSS: {memory_before_call.rss / 1024 / 1024:.1f} MB")
            
            response_stream = self.model(
                prompt,
                max_tokens=toks,
                temperature=temp,
                top_p=top_p,
                repeat_penalty=repeat_penalty,
                stop=["Human:", "Assistant:", "\n\n---"],
                echo=False,
                stream=True
            )
            
            # If we reach here, the model call returned successfully
            timeout_occurred.set()  # Cancel timeout monitoring
            print(f"[DEBUG] SUCCESS: self.model() returned! Time: {time.time()}")
            
            # Memory snapshot after model call
            memory_after_call = process.memory_info()
            print(f"[DEBUG] AFTER MODEL CALL - Memory RSS: {memory_after_call.rss / 1024 / 1024:.1f} MB")
            print(f"[DEBUG] MEMORY DELTA: {(memory_after_call.rss - memory_before_call.rss) / 1024 / 1024:.1f} MB")
            
            logger.info(f"📥 self.model() returned stream object: {type(response_stream)}")
            
            generated_text = ""
            token_count = 0
            chunk_count = 0
            
            logger.info("🔄 Starting to process stream chunks...")
            print(f"[DEBUG] Starting chunk processing loop")
            
            for chunk in response_stream:
                chunk_count += 1
                if chunk_count == 1:
                    logger.info("✅ Received FIRST chunk from stream")
                    print(f"[DEBUG] First chunk received: {chunk}")
                elif chunk_count % 10 == 0:
                    logger.info(f"📊 Processed {chunk_count} chunks so far")
                    # Memory check during processing
                    current_memory = process.memory_info()
                    print(f"[DEBUG] Chunk {chunk_count} - Memory RSS: {current_memory.rss / 1024 / 1024:.1f} MB")
                
                chunk_text = chunk['choices'][0]['text'] if chunk['choices'][0]['text'] else ""
                if chunk_text:
                    generated_text += chunk_text
                    token_count += 1
                    if token_count % 10 == 0:  # Log every 10 tokens for more detail
                        logger.info(f"Token {token_count}: Generated {len(generated_text)} chars total")
                
                # Log if we get empty chunks
                if not chunk_text and chunk_count <= 5:
                    logger.info(f"Chunk {chunk_count}: Empty text")
                    print(f"[DEBUG] Empty chunk {chunk_count}: {chunk}")
            
            print(f"[DEBUG] Stream completed: {chunk_count} chunks, {token_count} tokens, {len(generated_text)} characters")
            logger.info(f"Stream completed: {chunk_count} chunks, {token_count} tokens, {len(generated_text)} characters")
            
            # Final memory check
            final_memory = process.memory_info()
            print(f"[DEBUG] FINAL - Memory RSS: {final_memory.rss / 1024 / 1024:.1f} MB")
            print(f"[DEBUG] TOTAL MEMORY DELTA: {(final_memory.rss - memory_info.rss) / 1024 / 1024:.1f} MB")
            
            if len(generated_text) == 0:
                print("[DEBUG] Generated text is empty - model may have hit limits or failed to start")
                logger.error("Generated text is empty - model may have hit limits or failed to start")
                
            return generated_text.strip()
        except Exception as e:
            timeout_occurred.set()  # Cancel timeout monitoring
            print(f"[DEBUG] EXCEPTION in generate_response: {str(e)}")
            print(f"[DEBUG] Exception type: {type(e).__name__}")
            import traceback
            print(f"[DEBUG] Full traceback: {traceback.format_exc()}")
            
            # Memory check during exception
            exception_memory = process.memory_info()
            print(f"[DEBUG] EXCEPTION - Memory RSS: {exception_memory.rss / 1024 / 1024:.1f} MB")
            
            logger.error(f"Error in local AI generation: {str(e)}")
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