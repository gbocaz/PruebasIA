package networkcollector

import (
	"bufio"
	"net"
	"os"
	"strings"
)

var commonOUIs = map[string]string{
	"00000C": "Cisco",
	"001B0C": "Cisco",
	"001C58": "Cisco",
	"001E13": "Cisco",
	"0023EA": "Cisco",
	"0050F2": "Microsoft",
	"145A05": "Apple",
	"14EBB6": "TP-Link",
	"245A4C": "Ubiquiti",
	"24A43C": "Ubiquiti",
	"50C7BF": "TP-Link",
	"6032B1": "TP-Link",
	"788A20": "Ubiquiti",
	"C025E9": "TP-Link",
	"DC9FDB": "Ubiquiti",
	"E063DA": "Ubiquiti",
	"E848B8": "TP-Link",
	"F09FC2": "Ubiquiti",
}

func loadOUIDatabase(path string) map[string]string {
	output := make(map[string]string, len(commonOUIs))
	for prefix, vendor := range commonOUIs {
		output[prefix] = vendor
	}
	if path == "" {
		return output
	}
	file, err := os.Open(path)
	if err != nil {
		return output
	}
	defer file.Close()
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 2 {
			continue
		}
		prefix := cleanPrefix(fields[0])
		if len(prefix) < 6 {
			continue
		}
		output[prefix[:6]] = strings.Join(fields[1:], " ")
	}
	return output
}

func classifyVendor(description, objectID, mac string, oui map[string]string) string {
	lower := strings.ToLower(description + " " + objectID)
	switch {
	case strings.Contains(lower, "cisco"):
		return "Cisco"
	case strings.Contains(lower, "ubiquiti"), strings.Contains(lower, "unifi"):
		return "Ubiquiti"
	case strings.Contains(lower, "tp-link"), strings.Contains(lower, "tplink"), strings.Contains(lower, "omada"):
		return "TP-Link"
	case strings.Contains(lower, "aruba"):
		return "Aruba"
	case strings.Contains(lower, "hewlett packard"), strings.Contains(lower, "procurve"):
		return "HPE"
	case strings.Contains(lower, "mikrotik"):
		return "MikroTik"
	case strings.Contains(lower, "fortinet"):
		return "Fortinet"
	case strings.Contains(lower, "juniper"):
		return "Juniper"
	}
	prefix := cleanPrefix(mac)
	if len(prefix) >= 6 {
		if vendor := oui[prefix[:6]]; vendor != "" {
			return vendor
		}
	}
	return "Desconocido"
}

func classifyDeviceType(description string, ports []int) string {
	lower := strings.ToLower(description)
	switch {
	case strings.Contains(lower, "access point"), strings.Contains(lower, "wireless ap"),
		strings.Contains(lower, "unifi ap"), strings.Contains(lower, "omada ap"):
		return "access_point"
	case strings.Contains(lower, "switch"):
		return "switch"
	case strings.Contains(lower, "router"), strings.Contains(lower, "gateway"),
		strings.Contains(lower, "firewall"):
		return "gateway"
	case strings.Contains(lower, "printer"):
		return "impresora"
	case strings.Contains(lower, "camera"):
		return "camara"
	case containsPort(ports, 3389), containsPort(ports, 5900):
		return "computador"
	case strings.Contains(lower, "linux"), strings.Contains(lower, "windows"):
		return "servidor"
	default:
		return "desconocido"
	}
}

func classifyOS(description string) string {
	lower := strings.ToLower(description)
	switch {
	case strings.Contains(lower, "windows"):
		return "Windows"
	case strings.Contains(lower, "linux"), strings.Contains(lower, "ubuntu"),
		strings.Contains(lower, "debian"), strings.Contains(lower, "red hat"):
		return "Linux"
	case strings.Contains(lower, "ios"):
		return "Cisco IOS"
	case strings.Contains(lower, "routeros"):
		return "RouterOS"
	default:
		return ""
	}
}

func containsPort(ports []int, wanted int) bool {
	for _, port := range ports {
		if port == wanted {
			return true
		}
	}
	return false
}

func cleanPrefix(value string) string {
	replacer := strings.NewReplacer(":", "", "-", "", ".", "", " ", "")
	return strings.ToUpper(replacer.Replace(value))
}

func normalizeMAC(value string) string {
	hardware, err := net.ParseMAC(strings.TrimSpace(value))
	if err != nil {
		return ""
	}
	return strings.ToLower(hardware.String())
}
