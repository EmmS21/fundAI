# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import site
from pathlib import Path

# Safer approach to find llama_cpp library files
llama_cpp_libs = []
try:
    import llama_cpp
    llama_cpp_dir = os.path.dirname(llama_cpp.__file__)
    # Add all shared libraries in the llama_cpp directory
    for file in os.listdir(llama_cpp_dir):
        if file.endswith('.so') or file.endswith('.dylib') or file.endswith('.dll'):
            lib_path = os.path.join(llama_cpp_dir, file)
            llama_cpp_libs.append((lib_path, 'llama_cpp'))
    print(f"Found llama_cpp libraries: {llama_cpp_libs}")
except (ImportError, FileNotFoundError) as e:
    print(f"Warning: Could not find llama_cpp libraries: {e}")
    llama_cpp_libs = []

# Try to find the model file
MODEL_FILENAME = "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"
model_path = os.path.expanduser(f"~/Documents/models/llama/{MODEL_FILENAME}")
model_data = []
if os.path.isfile(model_path):
    model_data = [(model_path, 'models')]
    print(f"Found model file: {model_path}")
else:
    print(f"Warning: Model file not found at {model_path}")

llama_libs = [
    ('venv/lib/python3.13/site-packages/lib/libllama.dylib', '.'),
    ('venv/lib/python3.13/site-packages/llama_cpp/lib/libllava.dylib', 'llama_cpp/lib'),
    ('venv/lib/python3.13/site-packages/llama_cpp/lib/libggml.dylib', 'llama_cpp/lib'),
    ('venv/lib/python3.13/site-packages/llama_cpp/lib/libggml-base.dylib', 'llama_cpp/lib'),
    ('venv/lib/python3.13/site-packages/llama_cpp/lib/libggml-blas.dylib', 'llama_cpp/lib'),
    ('venv/lib/python3.13/site-packages/llama_cpp/lib/libllama.dylib', 'llama_cpp/lib'),
    ('venv/lib/python3.13/site-packages/llama_cpp/lib/libggml-cpu.dylib', 'llama_cpp/lib'),
    ('venv/lib/python3.13/site-packages/llama_cpp/lib/libggml-metal.dylib', 'llama_cpp/lib'),
]

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[os.path.abspath('.')],
    binaries=llama_libs,  
    datas=[
        ('src/assets', 'src/assets'),
        ('src/config', 'src/config'),
        ('src/core', 'src/core'),
        ('src/data', 'src/data'),
        ('src/ui', 'src/ui'),
        ('src/utils', 'src/utils'),
    ] + model_data,  
    hiddenimports=[
        'sqlalchemy.sql.default_comparator',
        'sqlalchemy.ext.declarative',
        'src.data.database.models',
        'src.utils.db',
        'src.core.services',
        'llama_cpp',
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
    [],
    exclude_binaries=True,
    name='Examiner',
    debug=True,  # Enable debug mode
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Enable console for debugging
    icon='src/assets/examiner.jpg'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Examiner'
)

app = BUNDLE(
    coll,
    name='Examiner.app',
    icon='src/assets/examiner.jpg',
    bundle_identifier='com.fundai.examiner',
    info_plist={
        'NSHighResolutionCapable': 'True'
    }
)
