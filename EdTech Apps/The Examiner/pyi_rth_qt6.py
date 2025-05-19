
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
