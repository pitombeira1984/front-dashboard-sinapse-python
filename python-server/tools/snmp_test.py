#!/usr/bin/env python3
"""Diagnóstico SNMP contra uma ONU real. Tenta várias community strings/versões
e, se alguma responder, faz um walk do grupo "system" pra identificar o equipamento.

Uso:
  python tools/snmp_test.py [ip] [community1,community2,...]

Exemplos:
  python tools/snmp_test.py
  python tools/snmp_test.py 192.168.100.1
  python tools/snmp_test.py 192.168.100.1 public,private,linkce
"""
import sys

from pysnmp.hlapi import (
    CommunityData, ContextData, ObjectIdentity, ObjectType, SnmpEngine,
    UdpTransportTarget, getCmd, nextCmd,
)

TARGET = sys.argv[1] if len(sys.argv) > 1 else "192.168.100.1"
COMMUNITIES = [c.strip() for c in (sys.argv[2] if len(sys.argv) > 2 else
               "public,private,admin,community,snmp,linkce").split(",") if c.strip()]
VERSIONS = [("v2c", 1), ("v1", 0)]  # mpModel: 1=v2c, 0=v1

SYS_DESCR = "1.3.6.1.2.1.1.1.0"
SYSTEM_SUBTREE = "1.3.6.1.2.1.1"
TIMEOUT_S = 2


def try_combo(community: str, mp_model: int):
    engine = SnmpEngine()
    iterator = getCmd(
        engine,
        CommunityData(community, mpModel=mp_model),
        UdpTransportTarget((TARGET, 161), timeout=TIMEOUT_S, retries=0),
        ContextData(),
        ObjectType(ObjectIdentity(SYS_DESCR)),
    )
    error_indication, error_status, _error_index, var_binds = next(iterator)
    if error_indication or error_status:
        return None
    return {"engine": engine, "community": community, "mpModel": mp_model, "sysDescr": str(var_binds[0][1])}


def walk_system(community: str, mp_model: int) -> list:
    lines = []
    for error_indication, error_status, _error_index, var_binds in nextCmd(
        SnmpEngine(),
        CommunityData(community, mpModel=mp_model),
        UdpTransportTarget((TARGET, 161), timeout=TIMEOUT_S, retries=0),
        ContextData(),
        ObjectType(ObjectIdentity(SYSTEM_SUBTREE)),
        lexicographicMode=False,
    ):
        if error_indication or error_status:
            break
        for name, value in var_binds:
            lines.append(f"  {name} = {value}")
    return lines


def main() -> int:
    print(f"Testando SNMP em {TARGET}...")
    print(f"Community strings: {', '.join(COMMUNITIES)}\n")

    for community in COMMUNITIES:
        for label, mp_model in VERSIONS:
            print(f'[{label}] community="{community}" ... ', end="", flush=True)
            result = try_combo(community, mp_model)

            if not result:
                print("sem resposta")
                continue

            print("RESPONDEU!")
            print(f"  sysDescr: {result['sysDescr']}\n")

            print("Fazendo walk do grupo system (1.3.6.1.2.1.1)...")
            lines = walk_system(community, mp_model)
            print("\n".join(lines) or "  (walk não retornou nada)")

            print(f'\nSucesso: community="{community}", versão={label}')
            return 0

    print(
        "\nNenhuma combinação respondeu. Possibilidades:\n"
        "  - SNMP desabilitado no lado LAN da ONU (só liberado pra gerência remota da operadora)\n"
        "  - Community string real é diferente das testadas (peça pra outra pessoa/técnico)\n"
        "  - Firewall do Windows bloqueando a resposta UDP/161 (tente desativar temporariamente)\n"
        "  - Pode ser necessário o roteador em bridge mode sugerido pelo técnico, pra alcançar a rede de gerência"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
