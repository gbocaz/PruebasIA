//go:build windows

package collect

import (
	"golang.org/x/sys/windows/registry"
)

func windowsSoftware() []Software {
	roots := []registry.Key{registry.LOCAL_MACHINE, registry.CURRENT_USER}
	paths := []string{
		`SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`,
		`SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall`,
	}
	var items []Software
	seen := map[string]bool{}
	for _, root := range roots {
		for _, path := range paths {
			k, err := registry.OpenKey(root, path, registry.READ)
			if err != nil {
				continue
			}
			names, _ := k.ReadSubKeyNames(-1)
			for _, name := range names {
				sk, err := registry.OpenKey(k, name, registry.READ)
				if err != nil {
					continue
				}
				display, _, _ := sk.GetStringValue("DisplayName")
				if display == "" {
					sk.Close()
					continue
				}
				version, _, _ := sk.GetStringValue("DisplayVersion")
				publisher, _, _ := sk.GetStringValue("Publisher")
				sk.Close()
				key := display + "|" + version
				if seen[key] {
					continue
				}
				seen[key] = true
				items = append(items, Software{Name: display, Version: version, Publisher: publisher})
			}
			k.Close()
		}
	}
	return items
}
