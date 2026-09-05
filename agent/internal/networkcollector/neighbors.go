package networkcollector

import (
	"bufio"
	"os/exec"
	"runtime"
	"strings"
)

func neighborTable() map[string]string {
	switch runtime.GOOS {
	case "linux":
		if output, err := exec.Command("ip", "neigh", "show").Output(); err == nil {
			return parseIPNeigh(string(output))
		}
	case "windows":
		if output, err := exec.Command("arp", "-a").Output(); err == nil {
			return parseWindowsARP(string(output))
		}
	default:
		if output, err := exec.Command("arp", "-an").Output(); err == nil {
			return parseBSDARP(string(output))
		}
	}
	return map[string]string{}
}

func parseIPNeigh(output string) map[string]string {
	result := map[string]string{}
	scanner := bufio.NewScanner(strings.NewReader(output))
	for scanner.Scan() {
		fields := strings.Fields(scanner.Text())
		if len(fields) < 4 {
			continue
		}
		for index, field := range fields {
			if field == "lladdr" && index+1 < len(fields) {
				if mac := normalizeMAC(fields[index+1]); mac != "" {
					result[fields[0]] = mac
				}
			}
		}
	}
	return result
}

func parseWindowsARP(output string) map[string]string {
	result := map[string]string{}
	scanner := bufio.NewScanner(strings.NewReader(output))
	for scanner.Scan() {
		fields := strings.Fields(scanner.Text())
		if len(fields) < 2 {
			continue
		}
		if mac := normalizeMAC(fields[1]); mac != "" {
			result[fields[0]] = mac
		}
	}
	return result
}

func parseBSDARP(output string) map[string]string {
	result := map[string]string{}
	scanner := bufio.NewScanner(strings.NewReader(output))
	for scanner.Scan() {
		fields := strings.Fields(scanner.Text())
		if len(fields) < 4 {
			continue
		}
		ip := strings.Trim(fields[1], "()")
		if fields[2] == "at" {
			if mac := normalizeMAC(fields[3]); mac != "" {
				result[ip] = mac
			}
		}
	}
	return result
}
