package main

import (
	"flag"
	"fmt"
	"log"
	"net"
	"net/url"
	"os"
	"strings"

	"github.com/gbocaz/tic-control-agent/internal/networkcollector"
	svc "github.com/gbocaz/tic-control-agent/internal/service"
)

func main() {
	if len(os.Args) < 2 {
		run(networkcollector.DefaultConfigPath())
		return
	}
	switch os.Args[1] {
	case "configure":
		configure(os.Args[2:])
	case "run":
		fs := flag.NewFlagSet("run", flag.ExitOnError)
		path := fs.String("config", networkcollector.DefaultConfigPath(), "Ruta de configuración")
		_ = fs.Parse(os.Args[2:])
		run(*path)
	case "install-service":
		installService()
	case "uninstall-service":
		uninstallService()
	case "version":
		fmt.Println(networkcollector.Version)
	default:
		log.Fatalf("comando desconocido: %s", os.Args[1])
	}
}

func configure(args []string) {
	fs := flag.NewFlagSet("configure", flag.ExitOnError)
	server := fs.String("server", "", "URL HTTPS de TIC Control AI")
	token := fs.String("token", "", "Token del recolector generado en la sede")
	path := fs.String("config", networkcollector.DefaultConfigPath(), "Ruta de configuración")
	poll := fs.Int("poll-seconds", 30, "Intervalo de consulta")
	concurrency := fs.Int("concurrency", 64, "Sondeos simultáneos (máximo 256)")
	timeout := fs.Int("timeout-ms", 800, "Timeout por puerto/SNMP")
	oui := fs.String("oui-file", "", "Base OUI local opcional")
	_ = fs.Parse(args)
	if *server == "" || *token == "" {
		log.Fatal("uso: tic-network-collector configure --server URL --token TOKEN")
	}
	if err := validateServer(*server); err != nil {
		log.Fatal(err)
	}
	cfg := &networkcollector.LocalConfig{
		ServerURL:      strings.TrimRight(*server, "/"),
		CollectorToken: *token,
		PollSeconds:    *poll,
		Concurrency:    *concurrency,
		TimeoutMillis:  *timeout,
		OUIFile:        *oui,
	}
	if err := networkcollector.SaveConfig(*path, cfg); err != nil {
		log.Fatal(err)
	}
	fmt.Printf("Configuración guardada en %s con permisos restringidos\n", *path)
}

func run(path string) {
	cfg, err := networkcollector.LoadConfig(path)
	if err != nil {
		log.Fatal(err)
	}
	if err := validateServer(cfg.ServerURL); err != nil {
		log.Fatal(err)
	}
	if err := networkcollector.Run(path); err != nil {
		log.Fatal(err)
	}
}

func validateServer(raw string) error {
	parsed, err := url.Parse(raw)
	if err != nil || parsed.Hostname() == "" {
		return fmt.Errorf("URL de servidor inválida")
	}
	if parsed.Scheme == "https" {
		return nil
	}
	host := parsed.Hostname()
	if parsed.Scheme == "http" {
		ip := net.ParseIP(host)
		if host == "localhost" || (ip != nil && ip.IsLoopback()) {
			return nil
		}
	}
	return fmt.Errorf("HTTPS es obligatorio salvo en localhost")
}

func installService() {
	service, err := svc.New(
		"TICControlNetworkCollector",
		"TIC Control Network Collector",
		"Descubrimiento autorizado de red para TIC Control AI",
		func() { run(networkcollector.DefaultConfigPath()) },
	)
	if err != nil {
		log.Fatal(err)
	}
	if err := service.Install(); err != nil {
		log.Fatal(err)
	}
	fmt.Println("Servicio del recolector instalado")
}

func uninstallService() {
	service, err := svc.New(
		"TICControlNetworkCollector",
		"TIC Control Network Collector",
		"Descubrimiento autorizado de red para TIC Control AI",
		func() {},
	)
	if err != nil {
		log.Fatal(err)
	}
	if err := service.Uninstall(); err != nil {
		log.Fatal(err)
	}
	fmt.Println("Servicio del recolector desinstalado")
}
