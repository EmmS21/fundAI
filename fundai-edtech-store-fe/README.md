# FundaAI EdTech Store

A desktop application serving as the frontend for the FundaAI EdTech Store. FundaAI is an AI-powered educational platform designed for self-driven students across Africa, helping them improve their grades and build critical thinking skills.

## Overview

This application provides a user-friendly interface for students to discover, download, and manage educational applications from the FundaAI ecosystem.

## Features

- Browse and search available educational applications
- Download and install applications
- User authentication and profile management
- Admin dashboard for managing applications and users
- Cross-platform support (Linux, macOS)

## Tech Stack

- **Frontend**: React 19, TypeScript, Tailwind CSS
- **Desktop Framework**: Electron
- **State Management**: Zustand
- **Authentication**: Firebase
- **File Handling**: React Dropzone
- **Notifications**: React Toastify
- **Build Tools**: Vite, Electron Builder

## Development

### Prerequisites

- Node.js (LTS version recommended)
- npm or yarn

### Installation

```bash
# Clone the repository
git clone https://github.com/EmmS21/fundAI.git
cd fundai-edtech-store-fe

# Install dependencies
npm install
```

### Running Development Environment

```bash
# Start the development server with hot reload
npm start
```

This command will:
1. Start the Vite development server
2. Launch the Electron application pointing to the dev server

### Testing

```bash
# Run tests
npm test
```

## Building and Distribution

### Building for Development

```bash
# Build the application
npm run build
```

### Creating Distribution Packages

#### For macOS and Linux

```bash
npm run electron:build
```

#### For Linux Only (with GitHub Release)

```bash
npm run build && npx electron-builder --linux --publish always
```

This command builds the application and publishes the artifacts to GitHub releases.

## Project Structure

- `/src` - React application source code
- `/electron` - Electron main process code
- `/dist` - Built application files
- `/release` - Generated distribution packages

## License

ISC License - See the LICENSE file for details

## Contact

Emmanuel Sibanda - emmanuel@emmanuelsibanda.com