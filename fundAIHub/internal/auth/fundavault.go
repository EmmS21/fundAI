package auth

import (
	"FundAIHub/internal/config"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
)

type FundaVaultClient struct {
	config *config.Config
	client *http.Client
}

type DeviceVerifyResponse struct {
	Authenticated   bool   `json:"authenticated"`
	UserID          int64  `json:"user_id"`
	Email           string `json:"email"`
	IsAdmin         bool   `json:"is_admin"`
	SubscriptionEnd string `json:"subscription_end,omitempty"`
}

type DeviceVerifyRequest struct {
	HardwareID string `json:"hardware_id"`
}

func NewFundaVaultClient(cfg *config.Config) *FundaVaultClient {
	return &FundaVaultClient{
		config: cfg,
		client: &http.Client{},
	}
}

func (f *FundaVaultClient) VerifyDevice(hardwareID string) (*DeviceVerifyResponse, int, error) {
	endpoint := fmt.Sprintf("%s/api/v1/auth/device", f.config.FundaVaultURL)

	requestPayload := DeviceVerifyRequest{HardwareID: hardwareID}
	requestBody, err := json.Marshal(requestPayload)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to marshal request body: %w", err)
	}

	req, err := http.NewRequestWithContext(context.Background(), "POST", endpoint, bytes.NewBuffer(requestBody))
	if err != nil {
		return nil, 0, fmt.Errorf("failed to create verify device request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Calling-Service", "FundAIHub")

	log.Printf("[FundaVaultClient] Sending verification request to %s for hardware ID: %s", endpoint, hardwareID)

	resp, err := f.client.Do(req)
	if err != nil {
		log.Printf("[FundaVaultClient] Error sending request to FundaVault: %v", err)
		return nil, 0, fmt.Errorf("failed to send request to FundaVault: %w", err)
	}
	defer resp.Body.Close()

	log.Printf("[FundaVaultClient] Received status code %d from FundaVault", resp.StatusCode)

	responseBodyBytes, readErr := io.ReadAll(resp.Body)
	if readErr != nil {
		log.Printf("[FundaVaultClient] Error reading response body: %v", readErr)
	} else {
		log.Printf("[FundaVaultClient] Received response body: %s", string(responseBodyBytes))
	}

	if resp.StatusCode != http.StatusOK {
		return nil, resp.StatusCode, fmt.Errorf("fundavault verification failed with status %d", resp.StatusCode)
	}

	var result DeviceVerifyResponse
	if err := json.Unmarshal(responseBodyBytes, &result); err != nil {
		log.Printf("[FundaVaultClient] Error decoding successful response body: %v", err)
		return nil, http.StatusInternalServerError, fmt.Errorf("failed to decode successful fundavault response: %w", err)
	}

	return &result, resp.StatusCode, nil
}
