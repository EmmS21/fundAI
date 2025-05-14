# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path
# import site # Typically not needed unless you are manipulating Python's site packages paths

# --- Dynamic Library Discovery for llama_cpp ---
# This section dynamically finds shared libraries (.so, .dylib, .dll)
# within the installed llama_cpp package. This is more robust than hardcoding paths.
llama_cpp_libs_to_bundle = []
try:
    import llama_cpp
    llama_cpp_dir = os.path.dirname(llama_cpp.__file__)
    # Add all shared libraries in the llama_cpp package directory and its subdirectories (like llama_cpp/lib)
    for root, _, files in os.walk(llama_cpp_dir):
        for file in files:
            if file.endswith(('.so', '.dylib', '.dll')):
                lib_path = os.path.join(root, file)
                # The second element of the tuple is the destination directory within the bundle.
                # Placing them in a 'llama_cpp' subdirectory inside the bundle is a common practice.
                destination_in_bundle = os.path.join('llama_cpp', os.path.relpath(root, llama_cpp_dir), file)
                if destination_in_bundle.startswith('llama_cpp/./'): # Clean up path if relpath returns './'
                    destination_in_bundle = destination_in_bundle.replace('llama_cpp/./', 'llama_cpp/', 1)

                llama_cpp_libs_to_bundle.append((lib_path, os.path.dirname(destination_in_bundle)))
    if llama_cpp_libs_to_bundle:
        print(f"Found and will bundle llama_cpp libraries: {llama_cpp_libs_to_bundle}")
    else:
        print("Warning: No llama_cpp libraries found to bundle automatically. Ensure llama_cpp is correctly installed.")
except (ImportError, FileNotFoundError) as e:
    print(f"Warning: Could not find llama_cpp or its libraries: {e}. Manual inclusion might be needed if runtime errors occur.")
    llama_cpp_libs_to_bundle = []

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


a = Analysis(
    ['src/main.py'],
    pathex=[os.path.abspath('.')], # Adds current directory to PyInstaller's search path
    binaries=llama_cpp_libs_to_bundle, # Use dynamically discovered llama_cpp libraries
    datas=[ # Data files to be bundled with the application
        ('src/assets', 'src/assets'),      # All assets will be in 'src/assets' in the bundle
        ('src/config', 'src/config'),      # Configuration files
        ('src/core', 'src/core'),          # Core logic modules (if they contain data)
        ('src/data', 'src/data'),          # Data-related modules/files
        ('src/ui', 'src/ui'),              # UI definition files (e.g., .ui files if any)
        ('src/utils', 'src/utils'),        # Utility modules (if they contain data)
        # The GGUF model is NOT bundled, so model_data is not added here.
    ],
    hiddenimports=[ # List of modules that PyInstaller might miss
        'sqlalchemy.sql.default_comparator',
        'sqlalchemy.ext.declarative',
        'src.data.database.models',
        'src.utils.db',
        'src.core.services',
        'llama_cpp', # Ensures llama_cpp modules are included
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [], # Additional scripts, usually empty
    exclude_binaries=True, # Binaries are handled by COLLECT and a.binaries
    name='Examiner',       # The name of the executable
    debug=True,            # Enable debug mode (more verbose output)
    bootloader_ignore_signals=False,
    strip=False,           # Do not strip symbols (can help with debugging)
    upx=True,              # Use UPX to compress the executable (if available)
    console=True,          # True: shows a console window (good for CLI apps or debugging GUI apps)
                           # False: hides console (typical for GUI apps in release)
    icon=exe_icon          # Icon for the executable (mainly for Windows and Linux)
)

coll = COLLECT( # Gathers all files for the application directory
    exe,
    a.binaries,  # Bundled binary files (like llama_cpp libs)
    a.zipfiles,  # Zipped dependencies
    a.datas,     # Data files
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Examiner' # Name of the output folder in 'dist'
)

# --- macOS .app Bundle Configuration ---
# This section is specific to macOS builds.
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name='Examiner.app', # Name of the .app bundle
        icon=app_icon_main,  # Path to the .icns file (e.g., src/assets/examiner.icns)
        bundle_identifier='com.fundai.examiner', # Unique identifier for the app
        info_plist={ # Additional entries for the Info.plist file
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '1.0.0', # User-visible version string
            'CFBundleVersion': '1.0',          # Build version number
            # 'LSMinimumSystemVersion': '10.15', # Example: specify minimum macOS version
        }
    )