package networkcollector

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"runtime"
)

type LocalConfig struct {
	ServerURL      string `json:"server_url"`
	CollectorToken string `json:"collector_token"`
	PollSeconds    int    `json:"poll_seconds"`
	Concurrency    int    `json:"concurrency"`
	TimeoutMillis  int    `json:"timeout_millis"`
	OUIFile        string `json:"oui_file,omitempty"`
}

func DefaultConfigPath() string {
	if runtime.GOOS == "windows" {
		base := os.Getenv("ProgramData")
		if base == "" {
			base = `C:\ProgramData`
		}
		return filepath.Join(base, "TICControl", "network-collector.json")
	}
	return "/etc/tic-control/network-collector.json"
}

func LoadConfig(path string) (*LocalConfig, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var cfg LocalConfig
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}
	if cfg.ServerURL == "" || cfg.CollectorToken == "" {
		return nil, errors.New("server_url y collector_token son obligatorios")
	}
	if cfg.PollSeconds <= 0 {
		cfg.PollSeconds = 30
	}
	if cfg.Concurrency <= 0 {
		cfg.Concurrency = 64
	}
	if cfg.Concurrency > 256 {
		cfg.Concurrency = 256
	}
	if cfg.TimeoutMillis <= 0 {
		cfg.TimeoutMillis = 800
	}
	return &cfg, nil
}

func SaveConfig(path string, cfg *LocalConfig) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o600)
}
