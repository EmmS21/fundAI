# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for The Engineer AI Tutor
Creates a Linux executable bundle with all dependencies
"""

import sys
import os
from pathlib import Path

# Platform-specific configuration
if sys.platform == "darwin":
    # macOS configuration
    app_icon_main = 'assets/icons/engineer.png'
    exe_icon = None
else:
    # Linux configuration  
    app_icon_main = 'assets/icons/engineer.png'
    exe_icon = app_icon_main

# Find llama-cpp installation and bundle its libraries
llama_cpp_libs_to_bundle = []
try:
    import llama_cpp
    llama_cpp_dir = Path(llama_cpp.__file__).parent
    print(f"Found llama_cpp at: {llama_cpp_dir}")
    
    # Dynamic discovery of llama_cpp shared libraries
    for root, _, files in os.walk(llama_cpp_dir):
        for file_name in files:
            if file_name.endswith(('.so', '.dylib', '.dll')):
                lib_path = os.path.join(root, file_name)
                destination = os.path.join('llama_cpp_libs', os.path.relpath(root, llama_cpp_dir))
                llama_cpp_libs_to_bundle.append((lib_path, destination))
                print(f"Bundling llama_cpp library: {lib_path} -> {destination}")
except ImportError:
    print("llama-cpp-python not found, skipping library bundling")

# Define data files to include
datas = [
    ('assets', 'assets'),              # Icons and images
    ('src/config', 'src/config'),      # Configuration files
]

# Add llama-cpp libraries if found
datas.extend(llama_cpp_libs_to_bundle)

# Hidden imports that PyInstaller might miss
hiddenimports = [
    # SQLAlchemy and database
    'sqlalchemy.sql.default_comparator',
    'sqlalchemy.dialects.sqlite',
    'src.data.database.models',
    
    # AI libraries
    'llama_cpp', 
    'llama_cpp.llama',
    'groq',
    
    # PySide6 components
    'PySide6.QtSvg',
    'PySide6.QtPrintSupport',
    'PySide6.QtOpenGL',
    'PySide6.QtMultimedia',
    
    # Application modules
    'src.core.ai_manager',
    'src.core.database',
    'src.core.questions',
    'src.core.ai.marker',
    'src.core.ai.groq_client',
    'src.core.ai.project_generator',
    'src.core.ai.project_prompts',
    'src.core.ai.prompt_examples',
    'src.core.ai.logic_puzzles_prompts',
    'src.ui.main_window',
    'src.ui.dashboard_view',
    'src.ui.assessment_view',
    'src.ui.utils',
    'src.ui.views.dashboard_view',
    'src.ui.views.logic_puzzles_view',
    'src.ui.views.onboarding_view',
    'src.ui.views.project_wizard_view',
    'src.ui.views.simple_question_widget',
    'src.ui.views.welcome_view',
    'src.utils.hardware_identifier',
    'src.utils.network_utils',
    
    # Standard library modules that might be missed
    'sqlite3',
    'json',
    'pathlib',
    'typing',
    'asyncio',
    'concurrent.futures',
    
    # Third-party integrations
    'firebase_admin',
    'pymongo',
    'requests',
    'aiohttp',
]

# Exclude unnecessary modules to reduce size
excludes = [
    'tkinter',
    'matplotlib',
    'numpy',
    'scipy',
    'pandas',
    'jupyter',
    'IPython',
    'notebook',
    'tornado',
]

# Analysis step
a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=['hooks/pyi_rth_qt6.py'],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove duplicate entries
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

if sys.platform == "darwin":
    # macOS app bundle
    exe = EXE(pyz, a.scripts, [],
        exclude_binaries=True,
        name='The Engineer',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=app_icon_main
    )
    
    coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas,
        strip=False, upx=False,
        name='The Engineer'
    )
    
    app = BUNDLE(coll,
        name='The Engineer.app',
        icon=app_icon_main,
        bundle_identifier='com.fundai.engineer',
        info_plist={
            'CFBundleDisplayName': 'The Engineer',
            'CFBundleIdentifier': 'com.fundai.engineer',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,
        }
    )
else:
    # Linux executable
    exe = EXE(pyz, a.scripts, [], 
        exclude_binaries=True,
        name='Engineer',
        debug=True,
        console=True,
        icon=exe_icon
    )

    coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas,
        strip=False, upx=False,
        name='Engineer'  # Output folder in dist/
    ) 