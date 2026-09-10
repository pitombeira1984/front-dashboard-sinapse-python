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
uvicorn app.main:app --reload
```

Abre em `http://127.0.0.1:8000`. `--reload` reinicia o processo a cada alteração de arquivo — útil em desenvolvimento, mas também **reseta todo o estado em memória** (dispositivos, alertas, histórico etc. voltam aos valores iniciais), já que não há banco de dados.

Para simular produção (sem reload):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Variáveis de ambiente

Copie `.env.example` para `.env` e preencha:

```
ONU_HOST=192.168.100.1
ONU_USERNAME=
ONU_PASSWORD=

SNMP_COMMUNITY=public
SNMP_TIMEOUT=1.5
SNMP_RETRIES=0
SCAN_MAX_WORKERS=40
SCAN_MAX_HOSTS=1024
```

- `ONU_*` — usadas só pelo script de diagnóstico `tools/onu_real_test.py` (não pelo servidor principal, que sempre roda em modo mock).
- `SNMP_*`/`SCAN_*` — usadas pelo servidor principal na Descoberta Automática (`POST /api/devices/scan`, ver seção abaixo).

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
│   ├── formatting.py             # datas pt-BR, uptime
│   ├── responses.py              # helper do envelope {"ok": true, ...}
│   └── routers/                  # um arquivo por área da API + páginas (ver lista abaixo)
├── templates/                    # Jinja2: base.html + uma página por rota + partials/macros.html
├── static/
│   ├── css/style.css
│   └── js/                       # polling, gráficos (Chart.js), modais + análise preditiva
│   │                              #   (regressão linear em utils.js/analysis.js, ver seção abaixo)
├── tools/
│   ├── onu_real_test.py          # diagnóstico de ONU real via login web
│   ├── snmp_test.py              # diagnóstico SNMP (community strings/versões)
│   └── lab/                      # dispositivos SNMP simulados (Docker) p/ Descoberta Automática
│       ├── Dockerfile            #   imagem genérica snmpsim-lextudio, dataset via build arg
│       ├── docker-compose.yml    #   um serviço por dispositivo simulado
│       ├── datasets/              #   um .snmprec por dispositivo simulado (olt, mikrotik,
│       │                          #   zte, nokia, onu-generic)
│       └── run_olt_sim.py        #   alternativa sem Docker (host direto, ver seção abaixo)
├── requirements.txt
├── .env.example
└── railway.toml                  # referência — o railway.toml real fica na raiz do repo
```

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

**Clientes**
`GET /clients` · `GET /clients/{id}`

**Dispositivos (CRUD)**
`GET/POST /devices` · `PUT/DELETE /devices/{id}` · `POST /devices/scan` (Descoberta Automática, ver seção abaixo) · `POST /onus`

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
| não reconhecido | — | Desconhecido | `system` |

`POST /api/devices/scan` é só leitura — "Adicionar" um resultado do scan abre o modal "Novo Dispositivo" pré-preenchido (ver "Como usar (UI)" acima), que por sua vez usa `POST /api/olts`/`POST /api/onus`/`POST /api/devices` conforme o tipo, sem duplicar lógica de criação. A telemetria do dispositivo, depois de adicionado, continua vindo do `mock_engine.py`; ainda não há um poller SNMP real substituindo os valores simulados.

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

## Scripts de diagnóstico

Standalone, não integrados nas rotas HTTP — usados só para investigar hardware real:

```bash
python tools/snmp_test.py [ip] [community1,community2,...]
python tools/onu_real_test.py [--watch]
```

### `onu_real_test.py` — leitura da ONU real

Faz login em `http://<ONU_HOST>/boaform/admin/formLogin` com as credenciais do `.env` e consulta `/boaform/getASPdata/ponGetStatus`. Esse equipamento não usa SNMP (não exposto ao cliente) nem cookie de sessão — o painel controla acesso pelo IP de origem, então o script só verifica ausência de marcadores de erro conhecidos na resposta.

Rode a partir de `python-server/` com o venv já criado (ver Instalação) e `ONU_HOST`/`ONU_USERNAME`/`ONU_PASSWORD` preenchidos no `.env`:

```bash
# consulta única
.venv\Scripts\python.exe tools\onu_real_test.py

# transmite os dados para o terminal continuamente (a cada 5s, Ctrl+C para sair)
.venv\Scripts\python.exe tools\onu_real_test.py --watch
```

Com o venv ativado (`.venv\Scripts\Activate.ps1`), pode-se usar só `python` no lugar do caminho completo. Cada leitura imprime modo PON, status de conexão, RxPower/TxPower (dBm), temperatura (°C), tensão (V), corrente de polarização (mA) e erros FEC/HEC.

## Análise preditiva (client-side)

A página `/analysis` calcula tendências e projeta prazos direto no navegador — não há endpoint de previsão no backend, o FastAPI só fornece o histórico bruto (`GET /api/history`, `GET /api/olts/bandwidth`, `GET /api/alerts`).

- **`static/js/utils.js`** — `linearRegression(values)`: regressão linear simples por mínimos quadrados, usando o índice da amostra como eixo X (assume amostras igualmente espaçadas no tempo). Retorna `{ slope, intercept, r2 }`.
- **`static/js/analysis.js`** — `runPredictiveAnalysis()`: chama `linearRegression()` para três séries, cada uma com seu próprio limiar de "confiança" (`r2` mínimo) e inclinação (`slope` mínima) para virar uma predição:
  - **RxPower por ONU** (`history.onuRxHistory`): alerta se a tendência é de queda (`slope < -0.003`, `r2 ≥ 0.35`) e projeta quando o sinal cruza -24 dBm (warning) ou -27 dBm (critical).
  - **Tráfego de entrada da OLT-01** (`history.traffic`): alerta se está em crescimento (`slope > 0.01`, `r2 ≥ 0.3`) e projeta quando atinge 85% da capacidade da OLT.
  - **Latência média da rede** (`history.latency`): alerta se está em alta (`slope > 0.002`, `r2 ≥ 0.3`) e projeta quando atinge o limiar padrão (`MONITORING_PARAM_TYPES.latencyHigh`).

  A quantidade de amostras consideradas (`lookback`) varia com o período selecionado na UI (`_lookbackForRange`: 20 para 24h, 60 para 7d, 120 para o restante); predições exigem no mínimo 12 amostras e um prazo estimado ≤ 90 dias, senão são descartadas. O `r2` também vira a `confidence` (%) exibida em cada card de previsão.

## Estado e persistência

Não há banco de dados: todo o estado (dispositivos, alertas, histórico, backups, parâmetros de monitoramento, manutenções, configurações) vive em memória no processo e **se perde a cada restart** — mesmo comportamento do protótipo original em Node. A simulação da topologia GPON (`mock_engine.py`) avança em tempo real a cada request (`tick()` baseado no tempo decorrido desde a última chamada), não em um timer fixo de fundo.

## Deploy

O `railway.toml` que realmente controla o deploy fica na **raiz do repositório** (não neste diretório) — o Nixpacks precisa de um `requirements.txt` na raiz para detectar o projeto como Python; ele só referencia (`-r python-server/requirements.txt`) as dependências reais, que ficam aqui.
