"""
Configuration settings for The Engineer AI Tutor
Contains AI model configurations and other settings
"""

# AI Configuration
AI_CONFIG = {
    "local": {
        "model_filename": "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf",
        "context_size": 4096,
        "max_tokens": 1536,
        "temperature": 0.6,
        "n_threads": 4,
    },
    "cloud": {
        "groq_model": "deepseek-r1-distill-llama-70b",
        "max_tokens": 2048,
        "temperature": 0.7,
    }
}

# Database Configuration
DATABASE_CONFIG = {
    "name": "engineer.db",
    "path": "data/",
}

# UI Configuration
UI_CONFIG = {
    "window_title": "The Engineer AI Tutor",
    "min_window_size": (800, 600),
    "default_window_size": (1200, 800),
}

# Assessment Configuration
ASSESSMENT_CONFIG = {
    "max_questions": 5,
    "time_limit_minutes": 30,
    "passing_score": 60,
} 