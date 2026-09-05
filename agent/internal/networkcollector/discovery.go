package networkcollector

import (
	"context"
	"errors"
	"fmt"
	"net"
	"sort"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
)

type probeResult struct {
	ip            string
	responsive    bool
	tcpResponsive bool
	openPorts     []int
	snmp          SNMPInfo
}

func Discover(cfg ServerConfig, methods []string, local LocalConfig) (ScanResult, error) {
	allowed := map[string]bool{}
	for _, method := range methods {
		allowed[method] = true
	}
	addresses, err := enumerateCIDRs(cfg.CIDRs, cfg.MaxHosts)
	if err != nil {
		return ScanResult{}, err
	}
	jobs := make(chan string)
	results := make(chan probeResult, len(addresses))
	workers := local.Concurrency
	if workers > len(addresses) {
		workers = len(addresses)
	}
	if workers < 1 {
		workers = 1
	}
	var wg sync.WaitGroup
	timeout := time.Duration(local.TimeoutMillis) * time.Millisecond
	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for ip := range jobs {
				result := probeResult{ip: ip}
				if allowed["tcp"] {
					result.openPorts, result.tcpResponsive = probeTCP(ip, cfg.TCPPorts, timeout)
					result.responsive = result.tcpResponsive
				}
				if allowed["snmp"] && len(cfg.Credentials) > 0 {
					if info, ok := probeSNMP(ip, cfg.Credentials, timeout); ok {
						result.snmp = info
						result.responsive = true
					}
				}
				results <- result
			}
		}()
	}
	go func() {
		for _, ip := range addresses {
			jobs <- ip
		}
		close(jobs)
		wg.Wait()
		close(results)
	}()

	probes := map[string]probeResult{}
	for result := range results {
		probes[result.ip] = result
	}
	arp := map[string]string{}
	if allowed["arp"] {
		arp = neighborTable()
	}
	vendorDB := loadOUIDatabase(local.OUIFile)
	var devices []Device
	for _, ip := range addresses {
		probe := probes[ip]
		mac := normalizeMAC(arp[ip])
		if !probe.responsive && mac == "" {
			continue
		}
		source := []string{}
		if probe.tcpResponsive {
			source = append(source, "tcp")
		}
		if probe.snmp.Found {
			source = append(source, "snmp")
		}
		if mac != "" {
			source = append(source, "arp")
		}
		hostname := probe.snmp.SysName
		if hostname == "" {
			hostname = reverseName(ip, timeout)
		}
		identity := strings.ToLower(mac)
		if identity == "" {
			identity = ip
		}
		vendor := classifyVendor(probe.snmp.SysDescription, probe.snmp.SysObjectID, mac, vendorDB)
		deviceType := classifyDeviceType(probe.snmp.SysDescription, probe.openPorts)
		services, managementURL := servicesFor(ip, probe.openPorts)
		device := Device{
			IdentityKey:     identity,
			IPAddress:       ip,
			MACAddress:      mac,
			Hostname:        hostname,
			Vendor:          vendor,
			Model:           probe.snmp.Model,
			SerialNumber:    probe.snmp.Serial,
			DeviceType:      deviceType,
			OSName:          classifyOS(probe.snmp.SysDescription),
			Status:          "online",
			DiscoverySource: strings.Join(source, ","),
			SysName:         probe.snmp.SysName,
			SysDescription:  probe.snmp.SysDescription,
			SysObjectID:     probe.snmp.SysObjectID,
			OpenPorts:       probe.openPorts,
			RemoteServices:  services,
			ManagementURL:   managementURL,
			neighbors:       probe.snmp.Neighbors,
		}
		devices = append(devices, device)
	}
	sort.Slice(devices, func(i, j int) bool {
		return bytesCompareIP(devices[i].IPAddress, devices[j].IPAddress) < 0
	})
	var links []Link
	for _, device := range devices {
		for _, neighbor := range device.neighbors {
			links = append(links, Link{
				SourceIdentity: device.IdentityKey,
				TargetIdentity: neighbor.Identity,
				SourcePort:     neighbor.LocalPort,
				TargetPort:     neighbor.RemotePort,
				Protocol:       neighbor.Protocol,
			})
		}
	}
	return ScanResult{Devices: devices, Links: links}, nil
}

func enumerateCIDRs(cidrs []string, limit int) ([]string, error) {
	if limit <= 0 {
		return nil, errors.New("max_hosts debe ser mayor que cero")
	}
	seen := map[string]bool{}
	var out []string
	for _, raw := range cidrs {
		ip, network, err := net.ParseCIDR(raw)
		if err != nil {
			return nil, fmt.Errorf("CIDR inválido %q: %w", raw, err)
		}
		if !ip.IsPrivate() && !ip.IsLoopback() && !ip.IsLinkLocalUnicast() {
			return nil, fmt.Errorf("se rechazó una red no privada: %s", raw)
		}
		var all []net.IP
		for current := cloneIP(network.IP); network.Contains(current); incrementIP(current) {
			all = append(all, cloneIP(current))
			if len(all) > limit+2 {
				return nil, fmt.Errorf("el alcance supera el máximo de %d hosts", limit)
			}
		}
		ones, bits := network.Mask.Size()
		if bits == 32 && ones < 31 && len(all) >= 2 {
			all = all[1 : len(all)-1]
		}
		for _, address := range all {
			text := address.String()
			if !seen[text] {
				seen[text] = true
				out = append(out, text)
				if len(out) > limit {
					return nil, fmt.Errorf("el alcance supera el máximo de %d hosts", limit)
				}
			}
		}
	}
	return out, nil
}

func cloneIP(ip net.IP) net.IP {
	out := make(net.IP, len(ip))
	copy(out, ip)
	return out
}

func incrementIP(ip net.IP) {
	for index := len(ip) - 1; index >= 0; index-- {
		ip[index]++
		if ip[index] != 0 {
			break
		}
	}
}

func probeTCP(ip string, ports []int, timeout time.Duration) ([]int, bool) {
	var open []int
	responsive := false
	for _, port := range ports {
		address := net.JoinHostPort(ip, strconv.Itoa(port))
		conn, err := net.DialTimeout("tcp", address, timeout)
		if err == nil {
			responsive = true
			open = append(open, port)
			_ = conn.Close()
			continue
		}
		if errors.Is(err, syscall.ECONNREFUSED) {
			responsive = true
		}
	}
	sort.Ints(open)
	return open, responsive
}

func reverseName(ip string, timeout time.Duration) string {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	names, err := net.DefaultResolver.LookupAddr(ctx, ip)
	if err != nil || len(names) == 0 {
		return ""
	}
	return strings.TrimSuffix(names[0], ".")
}

func servicesFor(ip string, ports []int) ([]string, string) {
	var services []string
	management := ""
	for _, port := range ports {
		switch port {
		case 22:
			services = append(services, "ssh")
		case 80:
			services = append(services, "http")
			if management == "" {
				management = "http://" + ip
			}
		case 443:
			services = append(services, "https")
			management = "https://" + ip
		case 3389:
			services = append(services, "rdp")
		case 5900:
			services = append(services, "vnc")
		}
	}
	return services, management
}

func bytesCompareIP(left, right string) int {
	a := net.ParseIP(left)
	b := net.ParseIP(right)
	if a == nil || b == nil {
		return strings.Compare(left, right)
	}
	return strings.Compare(string(a.To16()), string(b.To16()))
}
