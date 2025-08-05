# The Examiner AI Tutor - Project Structure Analysis

## Overview
The Examiner is a desktop educational AI application built with Python and Qt6, designed to evaluate student answers and provide intelligent feedback. It supports both local and cloud-based AI inference.

## AI Model Architecture

### Local AI Models
**Expected Location:**
```
~/Documents/models/llama/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf
```

**Fallback Locations:**
- **Packaged App:** `[app_bundle]/models/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf`
- **Development:** `~/Documents/models/llama/[MODEL_FILENAME]`

**Model Requirements:**
- **Format:** GGUF (llama.cpp compatible)
- **Engine:** llama-cpp-python
- **Context Size:** 2048 tokens
- **Max Tokens:** 1024 tokens generation
- **Architecture Support:** x86-64 (optimized), ARM64 (graceful degradation)

### Cloud AI Integration
**Provider:** Groq API
- **Model:** `deepseek-r1-distill-llama-70b`
- **Fallback:** When local model unavailable
- **Configuration:** API key via `src/config/secrets.py`

## Framework Stack

### Core Framework
- **GUI:** PySide6 (Qt6) - Cross-platform desktop interface
- **Language:** Python 3.11+
- **Packaging:** PyInstaller for executable generation
- **Build System:** Docker for cross-platform compilation

### Database & Storage
- **Local DB:** SQLite with SQLAlchemy ORM
- **Models:** `src/data/database/models.py`
- **Operations:** `src/data/database/operations.py`
- **Cloud Storage:** Firebase integration for sync

### Key Dependencies
```
PySide6==6.8.0.2         # Qt6 GUI framework
llama-cpp-python==0.3.9  # Local AI inference (optional on ARM64)
groq>=0.5.0              # Cloud AI API
sqlalchemy               # Database ORM
firebase-admin           # Cloud integration
```

## Project Structure

### Core Directories
```
src/
├── core/                 # Core application logic
│   ├── ai/              # AI inference modules
│   │   ├── marker.py    # Local AI evaluation
│   │   ├── groq_client.py # Cloud AI client
│   │   └── prompt_examples.py # Few-shot examples
│   ├── firebase/        # Cloud integration
│   ├── mongodb/         # Alternative cloud DB
│   └── services.py      # Service orchestration
├── data/                # Data management
│   ├── database/        # Local database
│   ├── cache/          # Question/answer caching
│   └── secure/         # Secure storage
├── ui/                  # User interface
│   ├── components/      # Reusable UI components
│   ├── views/          # Main application views
│   └── main_window.py  # Primary window
└── utils/              # Utility functions
```

### AI Integration Points

#### 1. Local AI (`src/core/ai/marker.py`)
```python
# Optional import pattern for cross-platform compatibility
try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    Llama = None
    LLAMA_AVAILABLE = False

def run_ai_evaluation(question_data, correct_answer_data, user_answer, marks):
    """Main evaluation function with fallback logic"""
    if not LLAMA_AVAILABLE:
        logger.warning("Local AI unavailable, use cloud AI instead")
        return None
```

#### 2. Cloud AI (`src/core/ai/groq_client.py`)
```python
class GroqClient:
    def __init__(self):
        self.client = Groq(api_key=get_groq_api_key())
    
    def generate_report_from_prompt(self, prompt_string):
        """Cloud-based evaluation with structured parsing"""
```

## Building Compatible AI Tutors

### 1. AI Interface Contract
Your AI tutor should implement these key methods:

```python
def run_ai_evaluation(question_data: Dict, correct_answer_data: Dict, 
                     user_answer: Dict[str, str], marks: Optional[int]) -> Optional[Tuple[Dict, str]]:
    """
    Returns: (results_dict, raw_response)
    results_dict format: {"Grade": str, "Rationale": str, "Study Topics": str}
    """
```

### 2. Model Integration Patterns

**For Local Models:**
```python
# Place model in standard location
~/Documents/models/llama/[YOUR_MODEL].gguf

# Update configuration
MODEL_FILENAME = "your-model-name.gguf"
CONTEXT_SIZE = 4096  # Adjust as needed
```

**For Cloud APIs:**
```python
# Add to src/core/ai/your_client.py
class YourAIClient:
    def generate_report_from_prompt(self, prompt_string: str) -> Dict:
        # Your implementation
        pass
```

### 3. Cross-Platform Considerations

**Architecture Support:**
- **x86-64:** Full optimization with SIMD instructions
- **ARM64:** Graceful degradation, cloud-only mode
- **Docker builds:** Automatic architecture detection

**Build Configuration:**
```dockerfile
# In Dockerfile.buildenv
RUN if [ "$(uname -m)" = "aarch64" ]; then \
        echo "ARM64 detected - skipping complex models"; \
    else \
        # Install your x86-64 optimized dependencies
    fi
```

### 4. Integration Steps

1. **Create AI Module:**
   ```
   src/core/ai/your_tutor.py
   ```

2. **Implement Interface:**
   ```python
   def evaluate_subject_specific(question_data, user_answer):
       # Your subject-specific logic
       pass
   ```

3. **Add to Service Registry:**
   ```python
   # In src/core/services.py
   from .ai.your_tutor import YourTutor
   ```

4. **Update UI Integration:**
   ```python
   # In src/ui/views/question_view.py
   # Add your tutor to available AI backends
   ```

## Configuration Management

### Environment Variables
```python
# src/config/secrets.py
def get_your_api_key():
    return os.getenv('YOUR_API_KEY')

# src/config/settings.ini
[AI]
default_backend = groq  # or local, or your_tutor
model_path = ~/Documents/models/llama/
```

### Model Management
- **Download:** Models auto-download or manual placement
- **Versioning:** Filename-based model versioning
- **Fallbacks:** Always provide cloud alternative

## Testing & Deployment

### Local Development
```bash
# Run from source
python src/main.py

# Test specific AI module
python -m pytest tests/test_your_tutor.py
```

### Cross-Platform Building
```bash
# Default x86-64 build (production)
./build.sh

# ARM64 build (testing)
./build.sh --arch arm64

# Your custom tutor build
./build.sh --tutor your_tutor_name
```

### Packaging Considerations
- **Model Size:** Large models increase package size
- **Dependencies:** Optional imports for platform compatibility
- **Distribution:** Separate model downloads vs bundled

## Best Practices for New AI Tutors

1. **Graceful Degradation:** Always provide fallbacks
2. **Optional Dependencies:** Use try/except for platform-specific libraries
3. **Structured Output:** Follow the established JSON format
4. **Logging:** Comprehensive logging for debugging
5. **Error Handling:** Robust error handling with user-friendly messages
6. **Performance:** Consider model size vs accuracy trade-offs
7. **Subject Specialization:** Leverage domain-specific knowledge

## Example: Subject-Specific Tutor

```python
# src/core/ai/math_tutor.py
class MathTutor:
    def __init__(self):
        self.specialized_prompts = {
            'algebra': "Focus on algebraic manipulation...",
            'geometry': "Consider geometric relationships...",
            'calculus': "Analyze derivatives and integrals..."
        }
    
    def evaluate_math_problem(self, question_data, user_answer):
        subject = self.detect_math_subject(question_data)
        prompt = self.build_specialized_prompt(subject, question_data, user_answer)
        return self.generate_evaluation(prompt)
```

This architecture allows for:
- **Easy integration** of new AI tutors
- **Subject specialization** while maintaining consistency
- **Cross-platform compatibility** with graceful degradation
- **Flexible deployment** options (local, cloud, hybrid)
