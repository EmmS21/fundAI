import os
import re
import uuid
import platform
import subprocess
from typing import Optional, Tuple

class HardwareIdentifier:
    @staticmethod
    def get_os_type() -> str:
        """Get current operating system type"""
        system = platform.system().lower()
        if system == 'darwin':
            return 'macos'
        return system

    @staticmethod
    def _get_windows_id() -> Optional[str]:
        """Get Windows MachineGUID without admin rights"""
        try:
            # Only import wmi on Windows
            if platform.system().lower() == 'windows':
                import wmi
                c = wmi.WMI()
                for item in c.Win32_ComputerSystemProduct():
                    if item.UUID:
                        return item.UUID
        except ImportError:
            pass  # Handle systems without wmi module
        
        # Fallback to using environment variables and system info
        system_info = [
            platform.node(),  # Computer network name
            platform.machine(),  # Machine type
            os.getenv('USERNAME', ''),
            os.getenv('COMPUTERNAME', ''),
            platform.processor()  # Processor info
        ]
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, '-'.join(system_info)))

    @staticmethod
    def _get_macos_id() -> Optional[str]:
        """Get MacOS hardware UUID without admin rights"""
        try:
            # Try using IOKit framework
            output = subprocess.check_output(['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'])
            uuid_match = re.search(b'IOPlatformUUID"= "([^"]+)"', output)
            if uuid_match:
                return uuid_match.group(1).decode('utf-8')
        except:
            pass

        # Fallback method
        system_info = [
            platform.node(),
            platform.machine(),
            os.getenv('USER', ''),
            platform.processor()
        ]
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, '-'.join(system_info)))

    @staticmethod
    def _get_linux_id() -> Optional[str]:
        """Get Linux machine ID without admin rights"""
        # Try reading machine-id files
        machine_id_files = [
            '/etc/machine-id',
            '/var/lib/dbus/machine-id'
        ]
        
        for file_path in machine_id_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        return content
            except:
                continue

        # Fallback method
        system_info = [
            platform.node(),
            platform.machine(),
            os.getenv('USER', ''),
            platform.processor()
        ]
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, '-'.join(system_info)))

    @classmethod
    def get_hardware_id(cls) -> Tuple[str, str, str]:
        """
        Get hardware identifier for current system
        Returns: (os_type, raw_identifier, normalized_identifier)
        """
        os_type = cls.get_os_type()
        
        # Get raw identifier based on OS
        if os_type == 'windows':
            raw_id = cls._get_windows_id()
        elif os_type == 'macos':
            raw_id = cls._get_macos_id()
        elif os_type == 'linux':
            raw_id = cls._get_linux_id()
        else:
            raise ValueError(f"Unsupported operating system: {os_type}")

        if not raw_id:
            # Final fallback - generate UUID from system info
            raw_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, platform.node()))

        # Normalize to UUID format
        normalized_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, raw_id))
        
        return os_type, raw_id, normalized_id
