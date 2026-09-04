package config

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"runtime"
)

type File struct {
	ServerURL     string `json:"server_url"`
	DeviceID      string `json:"device_id"`
	AgentToken    string `json:"agent_token"`
	HMACSecret    string `json:"hmac_secret"`
	HeartbeatSecs int    `json:"heartbeat_seconds"`
	AgentVersion  string `json:"agent_version"`
}

func DefaultPath() string {
	if runtime.GOOS == "windows" {
		base := os.Getenv("ProgramData")
		if base == "" {
			base = `C:\ProgramData`
		}
		return filepath.Join(base, "TICControl", "agent.json")
	}
	return "/etc/tic-control/agent.json"
}

func StateDir(cfgPath string) string {
	return filepath.Join(filepath.Dir(cfgPath), "state")
}

func Load(path string) (*File, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var cfg File
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}
	if cfg.ServerURL == "" || cfg.AgentToken == "" {
		return nil, errors.New("configuración incompleta")
	}
	if cfg.HeartbeatSecs <= 0 {
		cfg.HeartbeatSecs = 60
	}
	return &cfg, nil
}

func Save(path string, cfg *File) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o600)
}
