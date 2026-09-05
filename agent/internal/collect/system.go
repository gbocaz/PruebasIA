package collect

import (
	"net"
	"os"
	"os/user"
	"runtime"
	"strings"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/host"
	"github.com/shirou/gopsutil/v3/mem"
	netutil "github.com/shirou/gopsutil/v3/net"
)

type Interface struct {
	Name      string `json:"name"`
	MAC       string `json:"mac"`
	IPv4      string `json:"ipv4"`
	IPv6      string `json:"ipv6"`
	IsUp      bool   `json:"is_up"`
	SpeedMbps int    `json:"speed_mbps"`
	BytesSent uint64 `json:"bytes_sent"`
	BytesRecv uint64 `json:"bytes_recv"`
}

type Snapshot struct {
	Hostname      string      `json:"hostname"`
	OSFamily      string      `json:"os_family"`
	OSName        string      `json:"os_name"`
	OSVersion     string      `json:"os_version"`
	Architecture  string      `json:"architecture"`
	IPAddress     string      `json:"ip_address"`
	MACAddress    string      `json:"mac_address"`
	LoggedUser    string      `json:"logged_user"`
	CPUModel      string      `json:"cpu_model"`
	CPUPercent    float64     `json:"cpu_percent"`
	RAMTotalMB    uint64      `json:"ram_total_mb"`
	RAMUsedMB     uint64      `json:"ram_used_mb"`
	DiskTotalGB   float64     `json:"disk_total_gb"`
	DiskUsedGB    float64     `json:"disk_used_gb"`
	UptimeSeconds uint64      `json:"uptime_seconds"`
	AgentVersion  string      `json:"agent_version"`
	BytesSent     uint64      `json:"bytes_sent"`
	BytesRecv     uint64      `json:"bytes_recv"`
	Interfaces    []Interface `json:"interfaces"`
}

func osFamily() string {
	switch runtime.GOOS {
	case "windows":
		return "windows"
	case "linux":
		return "linux"
	default:
		return "other"
	}
}

func Collect(agentVersion string) Snapshot {
	hostInfo, _ := host.Info()
	vm, _ := mem.VirtualMemory()
	cpuPct, _ := cpu.Percent(200*time.Millisecond, false)
	cpuInfo, _ := cpu.Info()
	du, _ := disk.Usage(rootPath())
	ifaces := interfaces()
	snap := Snapshot{
		Hostname:     hostname(),
		OSFamily:     osFamily(),
		Architecture: runtime.GOARCH,
		LoggedUser:   currentUser(),
		AgentVersion: agentVersion,
		Interfaces:   ifaces,
	}
	if hostInfo != nil {
		snap.OSName = hostInfo.Platform
		snap.OSVersion = hostInfo.PlatformVersion
		snap.UptimeSeconds = hostInfo.Uptime
	}
	if vm != nil {
		snap.RAMTotalMB = vm.Total / 1024 / 1024
		snap.RAMUsedMB = vm.Used / 1024 / 1024
	}
	if len(cpuPct) > 0 {
		snap.CPUPercent = cpuPct[0]
	}
	if len(cpuInfo) > 0 {
		snap.CPUModel = cpuInfo[0].ModelName
	}
	if du != nil {
		snap.DiskTotalGB = float64(du.Total) / 1024 / 1024 / 1024
		snap.DiskUsedGB = float64(du.Used) / 1024 / 1024 / 1024
	}
	for _, iface := range ifaces {
		snap.BytesSent += iface.BytesSent
		snap.BytesRecv += iface.BytesRecv
		if snap.IPAddress == "" && iface.IPv4 != "" && !strings.HasPrefix(iface.IPv4, "127.") {
			snap.IPAddress = iface.IPv4
			snap.MACAddress = iface.MAC
		}
	}
	return snap
}

func hostname() string {
	h, err := os.Hostname()
	if err != nil {
		return "unknown"
	}
	return h
}

func currentUser() string {
	u, err := user.Current()
	if err != nil {
		return ""
	}
	return u.Username
}

func rootPath() string {
	if runtime.GOOS == "windows" {
		return `C:\`
	}
	return "/"
}

func interfaces() []Interface {
	ioCounters, _ := netutil.IOCounters(true)
	ioByName := map[string]netutil.IOCountersStat{}
	for _, c := range ioCounters {
		ioByName[c.Name] = c
	}
	addrs, err := net.Interfaces()
	if err != nil {
		return nil
	}
	var out []Interface
	for _, ni := range addrs {
		item := Interface{Name: ni.Name, MAC: ni.HardwareAddr.String(), IsUp: ni.Flags&net.FlagUp != 0}
		if io, ok := ioByName[ni.Name]; ok {
			item.BytesSent = io.BytesSent
			item.BytesRecv = io.BytesRecv
		}
		ipAddrs, _ := ni.Addrs()
		for _, a := range ipAddrs {
			s := a.String()
			ip, _, _ := net.ParseCIDR(s)
			if ip == nil {
				continue
			}
			if ip.To4() != nil && item.IPv4 == "" {
				item.IPv4 = ip.String()
			} else if ip.To4() == nil && item.IPv6 == "" && !ip.IsLoopback() {
				item.IPv6 = ip.String()
			}
		}
		out = append(out, item)
	}
	return out
}
