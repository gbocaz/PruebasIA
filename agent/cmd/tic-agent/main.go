package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"github.com/gbocaz/tic-control-agent/internal/backoff"
	"github.com/gbocaz/tic-control-agent/internal/client"
	"github.com/gbocaz/tic-control-agent/internal/collect"
	"github.com/gbocaz/tic-control-agent/internal/config"
	"github.com/gbocaz/tic-control-agent/internal/queue"
	svc "github.com/gbocaz/tic-control-agent/internal/service"
	"github.com/gbocaz/tic-control-agent/internal/tasks"
)

const version = "0.1.0"

func main() {
	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "enroll":
			enrollCmd(os.Args[2:])
			return
		case "run":
			runCmd(os.Args[2:])
			return
		case "install-service":
			installService()
			return
		case "uninstall-service":
			uninstallService()
			return
		case "version":
			fmt.Println(version)
			return
		}
	}
	runLoop(config.DefaultPath())
}

func enrollCmd(args []string) {
	fs := flag.NewFlagSet("enroll", flag.ExitOnError)
	server := fs.String("server", "", "URL del servidor, por ejemplo https://tic.institucion.tld")
	token := fs.String("token", "", "Token de enrolamiento")
	tokenFile := fs.String("token-file", "", "Archivo protegido que contiene el token")
	cfgPath := fs.String("config", config.DefaultPath(), "Ruta de configuración")
	_ = fs.Parse(args)
	enrollmentToken := *token
	if *tokenFile != "" {
		data, err := os.ReadFile(*tokenFile)
		if err != nil {
			log.Fatalf("no se pudo leer token-file: %v", err)
		}
		enrollmentToken = strings.TrimSpace(string(data))
	}
	if *server == "" || enrollmentToken == "" {
		log.Fatal("uso: tic-agent enroll --server URL (--token TOKEN | --token-file ARCHIVO)")
	}
	cli := client.New(*server, "", nil)
	host := collect.Collect(version)
	body := map[string]any{
		"token":         enrollmentToken,
		"hostname":      host.Hostname,
		"os_family":     host.OSFamily,
		"os_name":       host.OSName,
		"os_version":    host.OSVersion,
		"architecture":  host.Architecture,
		"agent_version": version,
	}
	data, err := cli.Post("/agent/enroll", body, false)
	if err != nil {
		log.Fatalf("enrolamiento fallido: %v", err)
	}
	var res struct {
		DeviceID      string `json:"device_id"`
		AgentToken    string `json:"agent_token"`
		HMACSecret    string `json:"hmac_secret"`
		HeartbeatSecs int    `json:"heartbeat_interval_seconds"`
	}
	if err := json.Unmarshal(data, &res); err != nil {
		log.Fatal(err)
	}
	cfg := &config.File{
		ServerURL:     *server,
		DeviceID:      res.DeviceID,
		AgentToken:    res.AgentToken,
		HMACSecret:    res.HMACSecret,
		HeartbeatSecs: res.HeartbeatSecs,
		AgentVersion:  version,
	}
	if err := config.Save(*cfgPath, cfg); err != nil {
		log.Fatal(err)
	}
	fmt.Printf("Enrolado como %s (%s)\n", host.Hostname, res.DeviceID)
}

func runCmd(args []string) {
	fs := flag.NewFlagSet("run", flag.ExitOnError)
	cfgPath := fs.String("config", config.DefaultPath(), "Ruta de configuración")
	_ = fs.Parse(args)
	runLoop(*cfgPath)
}

func runLoop(cfgPath string) {
	cfg, err := config.Load(cfgPath)
	if err != nil {
		log.Fatalf("no se pudo leer %s: %v (ejecute enroll primero)", cfgPath, err)
	}
	stateDir := config.StateDir(cfgPath)
	q := queue.New(stateDir)
	cli := client.New(cfg.ServerURL, cfg.AgentToken, q)
	policy := backoff.Policy{}
	cycles := 0
	for {
		cli.FlushQueue()
		snap := collect.Collect(version)
		_, err := cli.Post("/agent/heartbeat", snap, true)
		if err != nil {
			log.Printf("heartbeat: %v", err)
			time.Sleep(policy.Next())
			continue
		}
		policy.Reset()
		cycles++
		if cycles%6 == 1 {
			sw := collect.InstalledSoftware()
			_, err = cli.Post("/agent/inventory", map[string]any{
				"software":   sw,
				"interfaces": snap.Interfaces,
			}, true)
			if err != nil {
				log.Printf("inventario: %v", err)
			}
		}
		tasks.Run(cli, cfg, stateDir)
		wait := time.Duration(cfg.HeartbeatSecs) * time.Second
		if wait <= 0 {
			wait = 60 * time.Second
		}
		time.Sleep(wait)
	}
}

func installService() {
	s, err := svc.New("TICControlAgent", "TIC Control Agent", "Agente de inventario y mantenimiento TIC Control AI", func() {
		runLoop(config.DefaultPath())
	})
	if err != nil {
		log.Fatal(err)
	}
	if err := s.Install(); err != nil {
		log.Fatal(err)
	}
	fmt.Println("Servicio instalado")
}

func uninstallService() {
	s, err := svc.New("TICControlAgent", "TIC Control Agent", "Agente de inventario y mantenimiento TIC Control AI", func() {})
	if err != nil {
		log.Fatal(err)
	}
	if err := s.Uninstall(); err != nil {
		log.Fatal(err)
	}
	fmt.Println("Servicio desinstalado")
}
