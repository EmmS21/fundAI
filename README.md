# FundaAI - AI School for Africa

> **Turning self-driven 12-18 year old Africans into globally competitive software engineers through AI-powered education**

## The FundaAI Approach

Our educational model operates on a **two-fold approach**:

### 1. Virtual Campus

Students receive a laptop, running on Linux OS with an "offline AI brain" and an ecosystem of desktop applications (AI Tutors) focused on building skills associated with software engineering. This approach ensures:

**Key Learning Areas:**
- **Problem Solving**: Breaking down complex challenges
- **Pattern Recognition**: Identifying and applying patterns in code and systems
- **Systems Thinking**: Understanding how components work together
- **Software Engineering Fundamentals**: Best practices and methodologies

### 2. Virtual Apprenticeship
**Real-World Engineering Experience**

Students work alongside experienced engineers in a simulated engineering team environment, building and debugging their own AI Tutors. This hands-on approach provides:

- **Mentorship**: Direct guidance from seasoned professionals
- **Real Projects**: Building actual AI applications from scratch
- **Team Collaboration**: Learning to work in engineering teams
- **Industry Practices**: Exposure to professional development workflows

## Repository Structure

This monorepo contains the complete FundaAI ecosystem:

```
fundAI/
├── 🏛️ fundaVault/           # Authentication & User Management
├── 📦 fundAIHub/            # Content Distribution & App Store
├── 🎓 EdTech Apps/          # AI Tutoring Applications
│   ├── The Engineer/        # Engineering Thinking Assessment
│   └── The Examiner/        # Comprehensive Exam Preparation
├── 📚 virtualLibrary/       # AI-Powered Book Management
├── 🔍 qaextractor/          # PDF Processing & Question Extraction
└── 🛒 fundai-edtech-store-fe/ # Desktop Store Interface
```

## Core Services

### 🔐 FundaVault
**Authentication & User Management**
- Device-based authentication system
- Subscription management (30-day cycles)
- JWT token generation and validation
- User profile and progress tracking

### 📦 FundAIHub
**Content Distribution Platform**
- App store for AI tutoring applications
- Download control and version management
- Subscription-based access control
- Integration with authentication services

### 🎓 AI Tutoring Applications

#### The Engineer
- **Target**: Ages 12-18, engineering thinking development
- **Features**: Problem-solving assessment, local AI processing, kid-friendly interface
- **Technology**: Python/PySide6, SQLite, llama-cpp/Groq

#### The Examiner
- **Target**: Comprehensive exam preparation
- **Features**: Multi-subject support, AI-powered evaluation, offline-first design
- **Technology**: Python/PySide6, MongoDB, Firebase, hybrid AI processing

### 📚 Virtual Library
**AI-Powered Book Management**
- Automated book discovery and processing
- Vector embedding generation for AI understanding
- Offline access to educational content
- Cloud synchronization via Modal

### 🔍 QA Extractor
**Content Processing Pipeline**
- Automated PDF processing and question extraction
- AI-powered content analysis
- MongoDB storage and management
- Quality validation and optimization

## 🛠️ Technology Stack

| Service | Technology | Purpose |
|---------|------------|---------|
| **Authentication** | Python/FastAPI, PostgreSQL | User management and security |
| **Content Distribution** | Go, Supabase | App store and delivery |
| **Desktop Apps** | Python/PySide6, SQLite | Local AI tutoring |
| **AI Processing** | llama-cpp, Groq API | Local and cloud AI |
| **Content Processing** | Python, Dagger, MongoDB | PDF and question extraction |
| **Book Management** | Python, Firebase, Modal | Educational content |
| **Store Frontend** | React/TypeScript, Electron | Desktop store interface |

## Getting Started

### For Students
1. **Purchase**: Get a FundaAI laptop with pre-installed AI brain
2. **Setup**: Complete device registration and profile creation
3. **Learn**: Access virtual campus and start with AI tutoring apps
4. **Build**: Join virtual apprenticeship program
5. **Grow**: Develop into a globally competitive software engineer

### For Developers
1. **Clone**: `git clone https://github.com/EmmS21/fundAI.git`
2. **Explore**: Check out individual service documentation
3. **Contribute**: Join our mission to build Africa's next wave of software engineers
4. **Build**: Create new AI tutoring applications

## Documentation

- 📋 [Architecture Overview](./architecture.md) - Complete system architecture
- 🔧 [Service Documentation](./EdTech%20Apps/) - Individual app documentation
- 🚀 [Deployment Guide](./fundAIHub/README.md) - Setup and deployment
- 🧪 [Testing Guide](./qaextractor/README.md) - Testing and validation

## 🤝 Contributing

We welcome contributions from developers who share our vision of democratizing tech education in Africa. Whether you're building new AI tutors, improving existing services, or enhancing the learning experience, your contributions make a difference.

### How to Contribute
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request
5. Join our mission to transform African tech education

## 📞 Contact

**Emmanuel Sibanda** - Founder & Lead Engineer
- Email: emmanuel@emmanuelsibanda.com
- LinkedIn: [Emmanuel Sibanda](https://linkedin.com/in/emmanuelsibanda)

## 📄 License

This project is licensed under the ISC License - see the [LICENSE](LICENSE) file for details.

