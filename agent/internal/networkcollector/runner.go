package networkcollector

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/gbocaz/tic-control-agent/internal/backoff"
	"github.com/gbocaz/tic-control-agent/internal/client"
	"github.com/gbocaz/tic-control-agent/internal/queue"
)

const Version = "0.1.0"

func Run(configPath string) error {
	cfg, err := LoadConfig(configPath)
	if err != nil {
		return err
	}
	stateDir := configPath + ".state"
	q := queue.New(stateDir)
	api := client.New(cfg.ServerURL, cfg.CollectorToken, q)
	policy := backoff.Policy{}
	hostname, _ := os.Hostname()
	for {
		api.FlushQueue()
		if _, err := api.Post(
			"/collector/heartbeat",
			map[string]string{"hostname": hostname, "version": Version},
			false,
		); err != nil {
			log.Printf("heartbeat del recolector: %v", err)
			time.Sleep(policy.Next())
			continue
		}
		policy.Reset()
		if err := processTasks(api, *cfg); err != nil {
			log.Printf("tareas del recolector: %v", err)
		}
		time.Sleep(time.Duration(cfg.PollSeconds) * time.Second)
	}
}

func processTasks(api *client.Client, local LocalConfig) error {
	data, err := api.Get("/collector/tasks")
	if err != nil {
		return err
	}
	var tasks []ScanTask
	if err := json.Unmarshal(data, &tasks); err != nil {
		return err
	}
	for _, task := range tasks {
		configData, err := api.Get("/collector/config")
		if err != nil {
			return err
		}
		var server ServerConfig
		if err := json.Unmarshal(configData, &server); err != nil {
			return err
		}
		if server.SiteID != task.SiteID {
			return fmt.Errorf("la tarea pertenece a otra sede")
		}
		log.Printf("iniciando escaneo %s de %s", task.ScanID, server.SiteName)
		result, scanErr := Discover(server, task.Methods, local)
		if scanErr != nil {
			result = ScanResult{Error: scanErr.Error()}
		}
		if _, err := api.Post("/collector/scans/"+task.ScanID+"/results", result, true); err != nil {
			return err
		}
		log.Printf("escaneo %s completado: %d dispositivos", task.ScanID, len(result.Devices))
	}
	return nil
}
