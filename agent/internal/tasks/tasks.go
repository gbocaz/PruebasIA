package tasks

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/gbocaz/tic-control-agent/internal/client"
	"github.com/gbocaz/tic-control-agent/internal/collect"
	"github.com/gbocaz/tic-control-agent/internal/config"
)

type Task struct {
	TaskID    string          `json:"task_id"`
	DeviceID  string          `json:"device_id"`
	Type      string          `json:"type"`
	Params    json.RawMessage `json:"params"`
	Signature string          `json:"signature"`
	ExpiresAt string          `json:"expires_at"`
}

func validHMAC(secret, taskID, deviceID, typ, expires, signature string) bool {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(taskID + "|" + deviceID + "|" + typ + "|" + expires))
	return hmac.Equal([]byte(signature), []byte(hex.EncodeToString(mac.Sum(nil))))
}

func sha256File(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:]), nil
}

func Run(cli *client.Client, cfg *config.File, workDir string) {
	data, err := cli.Get("/agent/tasks")
	if err != nil {
		return
	}
	var tasks []Task
	if err := json.Unmarshal(data, &tasks); err != nil {
		return
	}
	doneFile := filepath.Join(workDir, "done_tasks.json")
	done := loadDone(doneFile)
	for _, t := range tasks {
		if done[t.TaskID] {
			continue
		}
		if t.ExpiresAt != "" {
			exp, err := time.Parse(time.RFC3339Nano, t.ExpiresAt)
			if err != nil {
				exp, err = time.Parse(time.RFC3339, t.ExpiresAt)
			}
			if err == nil && time.Now().After(exp) {
				continue
			}
		}
		if !validHMAC(cfg.HMACSecret, t.TaskID, t.DeviceID, t.Type, t.ExpiresAt, t.Signature) {
			_, _ = cli.Post("/agent/task-result", map[string]any{
				"task_id": t.TaskID, "success": false, "message": "firma inválida",
			}, true)
			continue
		}
		ok, msg := execute(cli, cfg, workDir, t)
		_, _ = cli.Post("/agent/task-result", map[string]any{
			"task_id": t.TaskID, "success": ok, "message": msg,
		}, true)
		done[t.TaskID] = true
		saveDone(doneFile, done)
	}
}

func execute(cli *client.Client, cfg *config.File, workDir string, t Task) (bool, string) {
	switch t.Type {
	case "collect_inventory":
		sw := collect.InstalledSoftware()
		_, err := cli.Post("/agent/inventory", map[string]any{"software": sw}, true)
		if err != nil {
			return false, err.Error()
		}
		return true, fmt.Sprintf("%d programas", len(sw))
	case "install_package":
		return installPackage(cli, workDir, t.Params)
	case "restart_agent":
		go func() {
			time.Sleep(2 * time.Second)
			os.Exit(0)
		}()
		return true, "reinicio programado"
	case "update_agent":
		return false, "actualización de agente pendiente de binario firmado"
	default:
		return false, "tipo de tarea no soportado"
	}
}

func installPackage(cli *client.Client, workDir string, params json.RawMessage) (bool, string) {
	var p struct {
		PackageID      string `json:"package_id"`
		SHA256         string `json:"sha256"`
		InstallCommand string `json:"install_command"`
		Filename       string `json:"filename"`
	}
	if err := json.Unmarshal(params, &p); err != nil {
		return false, "parámetros inválidos"
	}
	if p.PackageID == "" || p.SHA256 == "" || p.InstallCommand == "" {
		return false, "paquete incompleto"
	}
	dir := filepath.Join(workDir, "packages")
	_ = os.MkdirAll(dir, 0o700)
	dest := filepath.Join(dir, filepath.Base(p.Filename))
	if err := cli.Download("/agent/packages/"+p.PackageID+"/download", dest); err != nil {
		return false, "descarga: " + err.Error()
	}
	sum, err := sha256File(dest)
	if err != nil || !strings.EqualFold(sum, p.SHA256) {
		_ = os.Remove(dest)
		return false, "hash SHA-256 no coincide"
	}
	cmdLine := strings.ReplaceAll(p.InstallCommand, "{file}", dest)
	cmdLine = strings.ReplaceAll(cmdLine, "{dir}", dir)
	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		cmd = exec.Command("cmd", "/C", cmdLine)
	} else {
		cmd = exec.Command("bash", "-lc", cmdLine)
	}
	out, err := cmd.CombinedOutput()
	msg := strings.TrimSpace(string(out))
	if len(msg) > 500 {
		msg = msg[:500]
	}
	if err != nil {
		return false, err.Error() + " " + msg
	}
	return true, "instalado"
}

func loadDone(path string) map[string]bool {
	m := map[string]bool{}
	data, err := os.ReadFile(path)
	if err != nil {
		return m
	}
	_ = json.Unmarshal(data, &m)
	return m
}

func saveDone(path string, m map[string]bool) {
	data, _ := json.Marshal(m)
	_ = os.WriteFile(path, data, 0o600)
}
