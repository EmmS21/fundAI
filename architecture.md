# FundaAI Repository Architecture

## Executive Summary

FundaAI is a comprehensive AI-powered educational ecosystem designed to provide offline-capable learning tools for students across Africa. The repository is structured as a monorepo containing multiple interconnected services that work together to deliver personalized, AI-driven educational experiences.

## System Overview

The FundaAI ecosystem consists of several key components:

1. **Authentication & User Management** (FundaVault)
2. **Content Distribution** (FundAIHub)
3. **Desktop Applications** (The Engineer, The Examiner)
4. **Content Processing** (QA Extractor, Virtual Library)
5. **Frontend Store** (Electron-based Store)

## High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        A[Student Laptop]
        B[Store Frontend]
        C[Desktop Apps]
    end
    
    subgraph "Core Services"
        D[FundaVault<br/>Auth Service]
        E[FundAIHub<br/>Content Distribution]
    end
    
    subgraph "Content Processing"
        F[QA Extractor<br/>PDF Processing]
        G[Virtual Library<br/>Book Management]
    end
    
    subgraph "Storage Layer"
        H[PostgreSQL<br/>User Data]
        I[Supabase<br/>App Storage]
        J[MongoDB<br/>Question Banks]
        K[Firebase<br/>Real-time Data]
    end
    
    subgraph "AI Services"
        L[Local AI Models<br/>llama-cpp]
        M[Cloud AI<br/>Groq API]
    end
    
    A --> B
    B --> D
    B --> E
    C --> D
    C --> E
    C --> L
    C --> M
    D --> H
    E --> I
    E --> H
    F --> J
    G --> K
    C --> J
    C --> K
```

## Service Breakdown

### 1. FundaVault (Authentication Service)
**Technology**: Python/FastAPI, PostgreSQL
**Purpose**: Central authentication and user management

```mermaid
graph LR
    A[Device Registration] --> B[JWT Token Generation]
    B --> C[Subscription Management]
    C --> D[User Profile Storage]
    D --> E[Token Validation]
```

**Key Features**:
- Device-based authentication
- Subscription tracking (30-day cycles)
- JWT token generation and validation
- User profile management
- Admin operations

### 2. FundAIHub (Content Distribution)
**Technology**: Go, PostgreSQL, Supabase
**Purpose**: App store and content distribution

```mermaid
graph LR
    A[Content Upload] --> B[Version Management]
    B --> C[Download Control]
    C --> D[Access Validation]
    D --> E[Content Delivery]
```

**Key Features**:
- App store management
- Download control and tracking
- Content versioning
- Subscription-based access control
- Integration with FundaVault for authentication

### 3. The Engineer (Desktop App)
**Technology**: Python/PySide6, SQLite, Local AI
**Purpose**: Engineering thinking assessment for ages 12-18

```mermaid
graph TB
    A[User Interface<br/>PySide6] --> B[Assessment Engine]
    B --> C[Local AI<br/>llama-cpp]
    B --> D[Cloud AI<br/>Groq Fallback]
    C --> E[SQLite Database]
    D --> E
    E --> F[Progress Tracking]
```

**Key Features**:
- Engineering thinking assessment
- Local AI processing with cloud fallback
- Kid-friendly interface
- Offline capability
- Progress tracking

### 4. The Examiner (Desktop App)
**Technology**: Python/PySide6, SQLite, MongoDB, Firebase
**Purpose**: Comprehensive exam preparation platform

```mermaid
graph TB
    A[Main Window] --> B[Question View]
    A --> C[Report View]
    A --> D[Profile Management]
    
    B --> E[AI Marking Engine]
    E --> F[Local AI<br/>llama-cpp]
    E --> G[Cloud AI<br/>Groq]
    
    H[MongoDB<br/>Question Banks] --> B
    I[Firebase<br/>Sync] --> D
    J[SQLite<br/>Local Cache] --> B
```

**Key Features**:
- Comprehensive exam preparation
- AI-powered answer evaluation
- Multi-subject support
- Offline-first with cloud sync
- Detailed performance analytics

### 5. QA Extractor (Content Processing)
**Technology**: Python, Dagger, MongoDB
**Purpose**: Automated extraction of questions and answers from PDFs

```mermaid
graph LR
    A[PDF Ingestion] --> B[OCR Processing]
    B --> C[Question Extraction]
    C --> D[Answer Processing]
    D --> E[MongoDB Storage]
    E --> F[Quality Validation]
```

**Key Features**:
- Automated PDF processing
- Question and answer extraction
- AI-powered content analysis
- MongoDB storage
- Quality validation

### 6. Virtual Library (Book Management)
**Technology**: Python, Firebase, Google Drive, Modal
**Purpose**: AI-powered book processing and management

```mermaid
graph TB
    A[Google Drive<br/>Book Discovery] --> B[PDF Processing]
    B --> C[Vector Embeddings<br/>Nomic Embed]
    C --> D[Firebase Storage]
    D --> E[Offline Access]
    
    F[Modal<br/>Cloud Processing] --> B
    G[Sync Orchestrator] --> A
```

**Key Features**:
- Automated book discovery
- Vector embedding generation
- Firebase integration
- Cloud processing via Modal
- Offline access management

### 7. Store Frontend (Electron App)
**Technology**: React, TypeScript, Electron, Firebase
**Purpose**: Desktop store interface for app discovery and management

```mermaid
graph LR
    A[React UI] --> B[Electron Shell]
    B --> C[Firebase Auth]
    C --> D[FundAIHub API]
    D --> E[Download Manager]
```

**Key Features**:
- Cross-platform desktop app
- App discovery and browsing
- Download management
- User authentication
- Admin dashboard

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant S as Student
    participant SF as Store Frontend
    participant FV as FundaVault
    participant FH as FundAIHub
    participant DA as Desktop App
    participant AI as AI Services
    
    S->>SF: Launch Store
    SF->>FV: Authenticate Device
    FV-->>SF: JWT Token
    SF->>FH: Request App List
    FH-->>SF: Available Apps
    S->>SF: Download App
    SF->>FH: Start Download
    FH-->>SF: Download URL
    SF->>DA: Install App
    
    S->>DA: Use App
    DA->>AI: Process Content
    AI-->>DA: AI Response
    DA->>DA: Store Progress
    DA->>FV: Sync Data (Optional)
```

## Integration Points

### Authentication Flow
1. **Device Registration**: Devices register with FundaVault
2. **Token Generation**: FundaVault generates JWT tokens with subscription data
3. **Content Access**: FundAIHub validates tokens for content access
4. **Local Validation**: Desktop apps can validate tokens locally

### Content Distribution Flow
1. **Content Upload**: Admins upload apps to FundAIHub
2. **Version Management**: FundAIHub manages app versions
3. **Download Control**: Subscription-based download access
4. **Local Installation**: Apps install locally on student devices

### AI Processing Flow
1. **Local Processing**: Desktop apps use local AI models when available
2. **Cloud Fallback**: Cloud AI (Groq) used when local AI unavailable
3. **Hybrid Approach**: Intelligent routing based on complexity and availability

## Technology Stack Summary

| Service | Language | Framework | Database | AI | Deployment |
|---------|----------|-----------|----------|----|-----------| 
| FundaVault | Python | FastAPI | PostgreSQL | - | Render |
| FundAIHub | Go | HTTP Server | PostgreSQL | - | Render |
| The Engineer | Python | PySide6 | SQLite | llama-cpp/Groq | Local |
| The Examiner | Python | PySide6 | SQLite/MongoDB | llama-cpp/Groq | Local |
| QA Extractor | Python | Dagger | MongoDB | LLM APIs | Modal |
| Virtual Library | Python | - | Firebase | Nomic Embed | Modal |
| Store Frontend | TypeScript | React/Electron | Firebase | - | Local |

## Key Architectural Principles

### 1. Offline-First Design
- Desktop apps work without internet connection
- Local AI models for privacy and performance
- Local data storage with optional cloud sync

### 2. Microservice Architecture
- Loosely coupled services
- Independent deployment and scaling
- Clear service boundaries

### 3. Security by Design
- Device-based authentication
- JWT tokens with subscription data
- Local validation capabilities
- Minimal data collection

### 4. Educational Focus
- Age-appropriate interfaces
- Progressive difficulty
- Comprehensive progress tracking
- Multi-subject support

## Deployment Architecture

```mermaid
graph TB
    subgraph "Cloud Services"
        A[Render<br/>FundaVault]
        B[Render<br/>FundAIHub]
        C[Modal<br/>Processing]
    end
    
    subgraph "Storage"
        D[PostgreSQL<br/>User Data]
        E[Supabase<br/>App Storage]
        F[MongoDB<br/>Content]
        G[Firebase<br/>Real-time]
    end
    
    subgraph "Student Devices"
        H[Linux Laptops]
        I[macOS Devices]
        J[Windows Devices]
    end
    
    A --> D
    B --> E
    B --> D
    C --> F
    C --> G
    
    H --> A
    H --> B
    I --> A
    I --> B
    J --> A
    J --> B
```

## Future Roadmap

### Short-term (3 months)
- Complete QA Extractor integration
- Enhanced Virtual Library features
- Improved offline synchronization

### Medium-term (6 months)
- Mobile companion apps
- Advanced analytics dashboard
- Multi-language support

### Long-term (12 months)
- Collaborative learning features
- Advanced AI tutoring
- Expanded subject coverage

---

