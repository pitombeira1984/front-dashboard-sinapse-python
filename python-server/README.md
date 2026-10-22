# SINAPSE — Python Server

Backend + frontend server-rendered do SINAPSE, em **FastAPI** (API + engine de simulação) e **Jinja2** (páginas HTML). Serve tudo em um único processo, same-origin — sem CORS necessário entre frontend e API em produção.

## Requisitos

- Python 3.11+ (testado com 3.14)
- pip

## Instalação

```bash
cd python-server
python -m venv .venv
.venv\Scripts\activate            # Windows (PowerShell: .venv\Scripts\Activate.ps1)
# source .venv/bin/activate       # Linux/Mac
pip install -r requirements.txt
```

## Rodando localmente

```bash
uvicorn app.main:app --reload --port 8080
```

Abre em `http://127.0.0.1:8080`. A porta padrão do uvicorn (8000) não é usada porque o Windows costuma reservá-la (faixa excluída pelo Hyper-V/WSL — confira com `netsh interface ipv4 show excludedportrange protocol=tcp`), o que gera `WinError 10013` ao subir o servidor. `--reload` reinicia o processo a cada alteração de arquivo — útil em desenvolvimento, mas também **reseta todo o estado em memória** (dispositivos, alertas, histórico etc. voltam aos valores iniciais), já que não há banco de dados.

> **Atenção (Windows):** em alguns ambientes o `--reload` detecta a alteração mas o processo antigo continua respondendo com o código velho (processos `multiprocessing spawn` órfãos acumulam). Se uma mudança não aparecer, encerre todos os processos `python`/`uvicorn` do servidor e suba de novo **sem** `--reload` (comando abaixo).

JS e CSS são servidos com sufixo `?v=<versão>` (`static_version` em `app/routers/pages.py`), que muda a cada start do processo — o navegador sempre baixa a versão nova após um restart, sem precisar de Ctrl+F5.

Para simular produção (sem reload):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Acessando os dispositivos simulados (containers Docker)

Os dispositivos SNMP simulados do laboratório (`tools/lab/`) rodam como **containers** Docker — não são VMs completas: o Docker Desktop mantém uma única VM leve (WSL2) e cada dispositivo é um container dentro dela. Esta seção é o passo a passo operacional; os detalhes de arquitetura (por que cada um publica num IP diferente, como adicionar um novo) estão em [Laboratório: dispositivos SNMP simulados](#laboratório-dispositivos-snmp-simulados-docker).

Todos os comandos abaixo funcionam no **PowerShell** a partir de `python-server/tools/lab` (onde fica o `docker-compose.yml`). Com o `docker compose`, cada container é referenciado pelo **nome do serviço** (coluna "Serviço"); com o `docker` puro, pelo **nome do container** (`lab-<serviço>-1`).

| Serviço | Container | IP:porta (UDP) | Simula |
|---|---|---|---|
| `olt-sim` | `lab-olt-sim-1` | `192.168.100.26:161` (IP da LAN — ajuste `OLT_SIM_BIND`) | Huawei OLT MA5800 |
| `mikrotik-sim` | `lab-mikrotik-sim-1` | `127.0.0.2:161` | MikroTik RouterOS |
| `zte-sim` | `lab-zte-sim-1` | `127.0.0.3:161` | ZTE OLT ZXA10 |
| `nokia-sim` | `lab-nokia-sim-1` | `127.0.0.4:161` | Nokia OLT 7360 FX |
| `onu-generic-sim` | `lab-onu-generic-sim-1` | `127.0.0.5:161` | ONU/ONT OEM genérica |
| `linux-server-sim` | `lab-linux-server-sim-1` | `127.0.0.6:161` | Servidor Linux (CPU, memória, discos, interfaces) |

Community SNMP de todos: `public`.

### 1. Pré-requisitos

1. **Docker Desktop** instalado e **aberto** (ícone da baleia na bandeja do Windows parado, sem animação = engine pronta).
2. Confirme que o Docker responde:

   ```powershell
   docker version          # precisa mostrar as seções "Client" e "Server"
   ```

   Se aparecer `error during connect` / `The system cannot find the file specified`, o Docker Desktop não está rodando — abra-o e aguarde a engine iniciar.
3. Entre na pasta do laboratório:

   ```powershell
   cd "python-server\tools\lab"
   ```

### 2. Conectar (subir os dispositivos)

```powershell
# todos os dispositivos (a primeira vez faz o build da imagem — ~1 min)
docker compose up -d --build

# ou só os que você precisa
docker compose up -d --build linux-server-sim mikrotik-sim
```

`-d` roda em segundo plano (o terminal fica livre); `--build` reconstrói a imagem se o `Dockerfile` ou um dataset mudou. Os containers **não sobem sozinhos** ao reiniciar o Windows — depois de um reboot, abra o Docker Desktop e rode o comando de novo.

> **`olt-sim` publica no IP real da LAN** (`192.168.100.26` por padrão). Se a sua máquina tiver outro IP (veja com `ipconfig`), o `up` falha com `cannot assign requested address`. Defina o IP antes de subir: `$env:OLT_SIM_BIND = "<seu IP>"; docker compose up -d --build olt-sim` — ou suba os demais sem ele.

### 3. Verificar se estão no ar

```powershell
docker compose ps                     # STATUS "Up ..." = rodando
docker compose ps -a                  # inclui os parados ("Exited")
docker compose logs -f linux-server-sim   # log ao vivo (Ctrl+C sai do log, o container continua rodando)
```

Teste SNMP real a partir do host (venv **principal** do `python-server`, não de dentro do container):

```powershell
cd ..\..                              # volta para python-server
.venv\Scripts\python.exe tools\snmp_test.py 127.0.0.6 public
```

### 4. Acessar a plataforma com os dispositivos

1. Com o servidor rodando (ver [Rodando localmente](#rodando-localmente)), abra `http://127.0.0.1:8080/devices`.
2. Em **Descoberta Automática**, escaneie `127.0.0.0/24` (já vem pré-preenchido) com protocolo **SNMP v2c** — aparecem os simuladores de `127.0.0.2` a `127.0.0.6`. O `olt-sim` está na LAN: inclua `192.168.100.0/24` (ou o seu range) na faixa.
3. Clique em **Adicionar** no dispositivo desejado e confirme com **"Monitorar via SNMP"** marcado (community `public`, porta `161`).
4. Em ~30 s (`SNMP_POLL_INTERVAL`) a tabela de Dispositivos mostra CPU/memória/disco/tráfego; "Ver Métricas" abre o detalhe.

### 5. Entrar no terminal de um container

Para inspecionar um dispositivo por dentro (ver/editar o dataset, conferir processos):

```powershell
docker compose exec linux-server-sim bash
# equivalente com o docker puro:
docker exec -it lab-linux-server-sim-1 bash
```

O prompt muda para `root@<id-do-container>:/#`. Lá dentro:

- `/data/public.snmprec` — o dataset que o simulador está servindo (OID|tipo|valor).
- `ps aux` — o processo `snmpsim-command-responder` deve estar listado.

Para **sair** do terminal do container, digite `exit` (ou `Ctrl+D`). Isso só fecha o shell — o container **continua rodando**.

Para rodar um único comando sem abrir shell: `docker compose exec linux-server-sim cat /data/public.snmprec`.

> **Git Bash:** use o PowerShell para o `exec -it`. No Git Bash ele falha com `the input device is not a TTY` (prefixe com `winpty`) e converte caminhos como `/data` em `C:/Program Files/Git/data` (use `//data`).
>
> **Alterações feitas dentro do container são temporárias** — somem quando o container é recriado (`down`/`up --build`). Para mudar o comportamento de um dispositivo de forma permanente, edite `tools/lab/datasets/<nome>/public.snmprec` no host e rode `docker compose up -d --build <serviço>`.

### 6. Desconectar (parar os dispositivos)

| Objetivo | Comando | Efeito |
|---|---|---|
| Pausar um dispositivo (simular queda) | `docker compose stop linux-server-sim` | Para o container; ele deixa de responder SNMP e o SINAPSE abre o alerta **"Sem resposta SNMP"** no próximo ciclo |
| Religar o mesmo dispositivo | `docker compose start linux-server-sim` | Volta a responder; o alerta é resolvido automaticamente |
| Reiniciar | `docker compose restart linux-server-sim` | `stop` + `start` |
| Parar todos (mantendo os containers) | `docker compose stop` | Libera CPU/memória; `docker compose start` religa tudo |
| Desligar e remover tudo | `docker compose down` | Remove os containers e a rede do laboratório (as imagens ficam em cache, o próximo `up` é rápido) |
| Remover também as imagens | `docker compose down --rmi local` | Libera disco; o próximo `up --build` refaz o build |

Os dispositivos já cadastrados no SINAPSE **não são removidos** ao parar os containers — eles ficam offline (com alerta) até o container voltar, ou até você excluí-los em `/devices`. Ao terminar os testes, rode `docker compose stop` (ou `down`) para não deixar os simuladores consumindo recursos em segundo plano; fechar o Docker Desktop também para todos.

### 7. Problemas comuns

| Sintoma | Causa / solução |
|---|---|
| `docker: error during connect` | Docker Desktop fechado ou ainda iniciando — abra-o e aguarde. |
| `Bind for 127.0.0.x:161 failed: port is already allocated` | Outro container (de uma execução antiga, ver `docker ps -a`) ou o `run_olt_sim.py` já ocupa esse IP:porta — pare-o (`docker rm -f <container>` ou `Ctrl+C` no script) e suba de novo. |
| `cannot assign requested address` no `olt-sim` | `OLT_SIM_BIND` não é um IP desta máquina — ver passo 2. |
| Container em `Exited (255)` | Docker Desktop foi fechado / Windows reiniciou com ele rodando. Basta `docker compose up -d`. |
| Scan não encontra nada / dispositivo "Sem resposta SNMP" | Confira `docker compose ps` (precisa estar `Up`) e teste com `tools\snmp_test.py <ip> public`; confirme que `SNMP_COMMUNITY=public` no `.env`. |
| Mudança no dataset não aparece | O dataset é copiado para a imagem no build — rode `docker compose up -d --build <serviço>`. |

## Variáveis de ambiente

Copie `.env.example` para `.env` e preencha:

```
ONU_HOST=192.168.100.1
ONU_USERNAME=
ONU_PASSWORD=

ONU_POLLER_ENABLED=false
ONU_POLLER_ONU_ID=1
ONU_POLLER_INTERVAL=10

SNMP_COMMUNITY=public
SNMP_TIMEOUT=1.5
SNMP_RETRIES=0
SCAN_MAX_WORKERS=40
SCAN_MAX_HOSTS=1024

SNMP_POLLER_ENABLED=true
SNMP_POLL_INTERVAL=30
SNMP_POLL_MAX_WORKERS=20
```

- `ONU_HOST`/`ONU_USERNAME`/`ONU_PASSWORD` — acesso ao painel web da ONU real, usados pelo poller do servidor e pelo script `tools/onu_real_test.py`.
- `ONU_POLLER_*` — integração da ONU real ao Dashboard (ver [ONU real no Dashboard](#onu-real-no-dashboard)). `ONU_POLLER_ENABLED=false` (padrão) mantém o servidor 100% simulado; `ONU_POLLER_ONU_ID` escolhe qual ONU simulada (1–18, `mock_engine.ONU_PROFILES`) passa a receber os valores reais; `ONU_POLLER_INTERVAL` é o intervalo de leitura em segundos.
- `SNMP_COMMUNITY`/`SNMP_TIMEOUT`/`SNMP_RETRIES`/`SCAN_*` — usadas pela Descoberta Automática (`POST /api/devices/scan`); `SNMP_COMMUNITY` também é a community padrão de dispositivos cadastrados sem uma.
- `SNMP_POLLER_*`/`SNMP_POLL_*` — poller SNMP genérico (ver [Poller SNMP genérico](#poller-snmp-genérico)): liga/desliga, intervalo entre ciclos (s) e quantos dispositivos são lidos em paralelo. Timeout/retries vêm de `SNMP_TIMEOUT`/`SNMP_RETRIES`.

`PORT` também pode ser definida (usada só quando o processo é iniciado via `railway.toml`/Nixpacks em produção; localmente, passe `--port` direto para o uvicorn).

## Estrutura de pastas

```
python-server/
├── app/
│   ├── main.py                 # cria o FastAPI app, CORS, static files, registra routers
│   ├── config.py                # env vars (pydantic-settings) + allowlist de CORS
│   ├── state.py                  # estado da aplicação em memória (devices, alerts, rules,
│   │                              #   monitoring_params, maintenances, settings, history, backups)
│   ├── mock_engine.py            # simulação da topologia GPON: tick(), get_snapshot(), ONUs/OLTs
│   ├── trap_engine.py            # geração e consulta de SNMP Traps
│   ├── snapshot_cache.py         # cache de 2s do snapshot (evita recomputar por sub-rota)
│   ├── oids.py                   # OIDs SNMP + VENDOR_PROFILES (fingerprint de vendor)
│   ├── discovery.py              # scan real de rede + fingerprint SNMP (Descoberta Automática)
│   ├── snmp_poller.py            # poller SNMP genérico: system/interfaces/host de dispositivos reais
│   ├── onu_web_poller.py         # poller da ONU real via painel web (/boaform), thread de fundo
│   ├── optical_thresholds.py     # limites ópticos por tecnologia PON (GPON, XGS-PON)
│   ├── formatting.py             # datas pt-BR, uptime
│   ├── responses.py              # helper do envelope {"ok": true, ...}
│   └── routers/                  # um arquivo por área da API + páginas (ver lista abaixo)
├── templates/                    # Jinja2: base.html + uma página por rota + partials/macros.html
├── static/
│   ├── css/style.css
│   └── js/                       # polling, gráficos (Chart.js), modais + análise preditiva
│   │                              #   (regressão linear em utils.js/analysis.js, ver seção abaixo)
├── tools/
│   ├── onu_real_test.py          # diagnóstico de ONU real via login web (reusa app/onu_web_poller.py)
│   ├── snmp_test.py              # diagnóstico SNMP (community strings/versões)
│   └── lab/                      # dispositivos SNMP simulados (Docker) p/ Descoberta Automática
│       ├── Dockerfile            #   imagem genérica snmpsim-lextudio, dataset via build arg
│       ├── docker-compose.yml    #   um serviço por dispositivo simulado
│       ├── datasets/              #   um .snmprec por dispositivo simulado (olt, mikrotik,
│       │                          #   zte, nokia, onu-generic, linux-server)
│       └── run_olt_sim.py        #   alternativa sem Docker (host direto, ver seção abaixo)
├── requirements.txt
└── .env.example
```

O `railway.toml` do deploy fica na raiz do repositório (ver [Deploy](#deploy)).

## Páginas (Jinja2)

| Rota | Página |
|------|--------|
| `GET /` | Dashboard |
| `GET /devices` | Dispositivos |
| `GET /alerts` | Alertas |
| `GET /analysis` | Análise |
| `GET /settings` | Configurações |
| `GET /history` | Histórico |

## API

Todas as respostas seguem o envelope `{"ok": true/false, ...}`. Prefixo `/api`.

**Status / telemetria**
`GET /status` · `GET /device` · `GET /device/optical` · `GET /device/system` · `GET /device/wifi` · `GET /device/interfaces` · `GET /device/history` · `GET /metrics/live?port=` · `GET /alerts` (computado ao vivo) · `GET /oids`

**Traps SNMP**
`GET /traps` · `GET /traps/stats` · `GET /traps/types` · `PUT /traps/acknowledge` · `PUT /traps/acknowledge-all`

**Topologia GPON**
`GET /topology` · `GET /onus` · `GET /onus/{id}` · `GET /gpon/ports` · `GET /gpon/kpis` · `GET /olts` · `POST /olts` · `GET /olts/bandwidth`

**ONU real**
`GET /onu-real/status` (estado do poller: última leitura, último erro, `fresh`, `ageSeconds` — nunca expõe a senha)

**Clientes**
`GET /clients` · `GET /clients/{id}`

**Dispositivos (CRUD)**
`GET/POST /devices` · `PUT/DELETE /devices/{id}` · `POST /devices/scan` (Descoberta Automática, ver seção abaixo) · `POST /onus`

**Poller SNMP**
`GET /devices/{id}/snmp` (última leitura completa) · `POST /devices/{id}/snmp/poll` (leitura imediata) · `GET /snmp-poller/status`

**Alertas (persistidos)**
`GET /alerts/all` · `POST /alerts/add` · `PUT /alerts/{id}/resolve` · `DELETE /alerts/{id}`

**Regras (legado, sem UI associada — mantido por paridade de API)**
`GET/POST /rules` · `PUT /rules/{id}` · `PUT /rules/{id}/toggle` · `DELETE /rules/{id}`

**Parâmetros de Monitoramento**
`GET/POST /monitoring-params` · `PUT /monitoring-params/{id}` · `PUT /monitoring-params/{id}/toggle` · `DELETE /monitoring-params/{id}`

**Manutenções**
`GET/POST /maintenances` · `DELETE /maintenances/{id}`

**Histórico**
`GET/POST /history` · `GET /history/export.csv` · `GET /history/export.json` · `GET /history/export.pdf` (todas aceitam `?period=`)

**Backups**
`GET/POST /backups` · `POST /backups/{id}/restore` · `DELETE /backups/{id}`

**Configurações**
`GET/PUT /settings`

## Descoberta Automática (scan real de rede)

Em `/devices` → "Descoberta Automática", o botão "Escanear Rede" faz um scan **real** (não simulado) de um ou mais ranges CIDR (separados por vírgula), implementado em `app/discovery.py`:

- **SNMP** (padrão): um único GET de `sysDescr` + `sysObjectID` por host, usando a community de `SNMP_COMMUNITY`. Sem resposta dentro de `SNMP_TIMEOUT` × (`SNMP_RETRIES` + 1) ⇒ host tratado como fora do ar/sem SNMP.
- **Ping**: fallback via `ping` do próprio SO (sem precisar de socket raw/privilégio admin) — só confirma que o host está vivo, não classifica vendor.
- **Ping + SNMP**: o SNMP decide a classificação; o ping só preenche a latência exibida no card.

### Como usar (UI)

1. Abra `/devices` e vá até a seção "Descoberta Automática".
2. **Faixa de IP**: já vem pré-preenchida com **todas** as sub-redes que o próprio servidor tem (`GET /api/devices/scan/local-ranges`, uma por IP local via `socket.gethostbyname_ex` + sempre `127.0.0.0/24` para os dispositivos do laboratório — ver `discovery.local_network_ranges()`), separadas por vírgula, assumindo `/24` cada — então normalmente não precisa digitar nada. Aceita uma ou várias faixas de uma vez (`app/discovery._expand_ranges`); ajuste manualmente se quiser escanear só uma, outra máscara, ou uma faixa não detectada.
3. **Protocolo**: escolha `Ping (ICMP)`, `SNMP v2c` (padrão) ou `Ping + SNMP` — ver diferenças acima.
4. Clique em **"Escanear Rede"**. Uma barra de progresso indica o scan em andamento (paralelo, `SCAN_MAX_WORKERS` hosts por vez).
5. Cada host respondido aparece com IP, status, vendor/tipo (se SNMP) e um botão **"Adicionar"** que abre o mesmo modal "Novo Dispositivo" do botão do cabeçalho, já com Tipo/Nome/IP pré-preenchidos — revise e confirme lá. Isso garante que uma OLT/ONU encontrada no scan passe pelos mesmos endpoints (`/api/olts`, `/api/onus`) de um cadastro manual, em vez de um `POST /api/devices` genérico que não registra a OLT na topologia simulada.

Pré-requisitos para o scan encontrar dispositivos reais:

- O processo do `uvicorn` precisa ter acesso L3 até a faixa escaneada — se o servidor estiver em outra rede/VLAN dos dispositivos, eles não aparecem.
- Para classificação via SNMP, a `SNMP_COMMUNITY` do `.env` precisa bater com a community configurada nos dispositivos; caso contrário eles só aparecem usando o protocolo Ping (sem vendor/tipo).

Hosts que respondem SNMP são classificados por vendor (`VENDOR_PROFILES` em `app/oids.py`), por prefixo de `sysObjectID` (com `sysDescr` como fallback):

| Vendor | Prefixo `sysObjectID` | Tipo sugerido | Grupos de OID (`oid_groups`) |
|---|---|---|---|
| MikroTik RouterOS | `1.3.6.1.4.1.14988` | Router | `system`, `interfaces`, `host`, `wifi` |
| Huawei OLT (MA5800) | `1.3.6.1.4.1.2011` | OLT | `system`, `gpon` |
| ZTE OLT (ZXA10) | `1.3.6.1.4.1.3902` | OLT | `system`, `gpon` |
| Nokia OLT (7360 FX) | `1.3.6.1.4.1.637` | OLT | `system`, `gpon` |
| Servidor Linux (net-snmp) | `1.3.6.1.4.1.8072` | Server | `system`, `interfaces`, `host` |
| Servidor Windows | `1.3.6.1.4.1.311` | Server | `system`, `interfaces`, `host` |
| não reconhecido | — | Desconhecido | `system` |

`POST /api/devices/scan` é só leitura — "Adicionar" um resultado do scan abre o modal "Novo Dispositivo" pré-preenchido (ver "Como usar (UI)" acima), que por sua vez usa `POST /api/olts`/`POST /api/onus`/`POST /api/devices` conforme o tipo, sem duplicar lógica de criação. Com "Monitorar via SNMP" marcado no modal (padrão quando o host respondeu SNMP no scan), o dispositivo passa a ter telemetria real pelo [poller SNMP genérico](#poller-snmp-genérico); os grupos de OID sugeridos pelo `VENDOR_PROFILES` vão junto.

Concorrência: até `SCAN_MAX_WORKERS` hosts em paralelo (`ThreadPoolExecutor`, já que `pysnmp.hlapi` é síncrono), somando os hosts de **todas** as faixas passadas numa mesma chamada; se esse total passar de `SCAN_MAX_HOSTS`, a chamada é rejeitada (HTTP 400) para não travar o processo escaneando um `/8` digitado por engano.

### Laboratório: dispositivos SNMP simulados (Docker)

`tools/lab/` sobe um ou mais agentes SNMP fake via `snmpsim-lextudio`, pra testar a Descoberta Automática contra dispositivos "reais" na rede sem precisar do hardware. Hoje simula um Huawei MA5800 (`VENDOR_PROFILES["huawei_olt"]`), um MikroTik RouterOS (`VENDOR_PROFILES["mikrotik"]`), um ZTE ZXA10 (`VENDOR_PROFILES["zte_olt"]`), um Nokia 7360 FX (`VENDOR_PROFILES["nokia_olt"]`) e uma ONU/ONT OEM genérica (cai no fallback `generic`/"Desconhecido" — nenhum `sysObjectID`/`sysDescr` bate com um perfil conhecido, de propósito), cada um num container separado.

```bash
cd python-server/tools/lab
docker compose up -d --build
```

**IP do container não é alcançável do Windows.** Testado neste setup (Docker Desktop + backend WSL2): nem o bridge default nem uma rede custom com IP estático respondem a ping a partir do host — reachability de IP de container costuma depender da versão/modo de rede do Docker Desktop, então não assuma que funciona sem testar. Por isso cada serviço publica a porta `161/udp` direto num **IP que o host já possui**, em vez de depender do IP do container:

| Serviço | Publicado em | Vendor simulado |
|---|---|---|
| `olt-sim` | `192.168.100.26:161` (IP real da LAN) | Huawei OLT (MA5800) |
| `mikrotik-sim` | `127.0.0.2:161` (loopback extra) | MikroTik RouterOS |
| `zte-sim` | `127.0.0.3:161` (loopback extra) | ZTE OLT (ZXA10) |
| `nokia-sim` | `127.0.0.4:161` (loopback extra) | Nokia OLT (7360 FX) |
| `onu-generic-sim` | `127.0.0.5:161` (loopback extra) | ONU/ONT OEM genérica (`generic`/"Desconhecido") |
| `linux-server-sim` | `127.0.0.6:161` (loopback extra) | Servidor Linux net-snmp com interfaces (contadores crescendo ~48/12 Mbps na `eth0`), 4 núcleos de CPU, RAM e discos (`/var` em 93%) — alvo de teste do poller SNMP |

`192.168.100.26` é o IP real da LAN desta máquina (`ipconfig`) — ajuste `OLT_SIM_BIND` pro seu. Os `127.0.0.x` **não precisam de ajuste**: o Windows (e Linux) já responde por todo `127.0.0.0/8`, não só `127.0.0.1`, então qualquer IP nessa faixa funciona em qualquer máquina sem configurar nada (nada de `netsh`/placa extra). Como cada um está num IP diferente, dá pra escanear todos de uma vez — a faixa `127.0.0.0/24` sozinha já cobre `mikrotik-sim`, `zte-sim`, `nokia-sim` e `onu-generic-sim`; o `olt-sim` fica na LAN real (`192.168.100.0/24`). `docker compose down` derruba tudo.

**Por que container em vez do venv isolado:** `snmpsim-lextudio` arrasta `pysnmp-lextudio` 6.x como dependência, incompatível com o `pysnmp-lextudio` 5.x fixado no `requirements.txt` principal (API diferente — quebra `app/discovery.py` se instalado no mesmo venv). O container isola essa dependência sem precisar de um segundo venv no host.

**Adicionar mais um dispositivo simulado:**

1. Criar `tools/lab/datasets/<nome>/public.snmprec` (mesmo formato dos existentes — `sysDescr`/`sysObjectID` batendo com um `VENDOR_PROFILES` de `app/oids.py`; se for um vendor ainda não mapeado, adicionar um perfil novo lá primeiro, senão o scan classifica como `generic`/"Desconhecido").
2. Copiar um bloco de serviço em `docker-compose.yml`, trocando `DATASET_DIR: datasets/<nome>` e publicando num **próximo IP de loopback livre** (`127.0.0.3`, `127.0.0.4`, ...) — não dá pra publicar dois serviços na mesma porta 161 no mesmo IP, e `app/discovery.py` sempre consulta a porta 161 fixa, então "um IP por dispositivo simulado" (não portas diferentes) é o jeito de ter vários ao mesmo tempo.

O nome do arquivo (`public.snmprec`) fixa a community SNMP como `public`, batendo com o `SNMP_COMMUNITY` default do `.env.example` — mantenha esse nome a menos que troque a community nos dois lugares.

**Verificação manual de um dispositivo simulado** (sem passar pela UI): `python tools/snmp_test.py <ip> public` a partir do venv principal.

### Alternativa sem Docker: `run_olt_sim.py` no host

Se o Docker Desktop não estiver disponível, `tools/lab/public.snmprec` + `tools/lab/run_olt_sim.py` sobem o mesmo simulador direto no host Windows (só o OLT, sem o MikroTik) — não precisa de VM/Hyper-V, só escutar num IP não-loopback da própria máquina:

```bash
cd python-server/tools
python -m venv lab-venv/.venv
lab-venv\.venv\Scripts\pip install snmpsim-lextudio

# sobe o simulador (Ctrl+C pra parar)
lab-venv\.venv\Scripts\python.exe lab\run_olt_sim.py                  # 127.0.0.1:1161, padrão
lab-venv\.venv\Scripts\python.exe lab\run_olt_sim.py 192.168.100.26:161   # IP real do host (via ipconfig), porta 161
```

**Importante — venv isolado e fora de `tools/lab/`:** mesmo conflito de dependência do parágrafo acima — e crucialmente, o venv não pode ficar dentro de `tools/lab/`, porque esse diretório é o `data_dir` do simulador (escaneado recursivamente por `*.snmprec`), então um venv criado ali faz o simulador indexar os milhares de arquivos de amostra que o próprio pacote `snmpsim` instala, como se fossem dispositivos simulados extras.

`run_olt_sim.py` contorna dois bugs encontrados nessa combinação Windows + Python 3.12+/3.14 + `snmpsim-lextudio` 1.1.1 (não se aplicam ao container, que roda Linux):

- `asyncio.get_event_loop()` sem loop corrente quebra o carrier UDP — contornado criando um loop manualmente antes de chamar o responder.
- o indexador (`dbm`) monta a chave de cache concatenando `--data-dir` com `_` no lugar do separador de path; se o argumento vier com `/` (estilo Unix) em vez de `\`, gera um path quebrado no Windows. `run_olt_sim.py` usa `pathlib.Path` pra sempre passar o separador nativo.

`tools/snmp_test.py` (venv **principal**) sempre usa a porta 161 fixa — então para validar suba o simulador já na porta real (`run_olt_sim.py <ip>:161`; portas <1024 não exigem admin no Windows para bind UDP) e rode `python tools/snmp_test.py <ip> public` antes de testar pela UI. O endpoint default `127.0.0.1:1161` só serve para um teste rápido sem precisar de porta 161 livre.

## Poller SNMP genérico

`app/snmp_poller.py` lê telemetria **real** de qualquer equipamento que fale SNMP v2c com os MIBs padrão — servidores Linux/Windows, switches, roteadores, firewalls, storages e a parte de sistema/interfaces de OLTs. Uma thread de fundo (iniciada com o servidor quando `SNMP_POLLER_ENABLED=true`) consulta, a cada `SNMP_POLL_INTERVAL` segundos e em paralelo (`SNMP_POLL_MAX_WORKERS`), todos os dispositivos cadastrados com o campo `snmp`:

| Grupo (`oidGroups`) | Leitura | O que vira |
|---|---|---|
| `system` (sempre) | GET `sysDescr`, `sysObjectID`, `sysUpTime`, `sysName`, `sysLocation` | identificação e uptime |
| `interfaces` | GETBULK `ifTable` + `ifXTable` | status, velocidade, erros e **taxas em Mbps** (diferença dos contadores entre duas leituras; usa contadores de 64 bits quando o agente tem `ifXTable`, trata a volta do contador de 32 bits e ignora a leitura após reboot) |
| `host` | GETBULK `hrProcessorLoad` + `hrStorageTable` | CPU por núcleo e média, memória (`hrStorageRam`) e discos (`hrStorageFixedDisk`) com % de uso |

Tabelas que o agente não implementa voltam vazias, sem erro (ex: um roteador sem HOST-RESOURCES-MIB só mostra sistema e interfaces).

**Como cadastrar:** Dispositivos → "Novo Dispositivo" → tipo (Servidor, Roteador, Switch, Rádio ou OLT) → **"Monitorar via SNMP"** com community e porta. Ou, pela API, `POST /api/devices` (ou `/api/olts`) com:

```json
{"name": "srv-app-01", "ip": "10.0.0.20", "type": "Server",
 "snmp": {"community": "public", "port": 161, "oidGroups": ["system", "interfaces", "host"]}}
```

**O que aparece:** na tabela de Dispositivos, CPU · memória · maior uso de disco (amarelo ≥ 75%, vermelho ≥ 90%) e tráfego somado; em "Ver Métricas", o detalhe (sistema, CPU por núcleo, memória, cada disco e cada interface); "Testar Conexão" faz uma leitura SNMP imediata (`POST /api/devices/{id}/snmp/poll`). O status online/offline desses dispositivos passa a vir da resposta SNMP: sem resposta, o dispositivo fica offline e é aberto o alerta crítico **"Sem resposta SNMP — <nome>"** (inclusive na primeira tentativa); quando volta a responder, o alerta é resolvido automaticamente — ambos registrados no Histórico.

**Segurança:** a community nunca sai do servidor — `GET /api/devices`, a página Dispositivos e `GET /api/backups` devolvem `"community": "***"`. Um `PUT /api/devices/{id}` com `"community": "***"` mantém a community já cadastrada.

**Limitações atuais:**

- Só **SNMP v2c** (community em texto puro na rede). SNMPv3 (usuário + autenticação + criptografia) é o próximo passo antes de apontar para uma rede corporativa — junto com **login na própria plataforma**, que ainda não existe.
- Só MIBs padrão: OIDs proprietários (GPON por ONU nas OLTs, Wi-Fi) ainda não são lidos.
- Resultados em memória (só a última leitura; sem histórico/gráfico de longo prazo) — perdem-se no restart, como o resto do estado.
- Windows Server: o serviço SNMP é um recurso opcional obsoleto desde o 2012 R2; funciona, mas WMI/WinRM ou um agente costumam ser preferíveis.
- Os alertas são escritos pela thread do poller no mesmo estado em memória usado pelas rotas, sem lock — aceitável para o protótipo, a revisar quando houver banco de dados.

**Teste rápido com o laboratório:**

```bash
cd python-server/tools/lab
docker compose up -d --build linux-server-sim   # servidor Linux simulado em 127.0.0.6
```

Depois cadastre `127.0.0.6` como Servidor com "Monitorar via SNMP" (ou escaneie `127.0.0.0/24` e clique em "Adicionar"). A partir da 2ª leitura aparecem as taxas (~48 Mbps de entrada e ~12 Mbps de saída na `eth0`). `docker compose stop linux-server-sim` simula a queda (alerta aberto) e `start` a volta (alerta resolvido).

> **Simuladores ativos:** dois simuladores do laboratório continuam ativos — o servidor Linux em `127.0.0.6` e o MikroTik em `127.0.0.2`. Para ver funcionando, cadastre `127.0.0.6` como Servidor com SNMP, ou escaneie `127.0.0.0/24`. Para desligar:
>
> ```bash
> cd python-server/tools/lab && docker compose stop
> ```

## ONU real no Dashboard

A ONU física do laboratório não expõe SNMP; os dados vêm do **painel web** dela (servidor embarcado Boa, `/boaform`). `app/onu_web_poller.py` roda numa thread de fundo, iniciada junto com o servidor quando `ONU_POLLER_ENABLED=true`:

1. `POST http://<ONU_HOST>/boaform/admin/formLogin` com `ONU_USERNAME`/`ONU_PASSWORD`. A resposta é checada contra os marcadores de erro do próprio painel (`PW_OR_NAME_FALSE`, `LOGINED_ERROR_3`, `ANOTHER_USER_LOGINED`, `DEFAULT_PASSWD`...). O painel não usa cookie de sessão — libera o acesso pelo IP de origem.
2. A cada `ONU_POLLER_INTERVAL` segundos, `GET /boaform/getASPdata/ponGetStatus`, cuja resposta `pon_info=chave=valor&...` é convertida em modo PON, estado do link, RxPower/TxPower, temperatura, tensão, corrente bias, erros FEC/HEC e bytes.
3. Se a sessão expirar (resposta sem `pon_info=`), refaz o login no mesmo ciclo. Se o **login** falhar, espera 5 min antes de tentar de novo, para não disparar o bloqueio por tentativas do equipamento.

Integração com o restante do sistema:

- **Simulação** (`mock_engine._apply_real_reading`): a ONU de `ONU_POLLER_ONU_ID` deixa de ser simulada e recebe RxPower, TxPower, temperatura, tensão e `ponMode` reais. Latência e BER continuam simulados (o painel não os informa). Sem leitura bem-sucedida há mais de 3 intervalos, a ONU vira **offline** — gerando o mesmo alerta automático, trap `linkDown` e registro no histórico de uma queda simulada (e `linkUp` + alerta resolvido quando volta). Até a primeira tentativa terminar, a ONU segue simulada, para não gerar um "ONU Offline" falso no boot.
- **Dashboard**: card fixo **"ONU Real"** abaixo dos KPIs (independente da porta GPON selecionada), com todas as medições, selo de conexão (*Recebendo dados* / *Conectando...* / *Sem resposta* + mensagem de erro) e gráfico do RxPower real (um ponto por leitura nova, até 60). Só é renderizado quando o poller está habilitado.
- **Cards e tabela de dispositivos**: a ONU ganha o selo **REAL** e o campo `source: "real"` na API (`"mock"` nas demais).

Para usar:

```bash
# python-server/.env
ONU_POLLER_ENABLED=true
ONU_POLLER_ONU_ID=1
```

Suba o servidor e confira `GET /api/onu-real/status`. Limitações: uma ONU real por vez; **um único processo/worker** (cada worker faria seu próprio login e o painel pode recusar com "outro usuário já está logado"); os valores só avançam no resto do sistema enquanto alguma página com polling (Dashboard ou Dispositivos) estiver aberta, pois o `tick()` da simulação é disparado por request. Em produção (Railway) mantenha desligado — a ONU está na LAN local e não é alcançável da nuvem.

### Limites ópticos por tecnologia PON

`app/optical_thresholds.py` é a **fonte única** dos limites usados para avaliar cada ONU: estado `degraded` (`mock_engine`), traps `opticalDegradation` por ONU (`trap_engine`) e as cores da UI — exposto aos templates pela global Jinja `optical_color()` e ao navegador como `window.SINAPSE_OPTICAL_THRESHOLDS` (consumido por `opticalColor()`/`opticalProfile()` em `utils.js`, usados no Dashboard, em Dispositivos e na Análise). O perfil é escolhido pelo `ponMode` da ONU (`"XGS-PON"` informado pela ONU real; `"GPON"` nas simuladas).

| Grandeza | GPON (ITU-T G.984.2 B+) | XGS-PON (ITU-T G.9807.1 N1) |
|---|---|---|
| RxPower (dBm) | aviso < −24 · crítico < −27 ou > −8 | aviso < −25 ou > −10 · crítico < −28 ou > −9 |
| TxPower (dBm) | aviso < 1,0 · crítico < 0,5 ou > 5,0 | aviso < 4,5 ou > 8,5 · crítico < 4,0 ou > 9,0 |
| Temperatura (°C) | aviso > 50 · crítico > 70 | aviso > 80 · crítico > 90 |
| Tensão (V) | aviso fora de 3,1–3,5 · crítico fora de 3,0–3,6 | idem |

Os limites de temperatura do XGS-PON são valores típicos de alarme de fabricante para o DDM do módulo óptico (ONTs XGS-PON operam normalmente na faixa de 60–75 °C) — confirme no datasheet do equipamento. Os KPIs agregados do Dashboard e os Parâmetros de Monitoramento (configuráveis pelo operador em `/alerts`) **não** usam esta tabela.

## Scripts de diagnóstico

Standalone, não integrados nas rotas HTTP — usados só para investigar hardware real:

```bash
python tools/snmp_test.py [ip] [community1,community2,...]
python tools/onu_real_test.py [--watch]
```

### `onu_real_test.py` — leitura da ONU real

Faz login em `http://<ONU_HOST>/boaform/admin/formLogin` com as credenciais do `.env` e consulta `/boaform/getASPdata/ponGetStatus`. Esse equipamento não usa SNMP (não exposto ao cliente) nem cookie de sessão — o painel controla acesso pelo IP de origem, então o script só verifica ausência de marcadores de erro conhecidos na resposta. Usa as mesmas funções de login/leitura do poller do servidor (`app/onu_web_poller.py`). Se o servidor estiver rodando com o poller ligado, evite rodar o script ao mesmo tempo (dois logins simultâneos no painel).

Rode a partir de `python-server/` com o venv já criado (ver Instalação) e `ONU_HOST`/`ONU_USERNAME`/`ONU_PASSWORD` preenchidos no `.env`:

```bash
# consulta única
.venv\Scripts\python.exe tools\onu_real_test.py

# transmite os dados para o terminal continuamente (a cada 5s, Ctrl+C para sair)
.venv\Scripts\python.exe tools\onu_real_test.py --watch
```

Com o venv ativado (`.venv\Scripts\Activate.ps1`), pode-se usar só `python` no lugar do caminho completo. Cada leitura imprime modo PON, status de conexão, RxPower/TxPower (dBm), temperatura (°C), tensão (V), corrente de polarização (mA) e erros FEC/HEC.

## Análise preditiva (client-side)

A página `/analysis` calcula tendências e projeta prazos direto no navegador — não há endpoint de previsão no backend, o FastAPI só fornece o histórico bruto (`GET /api/device/history`, `GET /api/olts/bandwidth`, `GET /api/alerts/all`).

- **`static/js/utils.js`** — `linearRegression(values)`: regressão linear simples por mínimos quadrados, usando o índice da amostra como eixo X (assume amostras igualmente espaçadas no tempo). Retorna `{ slope, intercept, r2 }`.
- **`static/js/analysis.js`** — `runPredictiveAnalysis()`: chama `linearRegression()` para três séries, cada uma com seu próprio limiar de "confiança" (`r2` mínimo) e inclinação (`slope` mínima) para virar uma predição:
  - **RxPower por ONU** (`history.onuRxHistory`): alerta se a tendência é de queda (`slope < -0.003`, `r2 ≥ 0.35`) e projeta quando o sinal cruza o limite de aviso ou o crítico da tecnologia da ONU (GPON: -24/-27 dBm; XGS-PON: -25/-28 dBm — ver [Limites ópticos](#limites-ópticos-por-tecnologia-pon)).
  - **Tráfego de entrada da OLT-01** (`history.traffic`): alerta se está em crescimento (`slope > 0.01`, `r2 ≥ 0.3`) e projeta quando atinge 85% da capacidade da OLT.
  - **Latência média da rede** (`history.latency`): alerta se está em alta (`slope > 0.002`, `r2 ≥ 0.3`) e projeta quando atinge o limiar padrão (`MONITORING_PARAM_TYPES.latencyHigh`).

  A quantidade de amostras consideradas (`lookback`) varia com o período selecionado na UI (`_lookbackForRange`: 20 para 24h, 60 para 7d, 120 para o restante); predições exigem no mínimo 12 amostras e um prazo estimado ≤ 90 dias, senão são descartadas. O `r2` também vira a `confidence` (%) exibida em cada card de previsão.

## Estado e persistência

Não há banco de dados: todo o estado (dispositivos, alertas, histórico, backups, parâmetros de monitoramento, manutenções, configurações) vive em memória no processo e **se perde a cada restart** — mesmo comportamento do protótipo original em Node. A simulação da topologia GPON (`mock_engine.py`) avança em tempo real a cada request (`tick()` baseado no tempo decorrido desde a última chamada), não em um timer fixo de fundo. As exceções são os dois pollers, cada um em sua thread: o da ONU real (leitura aplicada à ONU mapeada no próximo `tick()`) e o poller SNMP genérico (resultados guardados no próprio módulo e mesclados aos dispositivos na leitura pela API, via `snmp_poller.public_device()`).

O intervalo de polling do frontend vem de Configurações → Monitoramento (padrão **5 segundos**) e controla a atualização do Dashboard, de Dispositivos e dos SNMP Traps.

## Deploy

O `railway.toml` que realmente controla o deploy fica na **raiz do repositório** (não neste diretório) — o Nixpacks precisa de um `requirements.txt` na raiz para detectar o projeto como Python; ele só referencia (`-r python-server/requirements.txt`) as dependências reais, que ficam aqui.
