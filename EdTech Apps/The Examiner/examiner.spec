# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path
# import site # Typically not needed unless you are manipulating Python's site packages paths

# --- Create pyi_rth_qt6.py runtime hook FIRST ---
# This hook will be created in the same directory as the .spec file
# It helps the bundled application find its own Qt plugins.
# Moved this to the TOP of the spec file to ensure it exists before Analysis.
hook_content = """
import os
import sys

# Set QT_PLUGIN_PATH to point to the bundled Qt plugins
# This is crucial for PySide6 to find its platform plugins, etc.
if sys.platform.startswith('linux') or sys.platform == 'darwin': # Applicable for both Linux and macOS
    if hasattr(sys, '_MEIPASS'):
        # Default base for PySide6 bundled files
        pyside_base = os.path.join(sys._MEIPASS, 'PySide6')
        
        # Main plugin path
        qt_plugin_path = os.path.join(pyside_base, 'Qt', 'plugins')
        # Alternative if plugins are directly under PySide6 (older PyInstaller/PySide6 versions)
        if not os.path.isdir(os.path.join(qt_plugin_path, 'platforms')):
             plugin_path_alt = os.path.join(pyside_base, 'plugins')
             if os.path.isdir(os.path.join(plugin_path_alt, 'platforms')):
                 qt_plugin_path = plugin_path_alt

        print(f"INFO: [pyi_rth_qt6] Effective Qt Plugin Path: {qt_plugin_path}")
        os.environ['QT_PLUGIN_PATH'] = qt_plugin_path
        
        qpa_plugin_path = os.path.join(qt_plugin_path, 'platforms')
        print(f"INFO: [pyi_rth_qt6] Effective QPA Platform Plugin Path: {qpa_plugin_path}")
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qpa_plugin_path

        # Also add to LD_LIBRARY_PATH as an additional measure for Linux
        if sys.platform.startswith('linux'):
            current_ld_path = os.environ.get('LD_LIBRARY_PATH', '')
            paths_to_add_to_ld = []

            # Add sys._MEIPASS first, as it's the root of the bundled app
            if sys._MEIPASS not in paths_to_add_to_ld:
                paths_to_add_to_ld.append(sys._MEIPASS)

            # Add PySide6 library path (e.g., _MEIPASS/PySide6)
            pyside_lib_path = os.path.join(sys._MEIPASS, 'PySide6') # Contains libPySide6.so.6.x etc.
            if os.path.isdir(pyside_lib_path) and pyside_lib_path not in paths_to_add_to_ld:
                 paths_to_add_to_ld.append(pyside_lib_path)

            # Add Qt plugin paths
            if os.path.isdir(qt_plugin_path) and qt_plugin_path not in paths_to_add_to_ld:
                 paths_to_add_to_ld.append(qt_plugin_path)
            if os.path.isdir(qpa_plugin_path) and qpa_plugin_path not in paths_to_add_to_ld:
                paths_to_add_to_ld.append(qpa_plugin_path)
            
            new_ld_path_components = paths_to_add_to_ld
            if current_ld_path: # Prepend our paths, then append existing ones
                new_ld_path_components.extend(current_ld_path.split(os.pathsep))
            
            # Remove duplicates while preserving order
            final_ld_path_components = []
            seen_paths = set()
            for path_component in new_ld_path_components:
                if path_component not in seen_paths:
                    final_ld_path_components.append(path_component)
                    seen_paths.add(path_component)
            
            os.environ['LD_LIBRARY_PATH'] = os.pathsep.join(final_ld_path_components)
            print(f"INFO: [pyi_rth_qt6] Updated LD_LIBRARY_PATH: {os.environ['LD_LIBRARY_PATH']}")

        # Debug: List available platform plugins if path exists
        if os.path.isdir(qpa_plugin_path):
            print(f"INFO: [pyi_rth_qt6] Available platform plugins in {qpa_plugin_path}: {os.listdir(qpa_plugin_path)}")
            # Further debug: check libqxcb.so dependencies if possible (requires ldd, not easy in hook)
            # For example, if 'libqxcb.so' in os.listdir(qpa_plugin_path):
            #    print(f"INFO: [pyi_rth_qt6] libqxcb.so found at {os.path.join(qpa_plugin_path, 'libqxcb.so')}")

        else:
            print(f"WARNING: [pyi_rth_qt6] QPA plugin path does NOT exist: {qpa_plugin_path}")
    else:
        # Development mode (running from source) - try to find system or venv PySide6 plugins
        try:
            import PySide6
            pyside6_dir = os.path.dirname(PySide6.__file__)
            dev_plugin_path = os.path.join(pyside6_dir, 'Qt', 'plugins')
            if not os.path.isdir(os.path.join(dev_plugin_path, 'platforms')):
                dev_plugin_path_alt = os.path.join(pyside6_dir, 'plugins')
                if os.path.isdir(os.path.join(dev_plugin_path_alt, 'platforms')):
                    dev_plugin_path = dev_plugin_path_alt
            
            if os.path.isdir(dev_plugin_path):
                # Only set if not already set, to avoid overriding Docker ENV vars during Linux build
                if 'QT_PLUGIN_PATH' not in os.environ:
                    os.environ['QT_PLUGIN_PATH'] = dev_plugin_path
                if 'QT_QPA_PLATFORM_PLUGIN_PATH' not in os.environ:
                    dev_qpa_plugin_path = os.path.join(dev_plugin_path, 'platforms')
                    if os.path.isdir(dev_qpa_plugin_path):
                        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = dev_qpa_plugin_path
        except ImportError:
            pass
"""
Path('pyi_rth_qt6.py').write_text(hook_content)
print("INFO: [spec] Created/Updated pyi_rth_qt6.py")

# --- Dynamic Library Discovery for llama_cpp ---
# This section dynamically finds shared libraries (.so, .dylib, .dll)
# within the installed llama_cpp package. This is more robust than hardcoding paths.
llama_cpp_libs_to_bundle = []
try:
    import llama_cpp
    import os
    
    # Debug output during build
    print(f"LLAMA-CPP DIR: {os.path.dirname(llama_cpp.__file__)}")
    
    llama_cpp_dir = os.path.dirname(llama_cpp.__file__)
    
    # Method 1: Search for all shared libraries
    for root, _, files in os.walk(llama_cpp_dir):
        for file_name in files:
            if file_name.endswith(('.so', '.dylib', '.dll')):
                lib_path = os.path.join(root, file_name)
                destination = os.path.join('llama_cpp_libs', os.path.relpath(root, llama_cpp_dir))
                print(f"Found library: {lib_path} -> {destination}")
                llama_cpp_libs_to_bundle.append((lib_path, destination))
    
    # Method 2: Check specific locations if method 1 fails
    if not llama_cpp_libs_to_bundle:
        # Check if the library is in the lib directory
        lib_dir = os.path.join(llama_cpp_dir, 'lib')
        if os.path.exists(lib_dir):
            print(f"Checking lib directory: {lib_dir}")
            for file_name in os.listdir(lib_dir):
                if file_name.endswith(('.so', '.dylib', '.dll')):
                    lib_path = os.path.join(lib_dir, file_name)
                    print(f"Found library in lib dir: {lib_path}")
                    llama_cpp_libs_to_bundle.append((lib_path, 'llama_cpp_libs'))
    
    # Method 3: Direct approach if methods 1 and 2 fail
    if not llama_cpp_libs_to_bundle:
        # Try to find libllama directly
        for lib_name in ['libllama.so', 'llama.dll', 'libllama.dylib']:
            potential_path = os.path.join(llama_cpp_dir, lib_name)
            if os.path.exists(potential_path):
                print(f"Found library directly: {potential_path}")
                llama_cpp_libs_to_bundle.append((potential_path, 'llama_cpp_libs'))
    
    # Final check and warning
    if not llama_cpp_libs_to_bundle:
        print("WARNING: No llama_cpp libraries found to bundle!")
        
except ImportError:
    print("WARNING: llama_cpp package not found. Cannot bundle its libraries.")
except Exception as e:
    print(f"WARNING: An error occurred during llama_cpp library discovery: {e}")

# --- Model File Handling (NOT BUNDLED) ---
# The GGUF model is assumed to be pre-installed on the target machine.
# This section is only for a developer-time check/warning during the build.
MODEL_FILENAME = "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf" # The expected model filename
EXPECTED_MODEL_PATH = os.path.expanduser(f"~/Documents/models/llama/{MODEL_FILENAME}")

if not os.path.isfile(EXPECTED_MODEL_PATH):
    print(f"Warning: Pre-installed model file not found at expected location: {EXPECTED_MODEL_PATH}")
    print("The application expects this model to be present on the user's system.")
# model_data = [] # Explicitly ensuring model_data is not used for bundling

block_cipher = None

# --- Platform-Specific Icon Paths ---
# Defines which icon file to use based on the operating system.
# For macOS, .icns is preferred for the .app bundle.
# For Linux (and potentially Windows EXE), .jpg is used.
# The build.sh script is responsible for creating examiner.icns on macOS.
if sys.platform == "darwin":
    app_icon_main = 'src/assets/examiner.icns' # For .app bundle
    exe_icon = None # .app bundle icon is primary; EXE's icon often not visible
else:
    app_icon_main = 'src/assets/examiner.jpg' # For Linux executable
    exe_icon = app_icon_main

# --- Data Files ---
datas = [
    ('src/assets', 'src/assets'),
    ('src/config', 'src/config'),
    # Add other non-Python data directories if they exist and are needed directly
    # e.g., ('src/ui_files', 'src/ui_files') if you have .ui files there
]
# If PySide6 needs specific data files like translations, uncomment and adapt:
# from PyInstaller.utils.hooks import collect_data_files
# datas += collect_data_files('PySide6', subdir='Qt/translations', destdir='PySide6/Qt/translations', include_py_files=False)
# datas += collect_data_files('PySide6', subdir='Qt/resources', destdir='PySide6/Qt/resources', include_py_files=False)

# --- Hidden Imports ---
hiddenimports = [
    'sqlalchemy.sql.default_comparator',
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.ext.declarative',
    'src.data.database.models',
    'src.utils.db',
    'src.core.services',
    'llama_cpp',
    'llama_cpp.llama',
    'PIL._tkinter_finder',
    'PySide6.QtSvg',
    'PySide6.QtPrintSupport',
    # Add other Qt modules your app uses if PyInstaller misses them
    'sentry_sdk.integrations', # Ensure parent package is processed
    'sentry_sdk.integrations.stdlib',
    'sentry_sdk.integrations.logging', 
    'sentry_sdk.integrations.atexit',
    'sentry_sdk.integrations.excepthook',
    'sentry_sdk.integrations.dedupe',
    'sentry_sdk.integrations.threading',
]

# Add this to your examiner.spec file inside the Analysis section
qt_plugins = [
    'platforms/libqxcb.so',
    'platforms/libqwayland.so',
    'platformthemes/libqgtk3.so',
    'imageformats/libqjpeg.so', 
    'imageformats/libqsvg.so',
]

binaries = []
for plugin in qt_plugins:
    if hasattr(sys, '_MEIPASS'):
        binaries.append((os.path.join(sys._MEIPASS, 'PySide6', 'Qt', 'plugins', plugin), os.path.join('PySide6', 'Qt', 'plugins', os.path.dirname(plugin))))
    else:
        try:
            import PySide6
            pyside_dir = os.path.dirname(PySide6.__file__)
            plugin_path = os.path.join(pyside_dir, 'Qt', 'plugins', plugin)
            if os.path.exists(plugin_path):
                binaries.append((plugin_path, os.path.join('PySide6', 'Qt', 'plugins', os.path.dirname(plugin))))
        except ImportError:
            pass

a = Analysis(
    ['src/main.py'],
    pathex=[os.path.abspath('.')],
    binaries=llama_cpp_libs_to_bundle + binaries,  # Add binaries here
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[
        'pyi_rth_qt6.py' 
    ],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# For macOS .app, BUNDLE is the primary target. EXE is intermediate.
# For Linux, EXE and COLLECT are primary.
if sys.platform == "darwin":
    # EXE for macOS is an intermediate step for BUNDLE
    exe = EXE(pyz, a.scripts, [], name='Examiner', debug=True, strip=False, upx=False, console=False, icon=None) # console=False for .app
    app = BUNDLE(
        exe, # Pass the EXE object directly
        name='Examiner.app',
        icon=app_icon_main, # This should be src/assets/examiner.icns
        bundle_identifier='com.fundai.examiner',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0.1',
            'LSMinimumSystemVersion': '11.0', # Example, adjust as needed
            'NSPrincipalClass': 'NSApplication',
            'NSMainNibFile': 'MainMenu',
            'CFBundlePackageType': 'APPL'
        },
        # PyInstaller will collect binaries and datas from Analysis 'a' for BUNDLE
        binaries=a.binaries, # Pass binaries from Analysis
        datas=a.datas,       # Pass datas from Analysis
        zipfiles=a.zipfiles
    )
else: # For Linux build (this part will be executed inside Docker by build.sh)
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Examiner',
        debug=True,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=True, 
        icon=exe_icon
    )
    # For Linux, we need COLLECT to create the one-dir bundle
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name='Examiner' # Output folder in dist/
    )