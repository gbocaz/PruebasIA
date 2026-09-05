package networkcollector

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/gosnmp/gosnmp"
)

const (
	oidSysDescr       = ".1.3.6.1.2.1.1.1.0"
	oidSysObjectID    = ".1.3.6.1.2.1.1.2.0"
	oidSysName        = ".1.3.6.1.2.1.1.5.0"
	oidEntitySerial   = ".1.3.6.1.2.1.47.1.1.1.1.11"
	oidEntityModel    = ".1.3.6.1.2.1.47.1.1.1.1.13"
	oidLLDPRemotePort = ".1.0.8802.1.1.2.1.4.1.1.7"
	oidLLDPRemoteName = ".1.0.8802.1.1.2.1.4.1.1.9"
	oidCDPRemoteName  = ".1.3.6.1.4.1.9.9.23.1.2.1.1.6"
	oidCDPRemotePort  = ".1.3.6.1.4.1.9.9.23.1.2.1.1.7"
)

type SNMPInfo struct {
	Found          bool
	SysName        string
	SysDescription string
	SysObjectID    string
	Model          string
	Serial         string
	Neighbors      []Neighbor
}

func probeSNMP(ip string, credentials []Credential, timeout time.Duration) (SNMPInfo, bool) {
	for _, credential := range credentials {
		session, err := snmpSession(ip, credential, timeout)
		if err != nil {
			continue
		}
		if err := session.Connect(); err != nil {
			continue
		}
		info, ok := readSNMP(session)
		_ = session.Conn.Close()
		if ok {
			return info, true
		}
	}
	return SNMPInfo{}, false
}

func snmpSession(ip string, credential Credential, timeout time.Duration) (*gosnmp.GoSNMP, error) {
	session := &gosnmp.GoSNMP{
		Target:    ip,
		Port:      161,
		Transport: "udp",
		Timeout:   timeout,
		Retries:   0,
		MaxOids:   gosnmp.MaxOids,
	}
	switch credential.Kind {
	case "snmp_v2c":
		session.Version = gosnmp.Version2c
		session.Community = credential.Secret
	case "snmp_v3":
		auth, ok := authProtocol(credential.AuthProtocol)
		if !ok {
			return nil, fmt.Errorf("protocolo de autenticación SNMPv3 no válido")
		}
		priv, ok := privacyProtocol(credential.PrivProtocol)
		if !ok {
			return nil, fmt.Errorf("protocolo de privacidad SNMPv3 no válido")
		}
		session.Version = gosnmp.Version3
		session.SecurityModel = gosnmp.UserSecurityModel
		flags := gosnmp.AuthNoPriv
		if priv != gosnmp.NoPriv {
			flags = gosnmp.AuthPriv
		}
		session.MsgFlags = flags
		session.SecurityParameters = &gosnmp.UsmSecurityParameters{
			UserName:                 credential.Username,
			AuthenticationProtocol:   auth,
			AuthenticationPassphrase: credential.Secret,
			PrivacyProtocol:          priv,
			PrivacyPassphrase:        credential.PrivacySecret,
		}
	default:
		return nil, fmt.Errorf("tipo de credencial no soportado")
	}
	return session, nil
}

func authProtocol(value string) (gosnmp.SnmpV3AuthProtocol, bool) {
	switch strings.ToUpper(value) {
	case "MD5":
		return gosnmp.MD5, true
	case "SHA":
		return gosnmp.SHA, true
	case "SHA224":
		return gosnmp.SHA224, true
	case "SHA256":
		return gosnmp.SHA256, true
	case "SHA384":
		return gosnmp.SHA384, true
	case "SHA512":
		return gosnmp.SHA512, true
	default:
		return gosnmp.NoAuth, false
	}
}

func privacyProtocol(value string) (gosnmp.SnmpV3PrivProtocol, bool) {
	switch strings.ToUpper(value) {
	case "", "NONE":
		return gosnmp.NoPriv, true
	case "DES":
		return gosnmp.DES, true
	case "AES":
		return gosnmp.AES, true
	case "AES192":
		return gosnmp.AES192, true
	case "AES256":
		return gosnmp.AES256, true
	default:
		return gosnmp.NoPriv, false
	}
}

func readSNMP(session *gosnmp.GoSNMP) (SNMPInfo, bool) {
	packet, err := session.Get([]string{oidSysDescr, oidSysObjectID, oidSysName})
	if err != nil || packet.Error != gosnmp.NoError {
		return SNMPInfo{}, false
	}
	info := SNMPInfo{Found: true}
	for _, variable := range packet.Variables {
		switch normalizeOID(variable.Name) {
		case normalizeOID(oidSysDescr):
			info.SysDescription = pduString(variable)
		case normalizeOID(oidSysObjectID):
			info.SysObjectID = pduString(variable)
		case normalizeOID(oidSysName):
			info.SysName = pduString(variable)
		}
	}
	info.Model = firstWalkString(session, oidEntityModel)
	info.Serial = firstWalkString(session, oidEntitySerial)
	info.Neighbors = append(info.Neighbors, readNeighbors(session, "lldp", oidLLDPRemoteName, oidLLDPRemotePort)...)
	info.Neighbors = append(info.Neighbors, readNeighbors(session, "cdp", oidCDPRemoteName, oidCDPRemotePort)...)
	return info, true
}

func firstWalkString(session *gosnmp.GoSNMP, oid string) string {
	value := ""
	_ = session.Walk(oid, func(pdu gosnmp.SnmpPDU) error {
		if value == "" {
			value = strings.TrimSpace(pduString(pdu))
		}
		return nil
	})
	return value
}

func readNeighbors(session *gosnmp.GoSNMP, protocol, nameOID, portOID string) []Neighbor {
	names := map[string]string{}
	ports := map[string]string{}
	_ = session.Walk(nameOID, func(pdu gosnmp.SnmpPDU) error {
		names[oidSuffix(pdu.Name, nameOID)] = strings.TrimSpace(pduString(pdu))
		return nil
	})
	_ = session.Walk(portOID, func(pdu gosnmp.SnmpPDU) error {
		ports[oidSuffix(pdu.Name, portOID)] = strings.TrimSpace(pduString(pdu))
		return nil
	})
	var output []Neighbor
	for suffix, name := range names {
		if name == "" {
			continue
		}
		localPort := localPortFromSuffix(suffix, protocol)
		output = append(output, Neighbor{
			Identity:   "name:" + strings.ToLower(name),
			LocalPort:  localPort,
			RemotePort: ports[suffix],
			Protocol:   protocol,
		})
	}
	return output
}

func pduString(pdu gosnmp.SnmpPDU) string {
	switch value := pdu.Value.(type) {
	case []byte:
		return string(value)
	case string:
		return value
	default:
		return fmt.Sprint(value)
	}
}

func normalizeOID(value string) string {
	return strings.TrimPrefix(value, ".")
}

func oidSuffix(value, base string) string {
	return strings.TrimPrefix(normalizeOID(value), normalizeOID(base)+".")
}

func localPortFromSuffix(suffix, protocol string) string {
	parts := strings.Split(suffix, ".")
	if protocol == "lldp" && len(parts) >= 3 {
		return parts[len(parts)-2]
	}
	if protocol == "cdp" && len(parts) >= 2 {
		return parts[len(parts)-2]
	}
	if len(parts) > 0 {
		if _, err := strconv.Atoi(parts[0]); err == nil {
			return parts[0]
		}
	}
	return ""
}
