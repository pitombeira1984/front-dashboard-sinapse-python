// ===== UTILITÁRIOS COMPARTILHADOS =====

// ===== CATÁLOGO DE TIPOS DE PARÂMETRO DE MONITORAMENTO =====
// Espelha state.MONITORING_PARAM_TYPES (app/state.py) — usado pelo modal de
// parâmetros (alerts.js) e pelo limiar de latência da análise preditiva (analysis.js).
const MONITORING_PARAM_TYPES = {
    opticalDegradation: { label: 'Sinal Óptico (RxPower)', icon: 'fa-satellite-dish', hasThreshold: true, operator: '<', unit: 'dBm', defaultThreshold: -24, defaultSeverity: 'critical', description: 'Dispara quando RxPower cai abaixo do limiar. Valor típico de operação: acima de -22 dBm.', dataKey: 'avgRxPower' },
    highTemperature:    { label: 'Temperatura Alta', icon: 'fa-thermometer-full', hasThreshold: true, operator: '>', unit: '°C', defaultThreshold: 65, defaultSeverity: 'warning', description: 'Dispara quando a temperatura interna ultrapassa o limiar operacional.', dataKey: 'temperature' },
    highCPU:             { label: 'CPU Alta', icon: 'fa-microchip', hasThreshold: true, operator: '>', unit: '%', defaultThreshold: 80, defaultSeverity: 'warning', description: 'Dispara quando a utilização de CPU ultrapassa o limiar por tempo configurado.', dataKey: 'cpu' },
    latencyHigh:         { label: 'Latência Alta', icon: 'fa-clock', hasThreshold: true, operator: '>', unit: 'ms', defaultThreshold: 50, defaultSeverity: 'warning', description: 'Dispara quando a latência média das ONUs supera o limiar configurado.', dataKey: 'avgLatency' },
    onuOffline:          { label: 'ONU Offline', icon: 'fa-network-wired', hasThreshold: false, defaultSeverity: 'critical', description: 'Dispara quando uma ou mais ONUs passam para o estado offline.', dataKey: 'onusOnline' },
    linkDown:            { label: 'Link Down', icon: 'fa-unlink', hasThreshold: false, defaultSeverity: 'critical', description: 'Dispara quando uma interface de rede fica inativa (via SNMP Trap).', dataKey: null },
    highBandwidth:       { label: 'Saturação de Banda', icon: 'fa-tachometer-alt', hasThreshold: true, operator: '>', unit: '%', defaultThreshold: 85, defaultSeverity: 'warning', description: 'Dispara quando a utilização de banda supera o limiar configurado.', dataKey: 'bandwidthPercent' },
    authenticationFailure: { label: 'Falha de Autenticação SNMP', icon: 'fa-shield-alt', hasThreshold: false, defaultSeverity: 'critical', description: 'Dispara quando ocorre falha de autenticação SNMP (via Trap).', dataKey: null },
};

// ===== LIMITES ÓPTICOS POR TECNOLOGIA PON =====
// Tabela vem do servidor (app/optical_thresholds.py, via window.SINAPSE_OPTICAL_THRESHOLDS
// em base.html) — mesma lógica de optical_thresholds.level() no Python.
function opticalProfile(ponMode) {
    const table = window.SINAPSE_OPTICAL_THRESHOLDS || {};
    return (ponMode && ponMode.toUpperCase().includes('XGS') ? table['XGS-PON'] : table['GPON']) || {};
}

function opticalLevel(metric, value, ponMode) {
    if (value == null || isNaN(value)) return null;
    const t = opticalProfile(ponMode)[metric];
    if (!t) return null;
    if (value < (t.critLow ?? -Infinity) || value > (t.critHigh ?? Infinity)) return 'crit';
    if (value < (t.warnLow ?? -Infinity) || value > (t.warnHigh ?? Infinity)) return 'warn';
    return 'ok';
}

function opticalColor(metric, value, ponMode, fallback = 'var(--text-primary)') {
    return { crit: 'var(--danger-color)', warn: 'var(--warning-color)', ok: 'var(--success-color)' }[opticalLevel(metric, value, ponMode)] || fallback;
}

// Espelha o macro Jinja2 device_cards (templates/partials/macros.html) — usado para
// re-renderizar o grid de dispositivos do Dashboard a cada ciclo de polling (5s),
// já que a versão inicial da página é montada pelo servidor mas as atualizações
// seguintes continuam vindo por fetch, como no app original.
function renderDeviceCards(devices, advancedMetrics) {
    if (!devices || !devices.length) return `<div style="color:var(--text-muted);padding:1.5rem;text-align:center;grid-column:1/-1;">Nenhum dispositivo encontrado.</div>`;
    return devices.map(d => {
        const rxColor = opticalColor('rxPower', d.rxPower, d.ponMode);
        return `
        <div class="device-card">
            <div class="device-header">
                <div class="device-name">${d.name}${d.source === 'real' ? ' <span class="badge badge-success" style="font-size:0.6rem;padding:0.1rem 0.45rem;vertical-align:middle;" title="Dados lidos do painel web da ONU física">REAL</span>' : ''}</div>
                <div class="device-status status-${d.status}">
                    <i class="fas fa-circle"></i>
                    <span>${d.status === 'online' ? 'Online' : 'Offline'}</span>
                </div>
            </div>
            <div style="color:var(--text-secondary);font-size:0.875rem;">IP: ${d.ip} • ${d.type}${d.port ? ' • ' + d.port : ''}</div>
            <div class="device-metrics">
                ${d.type === 'OLT' ? `
                    <div class="metric"><div class="metric-label">CPU</div><div class="metric-value">${d.cpu ?? '--'}%</div></div>
                    <div class="metric"><div class="metric-label">Memória</div><div class="metric-value">${d.memory ?? '--'}%</div></div>
                    <div class="metric"><div class="metric-label">Temp.</div><div class="metric-value">${d.temperature ?? '--'}°C</div></div>
                    <div class="metric"><div class="metric-label">ONUs Ativas</div><div class="metric-value">${d.onus_active ?? '--'}/${d.onus_total ?? '--'}</div></div>
                ` : d.type === 'ONU' ? (() => {
                    const txColor  = opticalColor('txPower', d.txPower, d.ponMode);
                    const sfpColor = opticalColor('temperature', d.sfpTemp, d.ponMode);
                    const vColor   = opticalColor('voltage', d.sfpVoltage, d.ponMode);
                    const berColor = d.ber !== undefined ? (d.ber > 1e-6 ? 'var(--danger-color)' : d.ber > 1e-9 ? 'var(--warning-color)' : 'var(--success-color)') : 'var(--text-primary)';
                    const berFmt   = v => v === undefined ? '--' : Number(v).toExponential(2);
                    return `
                    <div class="metric"><div class="metric-label">RxPower</div><div class="metric-value" style="color:${rxColor};">${d.status === 'online' ? (d.rxPower ?? '--') + ' dBm' : '--'}</div></div>
                    <div class="metric"><div class="metric-label">TxPower</div><div class="metric-value" style="color:${txColor};">${d.status === 'online' ? (d.txPower ?? '--') + ' dBm' : '--'}</div></div>
                    ${advancedMetrics ? `
                    <div class="metric"><div class="metric-label">Temp. SFP</div><div class="metric-value" style="color:${sfpColor};">${d.status === 'online' ? (d.sfpTemp ?? '--') + ' °C' : '--'}</div></div>
                    <div class="metric"><div class="metric-label">Tensão SFP</div><div class="metric-value" style="color:${vColor};">${d.status === 'online' ? (d.sfpVoltage ?? '--') + ' V' : '--'}</div></div>
                    <div class="metric"><div class="metric-label">BER</div><div class="metric-value" style="color:${berColor};font-size:0.8rem;">${d.status === 'online' ? berFmt(d.ber) : '--'}</div></div>
                    <div class="metric"><div class="metric-label">Uptime SFP</div><div class="metric-value" style="font-size:0.75rem;">${d.status === 'online' ? (d.uptime ?? '--') : '--'}</div></div>
                    ` : ''}
                    <div class="metric"><div class="metric-label">Latência</div><div class="metric-value">${d.status === 'online' ? (d.latency ?? '--') + ' ms' : '--'}</div></div>
                    <div class="metric"><div class="metric-label">Distância</div><div class="metric-value">${d.distance ?? '--'}</div></div>
                    <div class="metric metric-cliente"><div class="metric-label">Cliente</div><div class="metric-value" style="font-size:0.75rem;display:flex;align-items:center;gap:0.4rem;">${d.client ?? '--'}${d.id ? `<button class="client-info-btn" onclick="openClientDrawer(${d.id})" title="Ver informações do cliente"><i class="fas fa-info-circle"></i></button>` : ''}</div></div>`;
                })() : d.type === 'Router' ? `
                    <div class="metric"><div class="metric-label">Tráfego IN</div><div class="metric-value">${d.traffic_in ?? '--'} Mbps</div></div>
                    <div class="metric"><div class="metric-label">Tráfego OUT</div><div class="metric-value">${d.traffic_out ?? '--'} Mbps</div></div>
                    <div class="metric"><div class="metric-label">Pacotes/s</div><div class="metric-value">${(d.packets || 0).toLocaleString()}</div></div>
                    <div class="metric"><div class="metric-label">Uptime</div><div class="metric-value">${d.uptime || '-'}</div></div>
                ` : ''}
            </div>
        </div>`;
    }).join('');
}

function updateTime() {
    const now = new Date();
    const timeEl   = document.getElementById('current-time');
    const updateEl = document.getElementById('data-update');
    const timeString = now.toLocaleTimeString('pt-BR');
    const dateString = now.toLocaleDateString('pt-BR');
    if (timeEl)   timeEl.textContent = timeString;
    if (updateEl) updateEl.textContent = `Última atualização: ${dateString} ${timeString}`;
}

// ----- Toast -----
function showToast(message, type = 'success') {
    const existing = document.getElementById('sinapse-toast');
    if (existing) existing.remove();

    const colors = { success: 'var(--success-color)', warning: 'var(--warning-color)', error: 'var(--danger-color)', info: 'var(--secondary-color)' };
    const icons  = { success: 'fa-check-circle', warning: 'fa-exclamation-triangle', error: 'fa-times-circle', info: 'fa-info-circle' };

    if (!document.getElementById('toast-style')) {
        const s = document.createElement('style');
        s.id = 'toast-style';
        s.textContent = `
            @keyframes toastIn  { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
            @keyframes toastOut { from { opacity:1; transform:translateY(0);    } to { opacity:0; transform:translateY(12px); } }
        `;
        document.head.appendChild(s);
    }

    const toast = document.createElement('div');
    toast.id = 'sinapse-toast';
    toast.style.cssText = `
        position:fixed; bottom:2rem; right:2rem; z-index:199;
        background:var(--bg-card); border:1px solid var(--border-color);
        border-left:4px solid ${colors[type] || colors.success};
        border-radius:8px; padding:1rem 1.25rem;
        display:flex; align-items:center; gap:0.75rem;
        color:var(--text-primary); font-size:0.9rem; font-weight:500;
        box-shadow:0 8px 24px rgba(0,0,0,0.4);
        animation:toastIn 0.3s ease; max-width:400px;
    `;
    toast.innerHTML = `<i class="fas ${icons[type] || icons.success}" style="color:${colors[type]};font-size:1.1rem;"></i><span>${message}</span>`;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'toastOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ----- Modal -----
let _modalDestroy = null;

function openModal(title, content, confirmText, confirmCallback) {
    if (_modalDestroy) _modalDestroy();

    document.getElementById('modal-title').textContent   = title;
    document.getElementById('modal-body').innerHTML      = content;
    document.getElementById('modal-confirm').textContent = confirmText;
    document.getElementById('modal').style.display       = 'flex';

    const modal      = document.getElementById('modal');
    const closeBtn   = document.getElementById('close-modal');
    const cancelBtn  = document.getElementById('modal-cancel');
    const confirmBtn = document.getElementById('modal-confirm');

    const destroy = () => {
        _modalDestroy = null;
        modal.style.display = 'none';
        closeBtn.removeEventListener('click', destroy);
        cancelBtn.removeEventListener('click', destroy);
        confirmBtn.removeEventListener('click', onConfirm);
        modal.removeEventListener('click', onOutside);
    };
    const onConfirm = () => { if (confirmCallback) confirmCallback(); };
    const onOutside = (e) => { if (e.target === modal) destroy(); };

    closeBtn.addEventListener('click', destroy);
    cancelBtn.addEventListener('click', destroy);
    confirmBtn.addEventListener('click', onConfirm);
    modal.addEventListener('click', onOutside);

    _modalDestroy = destroy;
}

function closeModal() {
    if (_modalDestroy) _modalDestroy();
    else document.getElementById('modal').style.display = 'none';
}

// ----- Escape HTML -----
function escHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// ----- Análise preditiva: regressão linear simples (mínimos quadrados) -----
function linearRegression(values) {
    const n = values.length;
    if (n < 2) return { slope: 0, intercept: values[0] || 0, r2: 0 };
    const xMean = (n - 1) / 2;
    const yMean = values.reduce((a, b) => a + b, 0) / n;
    let num = 0, den = 0;
    for (let i = 0; i < n; i++) { num += (i - xMean) * (values[i] - yMean); den += (i - xMean) ** 2; }
    const slope = den === 0 ? 0 : num / den;
    const intercept = yMean - slope * xMean;
    let ssTot = 0, ssRes = 0;
    for (let i = 0; i < n; i++) { const pred = slope * i + intercept; ssRes += (values[i] - pred) ** 2; ssTot += (values[i] - yMean) ** 2; }
    const r2 = ssTot === 0 ? 0 : Math.max(0, 1 - ssRes / ssTot);
    return { slope, intercept, r2 };
}

function formatDuration(seconds) {
    if (seconds < 60) return `${Math.max(1, Math.round(seconds))}s`;
    const minutes = seconds / 60;
    if (minutes < 60) return `${Math.round(minutes)} min`;
    const hours = minutes / 60;
    if (hours < 48) return `${hours.toFixed(1)} h`;
    return `${(hours / 24).toFixed(1)} dias`;
}

// ----- Exportação (delega para os endpoints do servidor) -----
function exportData(format, period, type = 'history') {
    if (type !== 'history') return;
    const qs = `?period=${encodeURIComponent(period)}`;
    if (format === 'pdf') {
        window.open(`/api/history/export.pdf${qs}`, '_blank');
    } else {
        window.location.href = `/api/history/export.${format}${qs}`;
    }
}

// ----- Aplicação de configurações em tempo de execução -----
// Converte o intervalo de polling salvo em Configurações para milissegundos.
function _pollingIntervalToMs(label) {
    const map = { '5 segundos': 5000, '1 minuto': 60000, '5 minutos': 300000, '10 minutos': 600000, '15 minutos': 900000 };
    return map[label] !== undefined ? map[label] : 5000;
}

// Aplica o intervalo real de polling salvo em Configurações — chamada uma vez ao
// carregar qualquer página com polling ativo (sidebar/rodapé já vêm corretos do
// servidor, renderizados no HTML inicial).
function applyPollingIntervalFromSettings(pollingIntervalLabel) {
    if (typeof API !== 'undefined') API.POLL_INTERVAL = _pollingIntervalToMs(pollingIntervalLabel);
}

// ===== MODAL — ADICIONAR DISPOSITIVO (usado no Dashboard e em Dispositivos) =====
function updateDeviceFormFields() {
    const type = document.getElementById('new-device-type')?.value;
    const oltSection     = document.getElementById('new-device-olt-fields');
    const onuSection     = document.getElementById('new-device-onu-fields');
    const genericSection = document.getElementById('new-device-generic-fields');
    if (oltSection)     oltSection.style.display     = type === 'OLT' ? '' : 'none';
    if (onuSection)     onuSection.style.display     = type === 'ONU' ? '' : 'none';
    if (genericSection) genericSection.style.display = (type !== 'OLT' && type !== 'ONU') ? '' : 'none';
}

function openAddDeviceModal(onDone, prefill) {
    const type = prefill?.type || 'OLT';
    const opt = (value, label) => `<option value="${value}"${type === value ? ' selected' : ''}>${label}</option>`;
    openModal('Adicionar Novo Dispositivo', `
        <div class="form-group">
            <label class="form-label">Tipo de Dispositivo</label>
            <select class="form-control" id="new-device-type" onchange="updateDeviceFormFields()">
                ${opt('OLT', 'OLT (GPON/XGS-PON)')}
                ${opt('ONU', 'ONU (Terminal de Assinante)')}
                ${opt('Router', 'Roteador')}
                ${opt('Switch', 'Switch Gerenciável')}
                ${opt('Radio', 'Rádio Wireless')}
            </select>
        </div>

        <div id="new-device-olt-fields">
            <div class="form-group">
                <label class="form-label">Nome / ID *</label>
                <input type="text" class="form-control" id="olt-name" placeholder="Ex: OLT-04" value="${escHtml(type === 'OLT' ? (prefill?.name || '') : '')}">
            </div>
            <div class="form-group">
                <label class="form-label">Endereço IP *</label>
                <input type="text" class="form-control" id="olt-ip" placeholder="Ex: 10.0.4.10" value="${escHtml(type === 'OLT' ? (prefill?.ip || '') : '')}">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">Fabricante</label>
                    <select class="form-control" id="olt-vendor">
                        <option>Huawei</option><option>ZTE</option><option>Nokia</option><option>Fiberhome</option><option>Datacom</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Modelo</label>
                    <input type="text" class="form-control" id="olt-model" placeholder="Ex: MA5800-X2">
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">Localização (POP)</label>
                <input type="text" class="form-control" id="olt-location" placeholder="Ex: POP Bairro Leste">
            </div>
            <div class="form-group">
                <label class="form-label">Capacidade (Mbps)</label>
                <input type="number" class="form-control" id="olt-capacity" value="2500" min="100">
            </div>
        </div>

        <div id="new-device-onu-fields" style="display:none;">
            <div class="form-group">
                <label class="form-label">Porta GPON *</label>
                <select class="form-control" id="onu-gpon-port">
                    <option value="">Carregando portas...</option>
                </select>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">Apto / Unidade *</label>
                    <input type="text" class="form-control" id="onu-apt" placeholder="Ex: Apto 401">
                </div>
                <div class="form-group">
                    <label class="form-label">Endereço IP</label>
                    <input type="text" class="form-control" id="onu-ip" placeholder="Ex: 10.0.1.110">
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">Nome do Cliente</label>
                <input type="text" class="form-control" id="onu-client" placeholder="Ex: José Alves">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">Serial ONU</label>
                    <input type="text" class="form-control" id="onu-serial" placeholder="Ex: HW-ONU-000019">
                </div>
                <div class="form-group">
                    <label class="form-label">Modelo</label>
                    <select class="form-control" id="onu-model">
                        <option value="HG8245Q2">HG8245Q2 (Huawei)</option>
                        <option value="F660">F660 (ZTE)</option>
                        <option value="G-010G-T">G-010G-T (Nokia)</option>
                    </select>
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">Distância da OLT (km)</label>
                <input type="number" class="form-control" id="onu-distance" value="0.5" step="0.1" min="0.1" max="20">
            </div>
        </div>

        <div id="new-device-generic-fields" style="display:none;">
            <div class="form-group">
                <label class="form-label">Nome do Dispositivo *</label>
                <input type="text" class="form-control" id="generic-name" placeholder="Ex: Switch Sala 03" value="${escHtml(type !== 'OLT' && type !== 'ONU' ? (prefill?.name || '') : '')}">
            </div>
            <div class="form-group">
                <label class="form-label">Endereço IP *</label>
                <input type="text" class="form-control" id="generic-ip" placeholder="Ex: 10.0.1.50" value="${escHtml(type !== 'OLT' && type !== 'ONU' ? (prefill?.ip || '') : '')}">
            </div>
            <div class="form-group">
                <label class="form-label">Comunidade SNMP</label>
                <input type="text" class="form-control" id="device-snmp" value="public">
            </div>
        </div>
    `, 'Adicionar', async () => {
        const type = document.getElementById('new-device-type')?.value;

        if (type === 'OLT') {
            const ip       = document.getElementById('olt-ip')?.value?.trim();
            const name     = document.getElementById('olt-name')?.value?.trim();
            const vendor   = document.getElementById('olt-vendor')?.value;
            const model    = document.getElementById('olt-model')?.value?.trim();
            const location = document.getElementById('olt-location')?.value?.trim();
            const capacity = document.getElementById('olt-capacity')?.value;
            if (!ip) { showToast('Preencha o endereço IP da OLT.', 'warning'); return; }
            await API.addOLT({ name: name || undefined, ip, vendor, model, location, capacity });
            showToast('OLT adicionada ao monitoramento!', 'success');

        } else if (type === 'ONU') {
            const gponPort = document.getElementById('onu-gpon-port')?.value;
            const apt      = document.getElementById('onu-apt')?.value?.trim();
            const ip       = document.getElementById('onu-ip')?.value?.trim();
            const client   = document.getElementById('onu-client')?.value?.trim();
            const serial   = document.getElementById('onu-serial')?.value?.trim();
            const model    = document.getElementById('onu-model')?.value;
            const distance = document.getElementById('onu-distance')?.value;
            if (!gponPort) { showToast('Selecione a Porta GPON.', 'warning'); return; }
            if (!apt)      { showToast('Preencha o Apto / Unidade.', 'warning'); return; }
            await API.addONU({ gponPort, apt, ip, client, serial, model, distance });
            showToast(`ONU "${apt}" adicionada à porta ${gponPort}!`, 'success');

        } else {
            const name = document.getElementById('generic-name')?.value?.trim();
            const ip   = document.getElementById('generic-ip')?.value?.trim();
            if (!name || !ip) { showToast('Preencha Nome e IP.', 'warning'); return; }
            await API.addDevice({ name, ip, type });
            showToast(`"${name}" adicionado com sucesso!`, 'success');
        }

        closeModal();
        if (onDone) setTimeout(onDone, 400);
        else setTimeout(() => window.location.reload(), 400);
    });

    updateDeviceFormFields(); // sincroniza a seção visível com o tipo pré-selecionado

    API.getGponPorts().then(ports => {
        const sel = document.getElementById('onu-gpon-port');
        if (sel && ports && ports.length) {
            sel.innerHTML = ports.map(p =>
                `<option value="${p.id}">${p.name} (${p.onusOnline}/${p.onusTotal} ONUs • max ${p.maxONUs})</option>`
            ).join('');
        }
    }).catch(() => {});
}

// ===== DRAWER DE INFORMAÇÕES DO CLIENTE =====
function openClientDrawer(onuId) {
    const drawer  = document.getElementById('client-drawer');
    const overlay = document.getElementById('client-drawer-overlay');
    const body    = document.getElementById('client-drawer-body');
    const nameEl  = document.getElementById('drawer-client-name');
    const badge   = document.getElementById('drawer-criticality-badge');
    if (!drawer) return;

    drawer.classList.add('open');
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';

    if (nameEl) nameEl.textContent = 'Carregando...';
    if (badge)  badge.textContent  = '--';
    if (body)   body.innerHTML = `<div style="text-align:center;padding:3rem;color:var(--text-muted);"><i class="fas fa-spinner fa-spin" style="font-size:1.5rem;"></i></div>`;

    API.getClient(onuId).then(client => {
        if (!client) {
            if (body) body.innerHTML = `<div style="text-align:center;padding:3rem;color:var(--text-muted);"><i class="fas fa-user-slash" style="font-size:2rem;margin-bottom:1rem;display:block;"></i>Cliente não encontrado.</div>`;
            return;
        }

        const critMap = {
            'comum':      { bg:'rgba(100,116,139,0.15)', color:'#94a3b8', icon:'fa-user',      label:'Comum' },
            'prioritário':{ bg:'rgba(245,158,11,0.15)',  color:'#f59e0b', icon:'fa-star',      label:'Prioritário' },
            'crítico':    { bg:'rgba(220,38,38,0.15)',   color:'#dc2626', icon:'fa-heartbeat', label:'Crítico' },
        };
        const catIcons = { 'Residencial':'fa-home', 'Empresa':'fa-building', 'Saúde':'fa-hospital', 'Educação':'fa-graduation-cap' };
        const crit    = critMap[client.criticidade] || critMap['comum'];
        const catIcon = catIcons[client.categoria] || 'fa-tag';

        if (nameEl) nameEl.textContent = client.nome;
        if (badge) {
            badge.textContent       = crit.label;
            badge.style.background  = crit.bg;
            badge.style.color       = crit.color;
            badge.style.border      = `1px solid ${crit.color}55`;
        }

        const critDesc = client.criticidade === 'crítico'
            ? `${client.categoria} — SLA prioritário, alertas imediatos`
            : client.criticidade === 'prioritário'
            ? `${client.categoria} — Atendimento preferencial`
            : `${client.categoria} — Atendimento padrão`;

        if (body) body.innerHTML = `
            <div class="drawer-section">
                <div class="drawer-section-title"><i class="fas fa-id-card"></i> Identificação</div>
                <div class="drawer-info-grid">
                    <div class="drawer-info-item">
                        <span class="drawer-info-label">${client.tipo_documento === 'cnpj' ? 'CNPJ' : 'CPF'}</span>
                        <span class="drawer-info-value">${client.documento}</span>
                    </div>
                    <div class="drawer-info-item">
                        <span class="drawer-info-label">Contrato</span>
                        <span class="drawer-info-value">${client.contrato}</span>
                    </div>
                    <div class="drawer-info-item">
                        <span class="drawer-info-label">Categoria</span>
                        <span class="drawer-info-value"><i class="fas ${catIcon}" style="margin-right:0.35rem;color:var(--text-secondary);"></i>${client.categoria}</span>
                    </div>
                    <div class="drawer-info-item">
                        <span class="drawer-info-label">Instalação</span>
                        <span class="drawer-info-value">${client.data_instalacao}</span>
                    </div>
                </div>
            </div>

            <div class="drawer-section">
                <div class="drawer-section-title"><i class="fas fa-shield-alt"></i> Criticidade</div>
                <div class="drawer-criticality-block" style="background:${crit.bg};border:1px solid ${crit.color}33;">
                    <i class="fas ${crit.icon}" style="color:${crit.color};font-size:1.5rem;flex-shrink:0;"></i>
                    <div>
                        <div style="font-weight:600;color:${crit.color};">${crit.label}</div>
                        <div style="font-size:0.8rem;color:var(--text-secondary);">${critDesc}</div>
                    </div>
                </div>
            </div>

            <div class="drawer-section">
                <div class="drawer-section-title"><i class="fas fa-map-marker-alt"></i> Endereço</div>
                <div class="drawer-address">
                    <div>${client.endereco.rua}, ${client.endereco.numero}</div>
                    <div>${client.endereco.complemento}</div>
                    <div>${client.endereco.bairro} — ${client.endereco.cidade} / ${client.endereco.estado}</div>
                    <div style="color:var(--text-muted);font-size:0.8rem;">CEP: ${client.endereco.cep}</div>
                </div>
                <div class="drawer-coords">
                    <i class="fas fa-crosshairs" style="color:var(--text-muted);margin-right:0.4rem;font-size:0.7rem;"></i>
                    <span style="font-family:monospace;font-size:0.72rem;color:var(--text-muted);">${client.localizacao.lat}, ${client.localizacao.lng}</span>
                </div>
            </div>

            <div class="drawer-section">
                <div class="drawer-section-title"><i class="fas fa-phone-alt"></i> Contato</div>
                <div class="drawer-info-grid">
                    <div class="drawer-info-item">
                        <span class="drawer-info-label">Telefone</span>
                        <span class="drawer-info-value">${client.telefone}</span>
                    </div>
                    <div class="drawer-info-item">
                        <span class="drawer-info-label">E-mail</span>
                        <span class="drawer-info-value" style="font-size:0.78rem;">${client.email}</span>
                    </div>
                </div>
            </div>

            <div class="drawer-section">
                <div class="drawer-section-title"><i class="fas fa-wifi"></i> Plano Contratado</div>
                <div class="drawer-plan-badge"><i class="fas fa-bolt"></i> ${client.plano}</div>
            </div>`;
    }).catch(() => {
        if (body) body.innerHTML = `<div style="text-align:center;padding:3rem;color:var(--text-muted);">Erro ao carregar dados do cliente.</div>`;
    });
}

function closeClientDrawer() {
    const drawer  = document.getElementById('client-drawer');
    const overlay = document.getElementById('client-drawer-overlay');
    if (drawer)  drawer.classList.remove('open');
    if (overlay) overlay.classList.remove('open');
    document.body.style.overflow = '';
}
