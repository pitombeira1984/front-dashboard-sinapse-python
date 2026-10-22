from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    port: int = 3000
    onu_host: str = "192.168.100.1"
    onu_username: str = ""
    onu_password: str = ""
    onu_poller_enabled: bool = False
    onu_poller_onu_id: int = 1
    onu_poller_interval: float = 10.0

    snmp_community: str = "public"
    snmp_timeout: float = 1.5
    snmp_retries: int = 0
    scan_max_workers: int = 40
    scan_max_hosts: int = 1024

    snmp_poller_enabled: bool = True
    snmp_poll_interval: float = 30.0
    snmp_poll_max_workers: int = 20


settings = Settings()

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://pitombeira1984.github.io",
    "https://front-dashboard-sinapse-production.up.railway.app",
]
