# ===== OIDs SNMP REAIS =====
# Baseado nos MIBs padrão + MIBs proprietários de ONUs/Home Gateways

OIDs = {
    # RFC 1213 - MIB-II (padrão universal)
    "system": {
        "sysDescr": "1.3.6.1.2.1.1.1.0",
        "sysObjectID": "1.3.6.1.2.1.1.2.0",
        "sysUpTime": "1.3.6.1.2.1.1.3.0",
        "sysContact": "1.3.6.1.2.1.1.4.0",
        "sysName": "1.3.6.1.2.1.1.5.0",
        "sysLocation": "1.3.6.1.2.1.1.6.0",
    },

    # Interfaces (IF-MIB - RFC 2863)
    "interfaces": {
        "ifNumber": "1.3.6.1.2.1.2.1.0",
        "ifDescr": "1.3.6.1.2.1.2.2.1.2",
        "ifType": "1.3.6.1.2.1.2.2.1.3",
        "ifSpeed": "1.3.6.1.2.1.2.2.1.5",
        "ifOperStatus": "1.3.6.1.2.1.2.2.1.8",
        "ifInOctets": "1.3.6.1.2.1.2.2.1.10",
        "ifOutOctets": "1.3.6.1.2.1.2.2.1.16",
        "ifInErrors": "1.3.6.1.2.1.2.2.1.14",
        "ifOutErrors": "1.3.6.1.2.1.2.2.1.20",
        # IF-MIB ifXTable — nome curto, contadores de 64 bits e velocidade em Mbps
        "ifName": "1.3.6.1.2.1.31.1.1.1.1",
        "ifHCInOctets": "1.3.6.1.2.1.31.1.1.1.6",
        "ifHCOutOctets": "1.3.6.1.2.1.31.1.1.1.10",
        "ifHighSpeed": "1.3.6.1.2.1.31.1.1.1.15",
    },

    # IP MIB (RFC 4293)
    "ip": {
        "ipInReceives": "1.3.6.1.2.1.4.3.0",
        "ipOutRequests": "1.3.6.1.2.1.4.10.0",
        "ipForwarding": "1.3.6.1.2.1.4.1.0",
    },

    # HOST-RESOURCES-MIB (RFC 2790) - CPU, Memória
    "host": {
        "hrProcessorLoad": "1.3.6.1.2.1.25.3.3.1.2",
        "hrMemorySize": "1.3.6.1.2.1.25.2.2.0",
        "hrStorageType": "1.3.6.1.2.1.25.2.3.1.2",
        "hrStorageDescr": "1.3.6.1.2.1.25.2.3.1.3",
        "hrStorageAllocationUnits": "1.3.6.1.2.1.25.2.3.1.4",
        "hrStorageSize": "1.3.6.1.2.1.25.2.3.1.5",
        "hrStorageUsed": "1.3.6.1.2.1.25.2.3.1.6",
    },

    # GPON / ONU - ITU-T G.988 (OMCI MIB) + Huawei Enterprise MIB
    "gpon": {
        "onuRxPower": "1.3.6.1.4.1.2011.6.128.1.1.2.51.1.4",
        "onuTxPower": "1.3.6.1.4.1.2011.6.128.1.1.2.51.1.5",
        "onuTemperature": "1.3.6.1.4.1.2011.6.128.1.1.2.51.1.2",
        "onuVoltage": "1.3.6.1.4.1.2011.6.128.1.1.2.51.1.3",
        "onuStatus": "1.3.6.1.4.1.2011.6.128.1.1.2.46.1.15",
        "onuBER": "1.3.6.1.4.1.2011.6.128.1.1.2.46.1.21",
    },

    # Wi-Fi - IEEE 802.11 MIB + vendedor
    "wifi": {
        "clients24GHz": "1.3.6.1.4.1.14988.1.1.1.3.1.6.1",
        "clients5GHz": "1.3.6.1.4.1.14988.1.1.1.3.1.6.2",
        "channel24GHz": "1.3.6.1.4.1.14988.1.1.1.3.1.4.1",
        "channel5GHz": "1.3.6.1.4.1.14988.1.1.1.3.1.4.2",
        "avgRSSI24GHz": "1.3.6.1.4.1.14988.1.1.1.3.1.2.1",
        "avgRSSI5GHz": "1.3.6.1.4.1.14988.1.1.1.3.1.2.2",
    },
}

# ===== PERFIS DE VENDOR (Descoberta Automática) =====
# Usado pelo motor de scan (app/discovery.py) para classificar um dispositivo via
# fingerprint SNMP (sysObjectID/sysDescr) e saber quais grupos de OIDs acima fazem
# sentido consultar para ele. "oid_groups" diz quais grupos o poller SNMP
# (app/snmp_poller.py) lê de cada dispositivo cadastrado com SNMP.
VENDOR_PROFILES = {
    "mikrotik": {
        "label": "MikroTik RouterOS",
        "device_type": "Router",
        "sysobjectid_prefix": "1.3.6.1.4.1.14988",
        "sysdescr_keywords": ["routeros", "mikrotik"],
        "oid_groups": ["system", "interfaces", "host", "wifi"],
    },
    "huawei_olt": {
        "label": "Huawei OLT (MA5800)",
        "device_type": "OLT",
        "sysobjectid_prefix": "1.3.6.1.4.1.2011",
        "sysdescr_keywords": ["huawei", "ma5800", "ma56"],
        "oid_groups": ["system", "gpon"],
    },
    "zte_olt": {
        "label": "ZTE OLT (ZXA10)",
        "device_type": "OLT",
        "sysobjectid_prefix": "1.3.6.1.4.1.3902",
        "sysdescr_keywords": ["zte", "zxa10"],
        "oid_groups": ["system", "gpon"],
    },
    "nokia_olt": {
        "label": "Nokia OLT (7360 FX)",
        "device_type": "OLT",
        "sysobjectid_prefix": "1.3.6.1.4.1.637",
        "sysdescr_keywords": ["nokia", "isam", "7360", "alcatel"],
        "oid_groups": ["system", "gpon"],
    },
    "linux_server": {
        "label": "Servidor Linux (net-snmp)",
        "device_type": "Server",
        "sysobjectid_prefix": "1.3.6.1.4.1.8072",
        "sysdescr_keywords": ["linux"],
        "oid_groups": ["system", "interfaces", "host"],
    },
    "windows_server": {
        "label": "Servidor Windows",
        "device_type": "Server",
        "sysobjectid_prefix": "1.3.6.1.4.1.311",
        "sysdescr_keywords": ["windows"],
        "oid_groups": ["system", "interfaces", "host"],
    },
    "generic": {
        "label": "Dispositivo SNMP genérico",
        "device_type": "Desconhecido",
        "sysobjectid_prefix": None,
        "sysdescr_keywords": [],
        "oid_groups": ["system"],
    },
}


def classify_vendor(sys_descr: str | None, sys_object_id: str | None) -> str:
    """Classifica um dispositivo descoberto via SNMP num vendor_key de VENDOR_PROFILES.
    Prioriza o sysObjectID (número de enterprise, autoritativo); usa sysDescr como
    fallback quando o sysObjectID não bate com nenhum prefixo conhecido."""
    if sys_object_id:
        for key, profile in VENDOR_PROFILES.items():
            prefix = profile["sysobjectid_prefix"]
            if prefix and sys_object_id.startswith(prefix):
                return key

    if sys_descr:
        descr_lower = sys_descr.lower()
        for key, profile in VENDOR_PROFILES.items():
            if any(kw in descr_lower for kw in profile["sysdescr_keywords"]):
                return key

    return "generic"
