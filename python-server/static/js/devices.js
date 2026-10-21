// ===== DISPOSITIVOS =====
let _mgmtDevices = [];

function renderDeviceRows(devices) {
    if (!devices.length) return `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:2rem;">Nenhum dispositivo encontrado.</td></tr>`;
    return devices.map(d => {
        const typeBadge = d.type === 'OLT' ? 'badge-warning' : d.type === 'ONU' ? 'badge-success' : d.type === 'Router' ? 'badge-success' : 'badge-critical';

        let ipInfo = `<div style="font-size:0.875rem;">${d.ip || '--'}</div>`;
        if (d.type === 'ONU') {
            ipInfo += `<div style="font-size:0.72rem;color:var(--text-muted);font-family:monospace;">Porta: ${d.gponPort || '--'}</div>`;
            if (d.serial) ipInfo += `<div style="font-size:0.7rem;color:var(--text-muted);">${d.serial}</div>`;
        } else if (d.type === 'OLT' && d.vendor) {
            ipInfo += `<div style="font-size:0.75rem;color:var(--text-muted);">${d.vendor}${d.location ? ' • ' + d.location : ''}</div>`;
        }

        let metricsHtml = '<span style="color:var(--text-muted);">--</span>';
        if (d.type === 'ONU' && d.status === 'online') {
            const rxColor = opticalColor('rxPower', d.rxPower, d.ponMode);
            metricsHtml = `<div style="font-weight:600;color:${rxColor};">${d.rxPower != null ? d.rxPower + ' dBm' : '--'}</div>
                           <div style="font-size:0.75rem;color:var(--text-muted);">${d.latency != null ? d.latency + ' ms' : ''}</div>`;
        } else if (d.type === 'OLT') {
            const cpuColor = (d.cpu ?? 0) > 80 ? 'var(--danger-color)' : (d.cpu ?? 0) > 60 ? 'var(--warning-color)' : 'var(--text-primary)';
            metricsHtml = `<div style="color:${cpuColor};">CPU: ${d.cpu ?? '--'}%</div>
                           <div style="font-size:0.75rem;color:var(--text-muted);">ONUs: ${d.onus_active ?? '--'}/${d.onus_total ?? '--'}</div>`;
        } else if (d.status === 'online') {
            metricsHtml = `<span style="font-size:0.8rem;color:var(--text-secondary);">Online</span>`;
        }

        return `
        <tr data-device-id="${d.id}">
            <td>
                <div style="font-weight:600;">${d.name}</div>
                ${d.client ? `<div style="font-size:0.8rem;color:var(--text-secondary);">${d.client}</div>` : `<div style="font-size:0.8rem;color:var(--text-muted);">ID: ${d.id}</div>`}
            </td>
            <td>${ipInfo}</td>
            <td><span class="badge ${typeBadge}" style="font-size:0.75rem;">${d.type}</span></td>
            <td>
                <div class="device-status status-${d.status}" style="justify-content:flex-start;">
                    <i class="fas fa-circle"></i>
                    <span>${d.status === 'online' ? 'Online' : 'Offline'}</span>
                </div>
            </td>
            <td>${metricsHtml}</td>
            <td>
                <div class="device-actions">
                    <button class="action-btn" title="Editar"          onclick="editDevice(${d.id})"><i class="fas fa-edit"></i></button>
                    <button class="action-btn" title="Ver Métricas"    onclick="viewDeviceMetrics(${d.id})"><i class="fas fa-chart-bar"></i></button>
                    <button class="action-btn" title="Testar Conexão"  onclick="testDevice(${d.id})"><i class="fas fa-plug"></i></button>
                    <button class="action-btn" title="Remover" style="color:var(--danger-color);" onclick="removeDevice(${d.id})"><i class="fas fa-trash"></i></button>
                </div>
            </td>
        </tr>`;
    }).join('');
}

function _findDevice(id) { return _mgmtDevices.find(d => d.id === id); }

async function _loadMgmtDevices() {
    const devices = await API.getDevices();
    if (devices) { _mgmtDevices = devices; _applyMgmtFilters(); }
}

function _applyMgmtFilters() {
    const query  = (document.getElementById('device-search')?.value  || '').toLowerCase().trim();
    const type   = document.getElementById('device-filter-type')?.value  || '';
    const status = document.getElementById('device-filter-status')?.value || '';
    let list     = _mgmtDevices;
    if (query)  list = list.filter(d =>
        (d.name   || '').toLowerCase().includes(query) ||
        (d.ip     || '').toLowerCase().includes(query) ||
        (d.client || '').toLowerCase().includes(query) ||
        (d.type   || '').toLowerCase().includes(query)
    );
    if (type)   list = list.filter(d => d.type   === type);
    if (status) list = list.filter(d => d.status === status);
    const tbody = document.getElementById('devices-table-body');
    const count = document.getElementById('devices-count');
    if (tbody) tbody.innerHTML = renderDeviceRows(list);
    if (count) count.innerHTML = `Mostrando <strong>${list.length}</strong> de <strong>${_mgmtDevices.length}</strong> dispositivo(s)`;
}

function editDevice(id) {
    const device = _findDevice(id);
    if (!device) return;
    openModal(`Editar — ${device.name}`, `
        <div class="form-group">
            <label class="form-label">Nome</label>
            <input type="text" class="form-control" id="edit-name" value="${escHtml(device.name)}">
        </div>
        <div class="form-group">
            <label class="form-label">IP</label>
            <input type="text" class="form-control" id="edit-ip" value="${escHtml(device.ip || '')}">
        </div>
        <div class="form-group">
            <label class="form-label">Status</label>
            <select class="form-control" id="edit-status">
                <option value="online"  ${device.status === 'online'  ? 'selected' : ''}>Online</option>
                <option value="offline" ${device.status === 'offline' ? 'selected' : ''}>Offline</option>
            </select>
        </div>
    `, 'Salvar', async () => {
        const fields = {
            name:   document.getElementById('edit-name').value.trim(),
            ip:     document.getElementById('edit-ip').value.trim(),
            status: document.getElementById('edit-status').value,
        };
        await API.updateDevice(id, fields);
        showToast('Dispositivo atualizado!', 'success');
        closeModal();
        setTimeout(_loadMgmtDevices, 300);
    });
}

function viewDeviceMetrics(id) {
    const d = _findDevice(id);
    if (!d) return;
    let rows;
    if (d.type === 'OLT') {
        rows = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
            ${[['CPU', (d.cpu ?? '--') + '%'], ['Memória', (d.memory ?? '--') + '%'], ['Temperatura', (d.temperature ?? '--') + '°C'], ['ONUs Ativas', `${d.onus_active ?? '--'}/${d.onus_total ?? '--'}`]].map(([k, v]) => `
                <div style="background:var(--bg-base);padding:1rem;border-radius:8px;">
                    <div style="color:var(--text-secondary);font-size:0.8rem;">${k}</div>
                    <div style="font-size:1.4rem;font-weight:700;">${v}</div>
                </div>`).join('')}
           </div>`;
    } else if (d.type === 'ONU') {
        const rxColor = opticalColor('rxPower', d.rxPower, d.ponMode);
        rows = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
            ${[['RxPower', { val: (d.rxPower ?? '--') + ' dBm', color: rxColor }],
               ['TxPower', { val: (d.txPower ?? '--') + ' dBm', color: '' }],
               ['Latência', { val: (d.latency ?? '--') + ' ms', color: '' }],
               ['Distância', { val: d.distance ?? '--', color: '' }],
               ['Porta GPON', { val: d.gponPort ?? '--', color: '' }],
               ['Uptime', { val: d.uptime ?? '--', color: '' }]].map(([k, o]) => `
                <div style="background:var(--bg-base);padding:1rem;border-radius:8px;">
                    <div style="color:var(--text-secondary);font-size:0.8rem;">${k}</div>
                    <div style="font-size:1.1rem;font-weight:700;${o.color ? 'color:' + o.color + ';' : ''}">${o.val}</div>
                </div>`).join('')}
           </div>`;
    } else {
        rows = `<p style="color:var(--text-secondary);">Métricas detalhadas não disponíveis para este tipo.</p>`;
    }
    openModal(`Métricas — ${d.name}`, rows, 'Fechar', closeModal);
}

function testDevice(id) {
    const btn = event.target.closest('button');
    const original = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    btn.disabled = true;
    setTimeout(() => {
        btn.innerHTML = original;
        btn.disabled  = false;
        const d = _findDevice(id);
        showToast(`Ping para ${d?.ip || 'dispositivo'}: OK — ${Math.floor(Math.random() * 20) + 5}ms`, 'success');
    }, 1500);
}

function removeDevice(id) {
    const d = _findDevice(id);
    if (!d) return;
    openModal('Confirmar Remoção', `
        <div style="text-align:center;padding:1rem;">
            <i class="fas fa-trash" style="font-size:2.5rem;color:var(--danger-color);margin-bottom:1rem;display:block;"></i>
            <p>Tem certeza que deseja remover <strong>${escHtml(d.name)}</strong>?</p>
            <p style="color:var(--text-secondary);font-size:0.875rem;margin-top:0.5rem;">Esta ação não pode ser desfeita.</p>
        </div>
    `, 'Remover', async () => {
        await API.deleteDevice(id);
        showToast(`"${d.name}" removido.`, 'warning');
        closeModal();
        setTimeout(_loadMgmtDevices, 300);
    });
}

function renderScanResults(devices, container) {
    if (!container) return;
    const knownIps = _mgmtDevices.map(d => d.ip);
    const fresh    = devices.filter(d => !knownIps.includes(d.ip));

    if (!fresh.length) {
        container.innerHTML = `<div style="color:var(--text-secondary);font-size:0.875rem;margin-top:1rem;">Nenhum dispositivo novo encontrado na faixa.</div>`;
        return;
    }
    container.innerHTML = `
        <div style="margin-top:1rem;">
            <div style="font-weight:600;margin-bottom:0.75rem;color:var(--text-primary);">
                <i class="fas fa-check-circle" style="color:var(--success-color);margin-right:0.5rem;"></i>
                ${fresh.length} dispositivo(s) encontrado(s)
            </div>
            <div style="display:flex;flex-direction:column;gap:0.5rem;">
                ${fresh.map(d => {
                    const latency = d.latency_ms != null ? `${d.latency_ms}ms` : '--';
                    const badges  = (d.oid_groups || []).map(g => `<span class="badge badge-secondary" style="font-size:0.65rem;margin-right:0.25rem;">${g}</span>`).join('');
                    const nameEsc = (d.suggested_name || d.ip).replace(/'/g, "\\'");
                    return `
                    <div style="display:flex;align-items:center;justify-content:space-between;background:var(--bg-base);padding:0.75rem 1rem;border-radius:8px;gap:1rem;flex-wrap:wrap;">
                        <div style="display:flex;align-items:center;gap:1rem;">
                            <div class="device-status status-${d.status}" style="justify-content:flex-start;">
                                <i class="fas fa-circle" style="font-size:0.6rem;"></i>
                            </div>
                            <div>
                                <div style="font-weight:600;font-size:0.9rem;">${d.ip} <span style="font-weight:400;color:var(--text-secondary);">— ${d.vendor_label}</span></div>
                                <div style="color:var(--text-secondary);font-size:0.8rem;">${d.sysDescr ? d.sysDescr + ' • ' : ''}${d.device_type} • Latência: ${latency}</div>
                                ${badges ? `<div style="margin-top:0.25rem;">${badges}</div>` : ''}
                            </div>
                        </div>
                        <button class="btn btn-secondary" style="font-size:0.8rem;padding:0.35rem 0.75rem;"
                            onclick="openScannedDeviceModal('${d.ip}','${nameEsc}','${d.device_type}',this)">
                            <i class="fas fa-plus"></i> Adicionar
                        </button>
                    </div>`;
                }).join('')}
            </div>
        </div>`;
}

// Abre o mesmo modal "Novo Dispositivo" usado no botão do cabeçalho, já
// pré-preenchido com o resultado do scan — assim um OLT/Router encontrado na
// rede passa pelo mesmo fluxo (e endpoints /api/olts, /api/onus) de um
// cadastro manual, em vez de um POST /api/devices genérico que não registra
// OLTs na topologia do mock_engine.
function openScannedDeviceModal(ip, name, deviceType, btn) {
    const modalType = deviceType === 'OLT' ? 'OLT' : deviceType === 'Router' ? 'Router' : 'Switch';
    openAddDeviceModal(() => {
        _loadMgmtDevices();
        btn.innerHTML = '<i class="fas fa-check"></i> Adicionado';
        btn.disabled  = true;
        btn.style.backgroundColor = 'var(--success-color)';
    }, { type: modalType, ip, name });
}

document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('add-device-btn-page')?.addEventListener('click', () => openAddDeviceModal(_loadMgmtDevices));

    (async () => {
        await _loadMgmtDevices();
        API.startPolling(async () => { await _loadMgmtDevices(); });
    })();

    document.getElementById('device-search')?.addEventListener('input', _applyMgmtFilters);
    document.getElementById('device-filter-type')?.addEventListener('change', _applyMgmtFilters);
    document.getElementById('device-filter-status')?.addEventListener('change', _applyMgmtFilters);

    // Pré-preenche a Faixa de IP com TODAS as sub-redes que este host tem
    // (LAN real + adaptadores virtuais + loopback do laboratório), pra
    // escanear tudo de uma vez sem precisar digitar nada — só sobrescreve se
    // o campo ainda estiver no placeholder padrão (usuário não mexeu ainda).
    (async () => {
        const rangeInput = document.getElementById('scan-range');
        const hintEl = document.getElementById('scan-range-hint');
        if (!rangeInput || rangeInput.value !== '10.0.1.0/24') return;
        const detected = await API.getLocalRanges();
        if (detected?.length && rangeInput.value === '10.0.1.0/24') {
            rangeInput.value = detected.map(d => d.range).join(', ');
            const list = detected.map(d => `${d.range} (${d.ip})`).join(', ');
            if (hintEl) hintEl.textContent = `Redes detectadas neste host: ${list} — todas assumem /24, ajuste se quiser escanear outra coisa.`;
        }
    })();

    const scanBtn = document.getElementById('scan-btn');
    if (scanBtn) {
        scanBtn.addEventListener('click', async function () {
            const range     = document.getElementById('scan-range')?.value?.trim() || '10.0.1.0/24';
            const protocol  = document.getElementById('scan-protocol')?.value || 'ping';
            const resultsEl = document.getElementById('scan-results');

            const cidrRe = /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}$/;
            const parts  = range.split(',').map(p => p.trim()).filter(Boolean);
            if (!parts.length || !parts.every(p => cidrRe.test(p))) {
                showToast('Faixa de IP inválida. Use o formato 192.168.1.0/24 (uma ou mais, separadas por vírgula)', 'warning');
                return;
            }

            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Escaneando...';
            this.disabled  = true;
            if (resultsEl) {
                resultsEl.style.display = 'block';
                resultsEl.innerHTML = `
                    <div style="color:var(--text-secondary);font-size:0.875rem;margin-bottom:1rem;">
                        <i class="fas fa-search" style="color:var(--primary-color);margin-right:0.5rem;"></i>
                        Escaneando ${range} via ${protocol.toUpperCase()}...
                    </div>
                    <div id="scan-progress" style="width:100%;height:6px;background:var(--bg-elevated);border-radius:3px;overflow:hidden;">
                        <div id="scan-bar" style="width:0%;height:100%;background:var(--primary-color);border-radius:3px;transition:width 0.3s;"></div>
                    </div>`;
            }

            let progress = 0;
            const progressInterval = setInterval(() => {
                progress = Math.min(progress + Math.random() * 10, 95);
                const bar = document.getElementById('scan-bar');
                if (bar) bar.style.width = `${progress}%`;
            }, 300);

            try {
                const discovered = await API.scanDevices(range, protocol);
                const bar = document.getElementById('scan-bar');
                if (bar) bar.style.width = '100%';
                renderScanResults(discovered, resultsEl);
            } finally {
                clearInterval(progressInterval);
                this.innerHTML = '<i class="fas fa-search"></i> Escanear Rede';
                this.disabled  = false;
            }
        });
    }
});
