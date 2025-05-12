# The Examiner - Educational Assessment Platform

## Overview
The Examiner is a desktop application built with Python and PySide6, designed to provide educational assessments and testing capabilities. The application features offline functionality with online sync capabilities, user profile management, and a comprehensive logging system.

## Technical Stack
- **Frontend**: PySide6 (Qt for Python)
- **Backend**: Python 3.x
- **Database**: 
  - Local: SQLite (student_profile.db)
  - Cloud: Supabase
- **Additional Services**:
  - MongoDB for data caching
  - Firebase integration
  - Network monitoring and sync services

## Installation

### System Requirements
- Linux-based operating system
- Python 3.8 or higher
- Internet connection (for initial setup and syncing)

### Installation Methods

#### 1. AppImage Installation (Recommended)
1. Download the AppImage from the app store (Supabase)
2. Make the AppImage executable:
   ```bash
   chmod +x TheExaminer.AppImage
   ```
3. Double-click to run or execute from terminal:
   ```bash
   ./TheExaminer.AppImage
   ```

#### 2. Package Manager Installation (Coming Soon)
Support for popular Linux package managers (apt, snap, flatpak) will be available in future releases.

### Dependencies
The installer automatically handles the following dependencies:
- PySide6
- SQLAlchemy
- supabase-py
- pymongo
- firebase-admin
- requests
- python-dotenv

## Architecture

### Core Components
1. **Main Application (main.py)**
   - Application entry point
   - Window management
   - User session handling

2. **Application Services (app.py)**
   - Service initialization
   - Core functionality setup
   - Background services management

3. **Data Management**
   - Local SQLite database
   - Cloud sync with Supabase
   - Caching system with MongoDB

4. **Network Services**
   - Network monitoring
   - Offline/Online state management
   - Data synchronization

### Logging System
The application maintains comprehensive logs for debugging and monitoring:

- Location: `~/.local/share/TheExaminer/logs/`
- Log rotation: Daily basis
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Sync capability: Logs are stored locally and synced when online

## Development

### Building from Source
1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Build the AppImage:
   ```bash
   ./build_appimage.sh
   ```

### Packaging Process
The application is packaged using PyInstaller and AppImage:

1. **PyInstaller Configuration**
   ```python
   # pyinstaller.spec
   block_cipher = None
   a = Analysis(['src/main.py'],
                pathex=['/path/to/project'],
                binaries=[],
                datas=[('src/resources', 'resources')],
                hiddenimports=['PySide6'],
                hookspath=[],
                runtime_hooks=[],
                excludes=[],
                win_no_prefer_redirects=False,
                win_private_assemblies=False,
                cipher=block_cipher,
                noarchive=False)
   ```

2. **AppImage Creation**
   - Uses `linuxdeploy` and `linuxdeploy-plugin-qt`
   - Includes all necessary dependencies
   - Creates a self-contained executable

### Distribution
The application is distributed through Supabase:
1. AppImage is uploaded to Supabase storage
2. App store entry is updated with new version information
3. Users receive update notifications
4. Automatic updates are handled through the app

## Troubleshooting

### Log Analysis
Logs are stored in:
```bash
~/.local/share/TheExaminer/logs/examiner.log
```

Common log patterns:
- Network connectivity issues
- Database synchronization errors
- Service initialization failures

### Common Issues
1. **Database Sync Failures**
   - Check network connectivity
   - Verify Supabase credentials
   - Review sync service logs

2. **Missing Dependencies**
   - Run the repair tool: `./TheExaminer.AppImage --repair`
   - Check system requirements

3. **Performance Issues**
   - Clear cache: `./TheExaminer.AppImage --clear-cache`
   - Check available disk space
   - Monitor resource usage

## Security

### Data Protection
- Local data encryption
- Secure cloud sync
- Protected user credentials

### Updates
- Signed AppImage updates
- Automatic security patches
- Dependency vulnerability checking

## Support
- GitHub Issues: [Link to Issues]
- Email Support: [Support Email]
- Documentation: [Link to Docs]

## License
[License Information]
