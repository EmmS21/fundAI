# The Engineer AI Tutor

A simple AI tutor for teaching engineering thinking to young people (ages 12-18).

## Features

- **Engineering Thinking Assessment**: Evaluates problem-solving and logical thinking skills
- **Local AI Model**: Uses local LLAMA models for privacy
- **Cloud AI Fallback**: Falls back to Groq API when local AI unavailable
- **SQLite Database**: Simple local data storage
- **Kid-Friendly UI**: Designed for 12-18 year old learners

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up AI Models**
   - For local AI: Place your GGUF model at:
     `~/Documents/models/llama/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf`
   - For cloud AI: Copy `config.example` to `.env` and add your Groq API key

3. **Run the Application**
   ```bash
   python src/main.py
   ```

## AI Configuration

### Local AI (Recommended)
- Download a GGUF model (like DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf)
- Place it in `~/Documents/models/llama/`
- The app will automatically detect and use it

### Cloud AI (Fallback)
- Get a free API key from [Groq](https://groq.com)
- Set `GROQ_API_KEY` in your `.env` file
- The app will use cloud AI if local AI is unavailable

## Assessment

The onboarding includes 5 engineering thinking questions:
1. **Problem Solving**: Breaking down complex tasks
2. **Logical Thinking**: Organizing and sorting concepts  
3. **Pattern Recognition**: Finding and explaining patterns
4. **System Thinking**: Understanding how systems work
5. **Debugging Mindset**: Problem diagnosis and solving

## Target Audience

Designed for young learners (12-18) with little to no programming experience. Focuses on developing engineering thinking skills rather than specific coding knowledge.

## Architecture

- **Frontend**: PySide6 (Qt6) GUI
- **AI**: Local LLAMA models + Groq cloud fallback
- **Database**: SQLite for local data storage
- **Assessment**: Pseudo-code focused engineering thinking evaluation 