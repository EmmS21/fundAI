import os
import sys
import ctypes
from pathlib import Path
import importlib.abc
import importlib.machinery
import importlib.util

# Store the original import
_original_import = __import__

def patch_llama_path():
    """Find and preload llama library before any imports of llama_cpp"""
    if not getattr(sys, 'frozen', False):
        return  # Only needed in PyInstaller bundle
        
    # This function isn't just about patching the path anymore
    # It actively loads the library and hooks the import system
        
    bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    print(f"Bundle directory: {bundle_dir}")
    
    # Find the llama library
    potential_paths = [
        os.path.join(bundle_dir, '_internal', 'llama_cpp_libs', 'libllama.so'),
        # Add fallback paths here if needed
    ]
    
    # Try to load any libraries we find
    loaded_lib = None
    lib_path = None
    
    for path in potential_paths:
        if os.path.exists(path):
            print(f"Found libllama.so at: {path}")
            try:
                loaded_lib = ctypes.CDLL(path)
                lib_path = path
                print(f"Successfully loaded libllama.so from: {path}")
                break
            except Exception as e:
                print(f"Failed to load from {path}: {e}")
    
    # If we couldn't find the library in expected locations, do a deeper search
    if loaded_lib is None:
        print("Searching for libllama.so in the entire bundle...")
        for root, _, files in os.walk(bundle_dir):
            for file in files:
                if file == 'libllama.so':
                    path = os.path.join(root, file)
                    try:
                        loaded_lib = ctypes.CDLL(path)
                        lib_path = path
                        print(f"Successfully loaded libllama.so from: {path}")
                        break
                    except Exception as e:
                        print(f"Failed to load from {path}: {e}")
            if loaded_lib:
                break
    
    if loaded_lib is None:
        print("ERROR: Could not find or load libllama.so")
        return
        
    # Set environment variables to help llama_cpp find the library
    lib_dir = os.path.dirname(lib_path)
    os.environ['LD_LIBRARY_PATH'] = f"{lib_dir}:{os.environ.get('LD_LIBRARY_PATH', '')}"
    os.environ['LLAMA_CPP_LIB'] = lib_path
    
    # Create a module finder that will inject our preloaded library
    class LlamaCppFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path, target=None):
            if fullname == 'llama_cpp' or fullname.startswith('llama_cpp.'):
                # Let normal import happen, but record that we need to patch the module
                return None
            return None
            
    # Install our meta path finder
    sys.meta_path.insert(0, LlamaCppFinder())
    
    # Patch __import__ to intercept llama_cpp imports
    def patched_import(name, *args, **kwargs):
        module = _original_import(name, *args, **kwargs)
        
        # Check if this is the llama_cpp module we care about
        if name == 'llama_cpp' and hasattr(module, 'llama_cpp') and hasattr(module.llama_cpp, '_load_shared_library'):
            print("Intercepted llama_cpp import! Patching _load_shared_library...")
            
            # Replace the library loading function
            original_load = module.llama_cpp._load_shared_library
            def patched_load(*args, **kwargs):
                print("Redirecting llama_cpp library loading to our preloaded library")
                return loaded_lib
                
            module.llama_cpp._load_shared_library = patched_load
            
            # Also ensure the _lib attribute is set if it exists
            if hasattr(module.llama_cpp, '_lib') and module.llama_cpp._lib is None:
                print("Setting llama_cpp._lib directly")
                module.llama_cpp._lib = loaded_lib
                
        return module
        
    # Replace the built-in __import__ function
    builtins.__import__ = patched_import
    
    print("llama_cpp import system patched")
