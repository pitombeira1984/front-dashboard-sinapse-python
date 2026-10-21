// ===== DASHBOARD =====
// Nota de porte: os antigos handlers de ".chart-range-btn" e a chamada a
// renderONURxPowerChart() (função que nunca existiu) foram removidos aqui — o
// primeiro não tinha nenhum botão correspondente no HTML e o segundo quebrava o
// console ao trocar a porta GPON. Nenhuma funcionalidade real dependia deles.

function applyLiveData(data) {
    if (!data) return;

    if (typeof pushGPONChartPoints === 'function') pushGPONChartPoints(data);

    const setCPU   = document.getElementById('cpu-usage');
    const setLat   = document.getElementById('latency');
    const setAvail = document.getElementById('availability');

    if (setCPU) {
        setCPU.textContent = `${data.cpu}%`;
        const bar = document.getElementById('cpu-bar');
        if (bar) {
            bar.style.width = `${data.cpu}%`;
            bar.style.backgroundColor = data.cpu > 90 ? 'var(--danger-color)' : data.cpu > 70 ? 'var(--warning-color)' : 'var(--success-color)';
        }
    }

    const onusEl = document.getElementById('onus');
    if (onusEl) {
        const active = data.onusOnline ?? data.wifiClients ?? '--';
        const total  = data.onusTotal  ?? 8;
        onusEl.textContent = `${active}/${total}`;
    }

    const rxEl = document.getElementById('avg-rxpower');
    if (rxEl) {
        if (data.avgRxPower != null && data.avgRxPower !== 0) {
            rxEl.textContent = `${data.avgRxPower} dBm`;
            rxEl.style.color = data.avgRxPower < -25 ? 'var(--danger-color)' : data.avgRxPower < -22 ? 'var(--warning-color)' : 'var(--success-color)';
        } else {
            rxEl.textContent = '-- dBm';
            rxEl.style.color = '';
        }
    }

    if (setLat) {
        setLat.innerHTML = (data.avgLatency != null && data.avgLatency !== 0)
            ? `${data.avgLatency}<span style="font-size:1rem;">ms</span>`
            : `--<span style="font-size:1rem;">ms</span>`;
    }

    if (setAvail && data.availability !== undefined) {
        setAvail.textContent = `${data.availability}%`;
    }
}

function _updateAvailBar(availability) {
    const availBar = document.getElementById('avail-bar');
    if (availBar && availability !== undefined) {
        availBar.style.width = `${Math.min(availability, 100)}%`;
        availBar.style.backgroundColor = availability >= 99 ? 'var(--success-color)' : availability >= 90 ? 'var(--warning-color)' : 'var(--danger-color)';
    }
}

function _updateOnusTrend(onusOnline, onusTotal) {
    const trend = document.getElementById('onus-trend');
    if (trend && onusOnline !== undefined) {
        const offline = (onusTotal ?? 8) - onusOnline;
        trend.innerHTML = offline > 0
            ? `<i class="fas fa-exclamation-triangle" style="color:var(--danger-color);"></i> <span style="color:var(--danger-color);">${offline} offline</span>`
            : `<i class="fas fa-check-circle" style="color:var(--success-color);"></i> <span>Todas online</span>`;
    }
}

// ── ONU Real (card fixo, só existe no HTML quando ONU_POLLER_ENABLED=true) ──
let _onuRealLastAt = null;

function updateOnuRealCard(status) {
    if (!status || !document.getElementById('onu-real-card')) return;
    const r = status.lastReading || {};
    const set = (id, text, color = '') => {
        const el = document.getElementById(id);
        if (el) { el.textContent = text; el.style.color = color; }
    };
    const fmt = (v, unit, digits = 2) => v == null ? '--' : `${Number(v).toFixed(digits)} ${unit}`;

    const badge = document.getElementById('onu-real-badge');
    if (badge) {
        const [cls, label] = status.fresh ? ['badge-success', 'Recebendo dados']
            : status.lastError ? ['badge-critical', 'Sem resposta']
            : ['badge-warning', 'Conectando...'];
        badge.className = `badge ${cls}`;
        badge.textContent = label;
    }

    const errEl = document.getElementById('onu-real-error');
    if (errEl) {
        errEl.style.display = !status.fresh && status.lastError ? '' : 'none';
        errEl.innerHTML = status.lastError ? `<i class="fas fa-exclamation-triangle" style="margin-right:0.35rem;"></i>${escHtml(status.lastError)}` : '';
    }

    const stale = !status.fresh;
    const muted = stale ? 'var(--text-muted)' : '';
    // Limites da tecnologia informada pela própria ONU (ex: XGS-PON → ITU-T G.9807.1).
    const rxColor   = opticalColor('rxPower', r.rxPowerDbm, r.ponMode, '');
    const txColor   = opticalColor('txPower', r.txPowerDbm, r.ponMode, '');
    const tempColor = opticalColor('temperature', r.temperatureC, r.ponMode, '');
    const voltColor = opticalColor('voltage', r.voltageV, r.ponMode, '');

    set('onu-real-pon', [r.ponMode, r.connectStatus].filter(Boolean).join(' • ') || '--', muted);
    set('onu-real-rx', fmt(r.rxPowerDbm, 'dBm'), muted || rxColor);
    set('onu-real-tx', fmt(r.txPowerDbm, 'dBm'), muted || txColor);
    set('onu-real-temp', fmt(r.temperatureC, '°C', 1), muted || tempColor);
    set('onu-real-volt', fmt(r.voltageV, 'V'), muted || voltColor);
    set('onu-real-bias', fmt(r.biasCurrentMa, 'mA', 1), muted);
    set('onu-real-fec', `${r.fecErrors ?? '--'} / ${r.hecErrors ?? '--'}`, muted);
    set('onu-real-age', status.ageSeconds == null ? 'nenhuma ainda' : `há ${formatDuration(status.ageSeconds)}`, stale && status.ageSeconds != null ? 'var(--danger-color)' : '');

    // Só plota leitura nova — o polling do dashboard (5s) pode ser mais rápido que o do poller.
    if (status.lastReadingAt && status.lastReadingAt !== _onuRealLastAt) {
        _onuRealLastAt = status.lastReadingAt;
        pushOnuRealPoint(status.lastReadingAt, r.rxPowerDbm);
    }
}

document.addEventListener('DOMContentLoaded', function () {
    initLatencyGPONChartEmpty();
    initOnuRealChartEmpty();
    if (document.getElementById('onu-real-card')) API.getOnuRealStatus().then(updateOnuRealCard);

    const advancedMetrics = window.SINAPSE_SETTINGS?.advancedMetrics ?? true;

    (async () => {
        const olts = await API.getOLTsBandwidth();
        if (olts && olts.length) renderOLTBandwidthChart(olts);
    })();

    API.startPolling(async (data) => {
        applyLiveData(data);
        _updateAvailBar(data.availability);
        _updateOnusTrend(data.onusOnline, data.onusTotal);

        try {
            const [onus, olts, onuReal] = await Promise.all([
                API.getONUs(AppState.currentGponPort),
                API.getOLTsBandwidth(),
                document.getElementById('onu-real-card') ? API.getOnuRealStatus() : null,
            ]);
            updateOnuRealCard(onuReal);
            const grid = document.getElementById('devices-grid-dashboard');
            if (grid) {
                const oltDevice = {
                    id: 100, name: 'OLT Huawei MA5800-X2', ip: '10.0.1.10', type: 'OLT', status: 'online',
                    cpu: data.cpu, memory: data.memPercent, temperature: data.temperature,
                    onus_active: data.onusOnline, onus_total: data.onusTotal,
                };
                const onuDevices = (onus || []).map(o => ({ ...o, name: `ONU — ${o.apt}`, type: 'ONU' }));
                grid.innerHTML = renderDeviceCards([oltDevice, ...onuDevices], advancedMetrics);
            }
            if (olts && olts.length) {
                if (ChartRegistry['oltBandwidth']) updateOLTBandwidthChart(olts);
                else renderOLTBandwidthChart(olts);
            }
        } catch (e) { /* poll tick falhou silenciosamente, próximo ciclo tenta de novo */ }
    });

    API.startTrapPolling((stats, lastTrap) => {
        updateTrapBadge(stats);
        showTrapToast(lastTrap);
        const trapCard = document.getElementById('trap-summary-card') || document.getElementById('trap-summary-placeholder');
        if (trapCard) trapCard.outerHTML = renderTrapSummaryCard(stats);
    });

    (async () => {
        const res = await API.getTrapStats();
        const stats = res?.data ?? res;
        if (stats) {
            updateTrapBadge(stats);
            const placeholder = document.getElementById('trap-summary-placeholder');
            if (placeholder) placeholder.outerHTML = renderTrapSummaryCard(stats);
        }
    })();

    (async () => {
        try {
            const ports = await API.getGponPorts();
            const select = document.getElementById('gpon-port-selector');
            if (select && ports && ports.length) {
                AppState.currentGponPort = select.dataset.current || AppState.currentGponPort;
                select.innerHTML = ports.map(p => {
                    const onuInfo = p.onusTotal > 0 ? ` (${p.onusOnline}/${p.onusTotal} ONUs)` : ' (sem ONUs)';
                    return `<option value="${p.id}" ${p.id === AppState.currentGponPort ? 'selected' : ''}>${p.name}${onuInfo}</option>`;
                }).join('');

                select.addEventListener('change', async function () {
                    AppState.currentGponPort = this.value;
                    initLatencyGPONChartEmpty();

                    const [liveData, onus] = await Promise.all([
                        API.getLive(AppState.currentGponPort),
                        API.getONUs(AppState.currentGponPort),
                    ]);

                    if (liveData) {
                        applyLiveData(liveData);
                        _updateAvailBar(liveData.availability);
                        _updateOnusTrend(liveData.onusOnline, liveData.onusTotal);
                    }

                    const grid = document.getElementById('devices-grid-dashboard');
                    if (grid && liveData) {
                        const oltDevice = {
                            id: 100, name: 'OLT Huawei MA5800-X2', ip: '10.0.1.10', type: 'OLT', status: 'online',
                            cpu: liveData.cpu, memory: liveData.memPercent, temperature: liveData.temperature,
                            onus_active: liveData.onusOnline, onus_total: liveData.onusTotal,
                        };
                        const onuDevices = (onus || []).map(o => ({ ...o, name: `ONU — ${o.apt}`, type: 'ONU' }));
                        grid.innerHTML = renderDeviceCards([oltDevice, ...onuDevices], advancedMetrics);
                    }

                    const portObj = ports.find(p => p.id === AppState.currentGponPort);
                    showToast(`Monitorando porta ${portObj?.name || AppState.currentGponPort}`, 'info');
                });
            }
        } catch (e) { /* seletor de portas indisponível — dashboard segue com a porta padrão */ }
    })();

    document.getElementById('add-device-btn')?.addEventListener('click', () => openAddDeviceModal());

    // "Atualizar" — refaz o polling imediatamente (o dado real já é atualizado a
    // cada 5s; este botão só antecipa o próximo ciclo e dá feedback visual).
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async function () {
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Atualizando...';
            const data = await API.getLive(AppState.currentGponPort);
            if (data) { applyLiveData(data); _updateAvailBar(data.availability); _updateOnusTrend(data.onusOnline, data.onusTotal); }
            this.innerHTML = '<i class="fas fa-sync-alt"></i> Atualizar';
            this.style.backgroundColor = 'var(--success-color)';
            setTimeout(() => { this.style.backgroundColor = ''; }, 500);
        });
    }
});
