package auth

import (
	"FundAIHub/internal/config"
	"encoding/json"
	"fmt"
	"net/http"
)

type FundaVaultClient struct {
	config *config.Config
	client *http.Client
}

type TokenVerifyResponse struct {
	Valid   bool `json:"valid"`
	Payload struct {
		HardwareID      string `json:"hardware_id,omitempty"`
		UserID          string `json:"user_id,omitempty"`
		IsAdmin         bool   `json:"is_admin,omitempty"`
		SubscriptionEnd string `json:"subscription_end,omitempty"`
	} `json:"payload"`
}

func NewFundaVaultClient(cfg *config.Config) *FundaVaultClient {
	return &FundaVaultClient{
		config: cfg,
		client: &http.Client{},
	}
}

func (f *FundaVaultClient) VerifyToken(token string, hardwareID string) (*TokenVerifyResponse, error) {
	endpoint := fmt.Sprintf("%s/api/v1/devices/%s/verify",
		f.config.FundaVaultURL,
		hardwareID,
	)

	req, err := http.NewRequest("GET", endpoint, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}

	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", token))

	resp, err := f.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("verify token: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("invalid token: status %d", resp.StatusCode)
	}

	var result TokenVerifyResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}

	return &result, nil
}
