package networkcollector

import (
	"net"
	"testing"
)

func TestEnumerateCIDRsRestrictsScope(t *testing.T) {
	hosts, err := enumerateCIDRs([]string{"192.168.10.0/30"}, 10)
	if err != nil {
		t.Fatal(err)
	}
	if len(hosts) != 2 || hosts[0] != "192.168.10.1" || hosts[1] != "192.168.10.2" {
		t.Fatalf("unexpected hosts: %#v", hosts)
	}
	if _, err := enumerateCIDRs([]string{"8.8.8.0/24"}, 300); err == nil {
		t.Fatal("public networks must be rejected")
	}
	if _, err := enumerateCIDRs([]string{"10.0.0.0/16"}, 100); err == nil {
		t.Fatal("scope larger than limit must be rejected")
	}
}

func TestARPParsersAndClassification(t *testing.T) {
	linux := parseIPNeigh("192.168.1.10 dev eth0 lladdr 24:5a:4c:01:02:03 REACHABLE\n")
	if linux["192.168.1.10"] != "24:5a:4c:01:02:03" {
		t.Fatalf("linux arp not parsed: %#v", linux)
	}
	windows := parseWindowsARP("  192.168.1.20       e8-48-b8-01-02-03     dynamic\n")
	if windows["192.168.1.20"] != "e8:48:b8:01:02:03" {
		t.Fatalf("windows arp not parsed: %#v", windows)
	}
	db := loadOUIDatabase("")
	if got := classifyVendor("", "", "24:5a:4c:01:02:03", db); got != "Ubiquiti" {
		t.Fatalf("unexpected vendor %s", got)
	}
	if got := classifyVendor("Cisco IOS XE", "", "", db); got != "Cisco" {
		t.Fatalf("unexpected vendor %s", got)
	}
	if got := classifyVendor("TP-Link Omada access point", "", "", db); got != "TP-Link" {
		t.Fatalf("unexpected vendor %s", got)
	}
}

func TestLocalTCPDiscovery(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer listener.Close()
	port := listener.Addr().(*net.TCPAddr).Port
	result, err := Discover(
		ServerConfig{
			SiteID:   "test",
			CIDRs:    []string{"127.0.0.1/32"},
			MaxHosts: 1,
			TCPPorts: []int{port},
		},
		[]string{"tcp"},
		LocalConfig{Concurrency: 2, TimeoutMillis: 200},
	)
	if err != nil {
		t.Fatal(err)
	}
	if len(result.Devices) != 1 {
		t.Fatalf("expected one discovered device, got %d", len(result.Devices))
	}
	if result.Devices[0].IPAddress != "127.0.0.1" {
		t.Fatalf("unexpected address %s", result.Devices[0].IPAddress)
	}
}
