package networkcollector

type Credential struct {
	ID            string `json:"id"`
	Name          string `json:"name"`
	Kind          string `json:"kind"`
	Username      string `json:"username"`
	Secret        string `json:"secret"`
	AuthProtocol  string `json:"auth_protocol"`
	PrivProtocol  string `json:"privacy_protocol"`
	PrivacySecret string `json:"privacy_secret"`
}

type ServerConfig struct {
	SiteID      string       `json:"site_id"`
	SiteName    string       `json:"site_name"`
	CIDRs       []string     `json:"cidrs"`
	MaxHosts    int          `json:"max_hosts"`
	TCPPorts    []int        `json:"tcp_ports"`
	Credentials []Credential `json:"credentials"`
}

type ScanTask struct {
	ScanID      string   `json:"scan_id"`
	SiteID      string   `json:"site_id"`
	Methods     []string `json:"methods"`
	RequestedAt string   `json:"requested_at"`
}

type Neighbor struct {
	Identity   string
	LocalPort  string
	RemotePort string
	Protocol   string
}

type Device struct {
	IdentityKey     string   `json:"identity_key"`
	IPAddress       string   `json:"ip_address"`
	MACAddress      string   `json:"mac_address"`
	Hostname        string   `json:"hostname"`
	Vendor          string   `json:"vendor"`
	Model           string   `json:"model"`
	SerialNumber    string   `json:"serial_number"`
	DeviceType      string   `json:"device_type"`
	OSName          string   `json:"os_name"`
	Status          string   `json:"status"`
	DiscoverySource string   `json:"discovery_source"`
	SysName         string   `json:"sys_name"`
	SysDescription  string   `json:"sys_description"`
	SysObjectID     string   `json:"sys_object_id"`
	OpenPorts       []int    `json:"open_ports"`
	RemoteServices  []string `json:"remote_services"`
	ManagementURL   string   `json:"management_url"`
	SwitchPort      string   `json:"switch_port"`
	VLAN            string   `json:"vlan"`
	SSID            string   `json:"ssid"`
	neighbors       []Neighbor
}

type Link struct {
	SourceIdentity string `json:"source_identity"`
	TargetIdentity string `json:"target_identity"`
	SourcePort     string `json:"source_port"`
	TargetPort     string `json:"target_port"`
	Protocol       string `json:"protocol"`
}

type ScanResult struct {
	Devices []Device `json:"devices"`
	Links   []Link   `json:"links"`
	Error   string   `json:"error,omitempty"`
}
