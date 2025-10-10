"""
PyInstaller runtime hook for Qt6/PySide6
Ensures Qt plugins are properly configured in the bundled application
"""

import os
import sys
from pathlib import Path

def setup_qt_plugins():
    """Configure Qt plugin paths for bundled application"""
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle
        bundle_dir = Path(sys._MEIPASS)
        
        # Set QT_PLUGIN_PATH for bundled Qt plugins
        qt_plugin_path = bundle_dir / 'PySide6' / 'Qt' / 'plugins'
        if qt_plugin_path.exists():
            os.environ['QT_PLUGIN_PATH'] = str(qt_plugin_path)
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(qt_plugin_path / 'platforms')
            print(f"[Qt Hook] Set QT_PLUGIN_PATH to: {qt_plugin_path}")
        
        # Alternative plugin location
        alt_plugin_path = bundle_dir / 'qt_plugins'
        if alt_plugin_path.exists():
            current_path = os.environ.get('QT_PLUGIN_PATH', '')
            if current_path:
                os.environ['QT_PLUGIN_PATH'] = f"{current_path}{os.pathsep}{alt_plugin_path}"
            else:
                os.environ['QT_PLUGIN_PATH'] = str(alt_plugin_path)
        
        # Set QT_QPA_PLATFORM if not already set
        if 'QT_QPA_PLATFORM' not in os.environ:
            # Use xcb for Linux, cocoa for macOS
            if sys.platform.startswith('linux'):
                os.environ['QT_QPA_PLATFORM'] = 'xcb'
            elif sys.platform == 'darwin':
                os.environ['QT_QPA_PLATFORM'] = 'cocoa'
        
        # Disable Qt logging for cleaner output
        os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.qpa.*=false'

# Execute the setup
setup_qt_plugins() 