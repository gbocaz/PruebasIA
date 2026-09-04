package collect

import (
	"bufio"
	"os"
	"os/exec"
	"runtime"
	"strings"
)

type Software struct {
	Name      string `json:"name"`
	Version   string `json:"version"`
	Publisher string `json:"publisher"`
}

func InstalledSoftware() []Software {
	if runtime.GOOS == "windows" {
		return windowsSoftware()
	}
	return linuxSoftware()
}

func linuxSoftware() []Software {
	if items := dpkgSoftware(); len(items) > 0 {
		return items
	}
	return rpmSoftware()
}

func dpkgSoftware() []Software {
	cmd := exec.Command("dpkg-query", "-W", "-f=${Package}\t${Version}\t${Maintainer}\n")
	out, err := cmd.Output()
	if err != nil {
		return nil
	}
	var items []Software
	sc := bufio.NewScanner(strings.NewReader(string(out)))
	for sc.Scan() {
		parts := strings.Split(sc.Text(), "\t")
		if len(parts) < 2 || parts[0] == "" {
			continue
		}
		pub := ""
		if len(parts) > 2 {
			pub = parts[2]
		}
		items = append(items, Software{Name: parts[0], Version: parts[1], Publisher: pub})
	}
	return items
}

func rpmSoftware() []Software {
	cmd := exec.Command("rpm", "-qa", "--queryformat", "%{NAME}\t%{VERSION}\t%{VENDOR}\n")
	out, err := cmd.Output()
	if err != nil {
		return nil
	}
	var items []Software
	sc := bufio.NewScanner(strings.NewReader(string(out)))
	for sc.Scan() {
		parts := strings.Split(sc.Text(), "\t")
		if len(parts) < 2 {
			continue
		}
		pub := ""
		if len(parts) > 2 {
			pub = parts[2]
		}
		items = append(items, Software{Name: parts[0], Version: parts[1], Publisher: pub})
	}
	return items
}

func readOSRelease() string {
	f, err := os.Open("/etc/os-release")
	if err != nil {
		return ""
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		if strings.HasPrefix(sc.Text(), "PRETTY_NAME=") {
			return strings.Trim(strings.TrimPrefix(sc.Text(), "PRETTY_NAME="), `"`)
		}
	}
	return ""
}
