# MoneyWise Academy 💰

> Financial literacy AI tutor for ages 12-18

MoneyWise Academy is an offline-first desktop application that teaches financial literacy concepts through interactive lessons, quizzes, and AI-powered tutoring.

**Current Phase:** Initial Setup & Planning | **Version:** 0.1.0 (Skeleton)

**Task Management:** All development tasks tracked in Linear

---

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Device Identification (Critical)](#-device-identification-shared-across-ai-tutors)
- [Features](#-features)
- [Setup](#-setup)
- [Development](#-development)
- [Project Structure](#-project-structure)
- [Educational Content](#-educational-content)

---

## 🏗️ Architecture

MoneyWise Academy follows a **three-tier offline-first architecture** matching The Engineer and The Examiner:

### Local Layer
- **SQLite Database**: User data, progress, and content cache
- **Local LLM**: Privacy-first AI tutoring (llama-cpp-python with GGUF models)
- **Device UUID**: Shared hardware identification (see below)

### Network Layer
- **Network Monitor**: Detects online/offline state
- **Queue Manager**: Processes background tasks and queued operations
- **Differential Sync**: Efficient data synchronization when online

### Cloud Layer
- **MongoDB**: Cloud data persistence and cross-device sync
- **Firebase**: Authentication and real-time sync
- **Groq AI**: Cloud AI fallback for high-quality responses

**Design Principles:**
- ✅ Offline-first (works without internet)
- ✅ Local data + Cloud sync
- ✅ Privacy-focused (local AI preferred)
- ✅ Multi-device support

---

## 🔑 Device Identification (Shared Across AI Tutors)

### ⚠️ Critical for Engineers

MoneyWise Academy uses a **SHARED hardware ID** system with all fundAI AI Tutor applications.

**Storage Location:** `~/.ai_tutors/hardware_id.json`

**Shared By:**
- The Engineer
- The Examiner  
- MoneyWise Academy
- All future fundAI AI Tutor apps

### Why Shared?

1. **Unified User Identity**: Same user recognized across all tutors
2. **Subscription Management**: One subscription works across all apps
3. **Cross-App Features**: (Future) Progress tracking across subjects
4. **Simplified Licensing**: One device, one ID, all apps

### How It Works

```python
from src.utils.hardware_identifier import HardwareIdentifier

# Get the shared hardware ID
device_id = HardwareIdentifier.get_hardware_id()
# Returns same UUID across all AI Tutor apps on this device
```

**The hardware ID is:**
- Generated once per device (random UUID)
- Stored in `~/.ai_tutors/hardware_id.json` (SHARED location)
- Persists across app reinstalls
- Consistent across all fundAI AI Tutor applications

**File Format:**
```json
{
  "hardware_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Implementation:** See `src/utils/hardware_identifier.py`

---

## 📋 Features

### Implemented (Skeleton)
- ✅ Shared hardware identification system
- ✅ Network monitoring (offline/online detection)
- ✅ Configuration management (settings + secrets)
- ✅ Basic project structure

### Planned
- 🤖 AI tutor (local LLM + Groq cloud fallback)
- 📚 Comprehensive financial literacy curriculum
- 📊 Progress tracking and analytics
- 🎯 Gamification (achievements, badges, streaks)
- 💯 Interactive quizzes and assessments
- 🔄 Multi-device sync
- 🎨 Modern, kid-friendly UI (PySide6)
- 🔒 Privacy-focused (local-first, COPPA compliant)

---

## 🚀 Setup

### Prerequisites

- **Python 3.8+** (3.10+ recommended)
- **Poetry** for dependency management ([install guide](https://python-poetry.org/docs/#installation))
- **macOS or Linux** (primary targets)
- **Git** for version control
- **(Optional)** GGUF model for local AI

### Installation Steps

```bash
# 1. Navigate to project directory
cd "EdTech Apps/MoneyWise Academy"

# 2. Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# 3. Install dependencies
poetry install

# 4. Verify installation
poetry run python -c "import PySide6; print('PySide6 installed successfully')"

# 5. Configure environment (optional for local dev)
cp config.example .env
nano .env  # Edit with your API keys

# 6. Run the application
poetry run python src/main.py
# OR use the shortcut
poetry run moneywise
```

**Note:** This project uses Poetry exclusively for dependency management. All dependencies are defined in `pyproject.toml`.

This creates:
- `~/.moneywise/data/moneywise.db` (SQLite database)
- `~/.moneywise/logs/` (log files)
- `~/.moneywise/cache/` (cache directory)
- `~/.ai_tutors/hardware_id.json` (shared device ID)

### Configuration

Edit `.env` file (copy from `config.example`):

```bash
# AI Configuration
GROQ_API_KEY=your_groq_api_key_here  # Optional: for cloud AI

# Cloud Database
MONGODB_URI=your_mongodb_uri_here  # Optional: for cloud sync

# Firebase
FIREBASE_API_KEY=your_key
FIREBASE_PROJECT_ID=your_project
FIREBASE_STORAGE_BUCKET=your_bucket
FIREBASE_CREDENTIALS_PATH=/path/to/credentials.json

# App Settings
ENVIRONMENT=development
DEBUG=true
ENABLE_CLOUD_SYNC=true
ENABLE_LOCAL_AI=true
```

**Note:** All cloud services are optional. App works offline by default.

---

## 🧪 Development

### Poetry Quick Reference

```bash
# Install dependencies
poetry install

# Add a new dependency
poetry add package-name

# Add a dev dependency
poetry add --group dev package-name

# Update dependencies
poetry update

# Run Python scripts
poetry run python src/main.py

# Activate shell in virtual environment
poetry shell

# Show environment info
poetry env info

# Remove virtual environment
poetry env remove python
```

### Running Tests

```bash
# Run all tests
poetry run pytest tests/

# Run specific test file
poetry run pytest tests/unit/test_database.py

# Run with coverage
poetry run pytest --cov=src tests/
```

### Code Quality (Ruff)

We use **ruff** for linting and formatting (replaces black/pylint/mypy):

```bash
# Check code
poetry run ruff check src/

# Auto-fix issues
poetry run ruff check --fix src/

# Format code
poetry run ruff format src/

# Run all checks
poetry run ruff check src/ && poetry run ruff format --check src/
```

Configuration: See `pyproject.toml` (tool.ruff section)

### Common Development Tasks

#### Adding a New View

1. Create view file in `src/ui/views/`
2. Inherit from `QWidget` or `QMainWindow`
3. Implement layout and components
4. Add navigation from main window

#### Adding Database Models

**⚠️ IMPORTANT:** Database schema requires team discussion first!

See the database schema design task in Linear for detailed schema design discussion including:
- User, FinancialConcept, LearningProgress models
- Relationships and constraints
- Indexing strategy
- Cloud sync considerations

Current models are **PLACEHOLDERS** until schema is finalized.

#### Adding API Integration

1. Create client in `src/core/[service]/`
2. Add configuration in `src/config/settings.py`
3. Add secrets in `src/config/secrets.py`
4. Implement retry logic and error handling
5. Write tests

### Debugging

**Logs:** `~/.moneywise/logs/moneywise.log`

```bash
# Tail logs in real-time
tail -f ~/.moneywise/logs/moneywise.log
```

**Database:**

```bash
# Inspect database
sqlite3 ~/.moneywise/data/moneywise.db

# Common queries
.tables                    # List tables
.schema users              # Show table schema
SELECT * FROM users;       # Query data
```

**Hardware ID:**

```bash
# Test hardware identifier
poetry run python src/utils/hardware_identifier.py

# Check shared file
cat ~/.ai_tutors/hardware_id.json
```

### Common Issues

**Import Errors**
- Reinstall dependencies: `poetry install`
- Check Poetry environment: `poetry env info`
- Recreate environment: `poetry env remove python && poetry install`

**Database Errors**
- Reset database: `rm ~/.moneywise/data/moneywise.db`
- Restart app to recreate

**PySide6 Issues**
- macOS: May need to install Qt separately
- Linux: `sudo apt install qt6-base-dev` (Ubuntu/Debian)

**Poetry Issues**
- Update Poetry: `poetry self update`
- Check Python version: `poetry env info`
- Clear cache: `poetry cache clear pypi --all`

---

## 📂 Project Structure

```
MoneyWise Academy/
├── src/
│   ├── main.py                     # Application entry point
│   ├── config/
│   │   ├── settings.py             # App settings & paths
│   │   └── secrets.py              # API keys & credentials
│   ├── core/                       # Business logic
│   │   ├── ai/                     # AI integration (local + cloud)
│   │   ├── mongodb/                # MongoDB client
│   │   ├── firebase/               # Firebase auth & sync
│   │   ├── network/                # Network monitoring & sync
│   │   ├── content/                # Content management
│   │   ├── assessment/             # Quiz system
│   │   ├── analytics/              # Progress tracking
│   │   └── gamification/           # Achievement system
│   ├── ui/                         # User interface (PySide6)
│   │   ├── main_window.py          # Main window
│   │   ├── views/                  # Major views
│   │   │   ├── dashboard_view.py
│   │   │   ├── lesson_view.py
│   │   │   ├── quiz_view.py
│   │   │   └── ...
│   │   └── components/             # Reusable UI components
│   │       ├── common/             # Shared widgets
│   │       ├── onboarding/         # Onboarding flow
│   │       └── profile/            # Profile components
│   ├── utils/
│   │   ├── hardware_identifier.py  # Shared device UUID
│   │   └── network_monitor.py      # Network state detection
│   └── data/
│       ├── database/
│       │   ├── models.py           # SQLAlchemy models (placeholder)
│       │   └── operations.py       # CRUD operations
│       └── cache/                  # Caching system
├── assets/                         # Static assets
│   ├── icons/
│   ├── images/
│   └── illustrations/
├── tests/
│   ├── unit/                       # Unit tests
│   └── integration/                # Integration tests
├── pyproject.toml                  # Poetry config & dependencies
├── .gitignore                      # Git ignore patterns
├── config.example                  # Config template
├── MoneyWiseArchitecture.png       # Architecture diagram
└── README.md                       # This file
```

### Key Files Status

| File | Status | Notes |
|------|--------|-------|
| `src/main.py` | ✅ Skeleton | Basic entry point with logging |
| `src/config/settings.py` | ✅ Complete | Configuration management |
| `src/config/secrets.py` | ✅ Complete | Secrets handling |
| `src/utils/hardware_identifier.py` | ✅ Complete | Matches The Engineer |
| `src/utils/network_monitor.py` | ✅ Complete | Network state detection |
| `src/data/database/models.py` | ⚠️ Placeholder | Requires schema discussion (see Linear) |
| `src/data/database/operations.py` | ⚠️ Placeholder | Depends on models |
| All other `src/` files | 📋 Todo | See Linear for tasks |

---

## 🎓 Educational Content

The curriculum will cover essential financial literacy topics for ages 12-18:

1. **Money Basics**: Understanding money, earning, spending
2. **Saving**: Why save, savings strategies, emergency funds
3. **Banking**: Accounts, interest, loans
4. **Budgeting**: Income, expenses, planning
5. **Credit**: Credit cards, credit scores, managing debt
6. **Investing**: Stocks, bonds, risk and return
7. **Entrepreneurship**: Starting a business, business plans
8. **Financial Planning**: Long-term goals, retirement

**Content Status:** To be developed (see content creation tasks in Linear)

---

## 📖 Documentation

- **Architecture Diagram**: `MoneyWiseArchitecture.png`
- **Task Management**: All tasks tracked in Linear
- **Code of Conduct**: `../../CodeOfConduct.md`

---

## 🤝 Contributing

1. Check Linear for open tasks
2. Create feature branch: `git checkout -b feature/your-feature`
3. Install dependencies: `poetry install`
4. Write tests for new functionality
5. Run code quality checks: `poetry run ruff check src/`
6. Ensure all tests pass: `poetry run pytest tests/`
7. Commit with clear message
8. Push and create pull request

**Note:** All development tasks are tracked in Linear.



---

## 📦 Dependencies

**Core:**
- PySide6 (GUI framework)
- SQLAlchemy (database ORM)
- llama-cpp-python (local AI)
- groq (cloud AI fallback)

**Cloud:**
- firebase-admin (auth & sync)
- pymongo (MongoDB)

**Utilities:**
- python-dotenv (config)
- requests (HTTP)
- Pillow (images)

**Development:**
- pytest (testing)
- ruff (linting & formatting)
- PyInstaller (packaging)

See `requirements.txt` for full list with versions.

---

## 📜 License

[License information to be added]

---

## 🙏 Credits

**Part of the fundAI EdTech suite:**
- **The Engineer**: Engineering thinking tutor
- **The Examiner**: Educational assessment platform
- **MoneyWise Academy**: Financial literacy tutor

**Built by fundAI**

For questions, issues, or contributions, see our team chat or create a GitHub issue.

---

**Next Steps:** Check Linear for current sprint tasks and complete development roadmap.
