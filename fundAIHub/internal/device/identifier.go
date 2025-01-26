package device

import (
	"bufio"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"strings"
)

type DeviceIdentifier interface {
	GetHardwareID() (string, error)
}

type SystemIdentifier struct{}

func NewSystemIdentifier() *SystemIdentifier {
	return &SystemIdentifier{}
}

func (s *SystemIdentifier) GetHardwareID() (string, error) {
	var id string
	var err error

	switch runtime.GOOS {
	case "darwin":
		id, err = getMacHardwareUUID()
	case "windows":
		id, err = getWindowsMachineGUID()
	case "linux":
		id, err = getLinuxMachineID()
	default:
		return "", fmt.Errorf("unsupported operating system: %s", runtime.GOOS)
	}

	if err != nil {
		return "", err
	}

	// Normalize the ID with SHA-256
	hash := sha256.Sum256([]byte(id))
	return hex.EncodeToString(hash[:]), nil
}

func getMacHardwareUUID() (string, error) {
	cmd := exec.Command("system_profiler", "SPHardwareDataType")
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to get Mac hardware UUID: %w", err)
	}

	lines := strings.Split(string(output), "\n")
	for _, line := range lines {
		if strings.Contains(line, "Hardware UUID") {
			parts := strings.Split(line, ":")
			if len(parts) == 2 {
				return strings.TrimSpace(parts[1]), nil
			}
		}
	}
	return "", fmt.Errorf("hardware UUID not found in system_profiler output")
}

func getWindowsMachineGUID() (string, error) {
	cmd := exec.Command("reg", "query", "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Cryptography", "/v", "MachineGuid")
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to get Windows machine GUID: %w", err)
	}

	lines := strings.Split(string(output), "\n")
	for _, line := range lines {
		if strings.Contains(line, "MachineGuid") {
			parts := strings.Fields(line)
			if len(parts) >= 3 {
				return strings.TrimSpace(parts[len(parts)-1]), nil
			}
		}
	}
	return "", fmt.Errorf("machine GUID not found in registry output")
}

func getLinuxMachineID() (string, error) {
	// Try /etc/machine-id first
	id, err := readMachineID("/etc/machine-id")
	if err == nil {
		return id, nil
	}

	// Fall back to /var/lib/dbus/machine-id
	id, err = readMachineID("/var/lib/dbus/machine-id")
	if err == nil {
		return id, nil
	}

	return "", fmt.Errorf("failed to read machine ID from both locations")
}

func readMachineID(path string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	if scanner.Scan() {
		id := strings.TrimSpace(scanner.Text())
		if len(id) > 0 {
			return id, nil
		}
	}

	if err := scanner.Err(); err != nil {
		return "", err
	}

	return "", fmt.Errorf("empty or invalid machine ID in %s", path)
}
