package config

import (
	"os"
	"strings"
)

type Environment string

const (
	Development Environment = "development"
	Production  Environment = "production"
)

type Config struct {
	Environment   Environment
	FundaVaultURL string
}

// GetConfig returns configuration based on the environment
func GetConfig() *Config {
	env := getEnvironment()

	config := &Config{
		Environment:   env,
		FundaVaultURL: getFundaVaultURL(env),
	}

	return config
}

func getEnvironment() Environment {
	// Render sets this environment variable
	if os.Getenv("RENDER") != "" {
		return Production
	}
	return Development
}

func getFundaVaultURL(env Environment) string {
	// First check if explicitly set in environment
	if url := os.Getenv("FUNDAVAULT_URL"); url != "" {
		return strings.TrimSuffix(url, "/")
	}

	// Otherwise use default based on environment
	switch env {
	case Production:
		return "https://fundai.onrender.com"
	default:
		return "http://localhost:8000" // Default local FundaVault port
	}
}
