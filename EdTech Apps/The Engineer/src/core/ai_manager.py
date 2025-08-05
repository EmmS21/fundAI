import os
from pathlib import Path

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    Llama = None
    LLAMA_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    Groq = None
    GROQ_AVAILABLE = False

class AIManager:
    def __init__(self):
        self.local_model = None
        self.groq_client = None
        self.local_ready = False
        self.cloud_ready = False
        
        self._setup_local()
        self._setup_cloud()
    
    def _setup_local(self):
        if not LLAMA_AVAILABLE:
            return
        
        model_path = Path.home() / "Documents" / "models" / "llama" / "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"
        
        if not model_path.exists():
            return
        
        try:
            self.local_model = Llama(
                model_path=str(model_path),
                n_ctx=2048,
                verbose=False
            )
            self.local_ready = True
        except Exception:
            pass
    
    def _setup_cloud(self):
        if not GROQ_AVAILABLE:
            return
        
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            return
        
        try:
            self.groq_client = Groq(api_key=api_key)
            self.cloud_ready = True
        except Exception:
            pass
    
    def is_local_available(self):
        return self.local_ready
    
    def is_cloud_available(self):
        return self.cloud_ready
    
    def test_connection(self):
        if self.local_ready:
            try:
                response = self.local_model("Hello", max_tokens=5)
                return "Local AI working"
            except Exception:
                return "Local AI error"
        
        if self.cloud_ready:
            try:
                completion = self.groq_client.chat.completions.create(
                    model="deepseek-r1-distill-llama-70b",
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5
                )
                return "Cloud AI working"
            except Exception:
                return "Cloud AI error"
        
        return "No AI available" 