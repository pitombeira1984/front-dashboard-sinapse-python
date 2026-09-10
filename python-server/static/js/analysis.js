// ===== ANÁLISE (regressão linear roda no navegador, como no app original) =====

function renderPredictionItems(predictions) {
    if (!predictions.length) {
        return `<div style="text-align:center;color:var(--text-muted);padding:2rem;">
            <i class="fas fa-check-circle" style="font-size:1.5rem;color:var(--success-color);margin-bottom:0.5rem;display:block;"></i>
            Nenhuma tendência de degradação detectada nos dados monitorados.
        </div>`;
    }
    return predictions.map(p => `
        <div class="alert-item alert-${p.severity}">
            <i class="fas ${p.severity === 'critical' ? 'fa-exclamation-circle' : p.severity === 'warning' ? 'fa-exclamation-triangle' : 'fa-info-circle'} alert-icon"></i>
            <div class="alert-content">
                <div class="alert-title">
                    ${p.title}
                    ${p.onuId ? `<button class="client-info-btn" onclick="openClientDrawer(${p.onuId})" title="Ver informações do cliente"><i class="fas fa-info-circle"></i></button>` : ''}
                    ${p.hasActiveAlert ? '<span class="badge badge-critical" style="font-size:0.65rem;margin-left:0.4rem;">Alerta ativo</span>' : ''}
                </div>
                <div class="alert-description">${p.detail} • Previsão: ${p.etaLabel} • Confiança: ${p.confidence}%</div>
            </div>
            <button class="btn btn-secondary" style="font-size:0.75rem;padding:0.25rem 0.75rem;white-space:nowrap;" onclick="openScheduleMaintenanceModal('${escHtml(p.deviceTarget)}')">
                <i class="fas fa-calendar-check"></i> Agendar
            </button>
        </div>`).join('');
}

function renderRecommendationsPanel(predictions) {
    if (!predictions.length) {
        return `<div style="background:var(--bg-surface);padding:1rem;border-radius:var(--border-radius);color:var(--text-secondary);font-size:0.875rem;">
            Nenhuma ação recomendada no momento — todos os indicadores monitorados estão dentro da normalidade.
        </div>`;
    }
    const top = predictions[0];
    const stepsByKind = {
        optical: ['Verificar conector óptico e possível curvatura de fibra', 'Limpar conectores (SC/APC) na ONU e no splitter', 'Medir potência óptica na CTO com power meter', 'Agendar manutenção preventiva antes do prazo previsto'],
        traffic: ['Avaliar necessidade de upgrade de link/uplink', 'Balancear tráfego entre portas GPON disponíveis', 'Verificar políticas de QoS e contenção', 'Contatar operadora de backbone se aplicável'],
        latency: ['Verificar congestionamento nos enlaces GPON', 'Analisar filas e políticas de QoS na OLT', 'Checar utilização de CPU/memória da OLT', 'Agendar diagnóstico de rede'],
    };
    const steps = stepsByKind[top.kind] || ['Investigar causa raiz', 'Agendar diagnóstico técnico'];
    return `
        <div style="background:var(--bg-surface);padding:1rem;border-radius:var(--border-radius);">
            <div style="font-weight:600;margin-bottom:0.5rem;">Para ${escHtml(top.deviceTarget)}:</div>
            <div style="color:var(--text-secondary);font-size:0.875rem;margin-bottom:1rem;">
                ${steps.map((s, i) => `${i + 1}. ${s}`).join('<br>')}
            </div>
            <button class="btn btn-primary" style="font-size:0.875rem;" onclick="openScheduleMaintenanceModal('${escHtml(top.deviceTarget)}')">
                <i class="fas fa-calendar-check"></i> Agendar Manutenção
            </button>
        </div>
        ${predictions.length > 1 ? `<div style="margin-top:1rem;font-size:0.8rem;color:var(--text-muted);">+ ${predictions.length - 1} outra(s) previsão(ões) na lista ao lado.</div>` : ''}`;
}

function renderAiModelCard(avgConfidence) {
    const acc = avgConfidence === null || avgConfidence === undefined ? null : avgConfidence;
    return `
        <div style="background:var(--bg-surface);padding:1.5rem;border-radius:var(--border-radius);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
                <div style="font-weight:600;">Regressão Linear</div>
                <span class="badge badge-success">Ativo</span>
            </div>
            <div style="color:var(--text-secondary);font-size:0.875rem;margin-bottom:1rem;">Predição de degradação óptica, tráfego e latência por tendência (mínimos quadrados)</div>
            <div style="font-size:0.875rem;">
                <div style="display:flex;justify-content:space-between;margin-bottom:0.25rem;"><span>Confiança média (previsões ativas):</span><span>${acc === null ? '--' : acc + '%'}</span></div>
                <div style="width:100%;height:6px;background:var(--bg-elevated);border-radius:3px;">
                    <div style="width:${acc === null ? 0 : acc}%;height:100%;background:var(--success-color);border-radius:3px;"></div>
                </div>
            </div>
        </div>`;
}

function renderMaintenanceRows(items) {
    if (!items.length) return `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:2rem;">Nenhuma manutenção agendada.</td></tr>`;
    return items.map(m => `
        <tr data-maintenance-id="${m.id}">
            <td><div style="font-weight:600;">${m.device}</div></td>
            <td style="font-size:0.875rem;">${m.date} ${m.time || ''}</td>
            <td style="font-size:0.875rem;color:var(--text-secondary);">${m.description}</td>
            <td>${m.duration || '--'}</td>
            <td><span class="badge ${m.status === 'agendado' ? 'badge-warning' : 'badge-success'}">${m.status}</span></td>
            <td>
                <div class="device-actions">
                    <button class="action-btn" title="Cancelar" style="color:var(--danger-color);" onclick="cancelMaintenance(${m.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>`).join('');
}

let _maintenances = [];

function updateMaintenanceCount() {
    const el = document.getElementById('maintenance-count');
    if (el) el.textContent = _maintenances.length;
}

async function cancelMaintenance(id) {
    await API.deleteMaintenance(id);
    _maintenances = _maintenances.filter(m => m.id !== id);
    showToast('Manutenção cancelada.', 'warning');
    const row = document.querySelector(`tr[data-maintenance-id="${id}"]`);
    if (row) row.remove();
    updateMaintenanceCount();
}

function openScheduleMaintenanceModal(devicePreset = '') {
    API.getDevices().then(devices => {
        const today = new Date().toISOString().split('T')[0];
        const hasPreset = devices.some(d => d.name === devicePreset);
        openModal('Agendar Manutenção', `
            <div class="form-group">
                <label class="form-label">Dispositivo *</label>
                <select class="form-control" id="maint-device">
                    ${devices.map(d => `<option value="${d.name}" ${d.name === devicePreset ? 'selected' : ''}>${d.name}</option>`).join('')}
                    ${!hasPreset && devicePreset ? `<option value="${devicePreset}" selected>${devicePreset}</option>` : ''}
                </select>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">Data *</label>
                    <input type="date" class="form-control" id="maint-date" value="${today}" min="${today}">
                </div>
                <div class="form-group">
                    <label class="form-label">Horário *</label>
                    <input type="time" class="form-control" id="maint-time" value="03:00">
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">Duração Estimada</label>
                <select class="form-control" id="maint-duration">
                    <option>15 min</option><option>30 min</option><option selected>1 hora</option>
                    <option>2 horas</option><option>4 horas</option><option>8 horas</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Descrição da Manutenção *</label>
                <input type="text" class="form-control" id="maint-description" placeholder="Ex: Limpeza de conectores ópticos" value="${devicePreset ? 'Manutenção preventiva — ' + devicePreset : ''}">
            </div>
            <div class="form-group">
                <label class="form-label">Responsável</label>
                <input type="text" class="form-control" id="maint-responsible" placeholder="Nome do técnico">
            </div>
        `, 'Agendar', async () => {
            const device      = document.getElementById('maint-device')?.value;
            const date        = document.getElementById('maint-date')?.value;
            const time        = document.getElementById('maint-time')?.value;
            const duration    = document.getElementById('maint-duration')?.value;
            const description = document.getElementById('maint-description')?.value?.trim();
            const responsible = document.getElementById('maint-responsible')?.value?.trim();
            if (!device || !date || !description) { showToast('Preencha Dispositivo, Data e Descrição.', 'warning'); return; }

            const created = await API.addMaintenance({ device, date, time, duration, description, responsible: responsible || 'admin' });
            if (created) _maintenances.unshift(created);
            showToast(`Manutenção agendada para ${device} em ${date} às ${time}!`, 'success');
            closeModal();

            const tbody = document.getElementById('maintenance-table-body');
            if (tbody) tbody.innerHTML = renderMaintenanceRows(_maintenances);
            updateMaintenanceCount();
        });
    }).catch(() => {});
}

function _lookbackForRange(range) {
    switch (range) {
        case '24h': return 20;
        case '7d':  return 60;
        default:    return 120;
    }
}

let _lastPredictions = [];

async function runPredictiveAnalysis(showResultModal = false) {
    const listEl  = document.getElementById('predictions-list');
    const panelEl = document.getElementById('recommendations-panel');
    const badgeEl = document.getElementById('predictions-badge');

    const lookback = _lookbackForRange(AppState.currentTimeRange);
    const [history, oltBw, alerts] = await Promise.all([API.getHistory(), API.getOLTsBandwidth(), API.getAllAlerts()]);
    const SAMPLE_INTERVAL_SEC = history?.intervalSeconds || (API.POLL_INTERVAL / 1000);
    const activeAlerts = (alerts || []).filter(a => a.severity !== 'resolved');

    const devicesCountEl = document.getElementById('analysis-devices-count');
    if (devicesCountEl) {
        const oltCount = (oltBw || []).length;
        const onuCount = (history?.onuRxHistory || []).length;
        const totalMonitored = oltCount + onuCount;
        devicesCountEl.innerHTML = `<i class="fas fa-server" style="color:var(--primary-color);margin-right:0.35rem;"></i>${totalMonitored} dispositivo(s) monitorado(s) (${oltCount} OLT${oltCount === 1 ? '' : 's'} + ${onuCount} ONU${onuCount === 1 ? '' : 's'})`;
    }

    const predictions = [];

    (history?.onuRxHistory || []).forEach(onu => {
        const samples = (onu.history || []).slice(-lookback);
        if (samples.length < 12) return;
        const { slope, r2 } = linearRegression(samples);
        if (slope >= -0.003 || r2 < 0.35) return;
        const current = onu.current;
        if (current <= -27) return;
        const threshold = current > -24 ? -24 : -27;
        const samplesToThreshold = (threshold - current) / slope;
        if (!isFinite(samplesToThreshold) || samplesToThreshold <= 0) return;
        const seconds = samplesToThreshold * SAMPLE_INTERVAL_SEC;
        if (seconds > 90 * 86400) return;

        predictions.push({
            id: `onu-${onu.id}`, kind: 'optical', severity: threshold === -27 ? 'critical' : 'warning',
            title: `Degradação Óptica em ONU — ${onu.apt}`,
            detail: `${onu.client} • RxPower atual: ${current.toFixed(2)} dBm • Tendência: ${(slope * 10).toFixed(3)} dB/10 ciclos`,
            etaLabel: formatDuration(seconds), confidence: Math.round(Math.min(97, Math.max(35, r2 * 100))),
            deviceTarget: `ONU — ${onu.apt}`, onuId: onu.id,
            hasActiveAlert: activeAlerts.some(a => a.device && a.device.includes(onu.apt)),
        });
    });

    const olt01 = (oltBw || []).find(o => o.id === 'OLT-01');
    const trafficSamples = (history?.traffic || []).slice(-lookback).map(t => t.in);
    if (olt01 && trafficSamples.length >= 12) {
        const { slope, r2 } = linearRegression(trafficSamples);
        const threshold = olt01.capacity * 0.85;
        const current = trafficSamples[trafficSamples.length - 1];
        if (slope > 0.01 && r2 >= 0.3 && current < threshold) {
            const seconds = ((threshold - current) / slope) * SAMPLE_INTERVAL_SEC;
            if (seconds > 0 && seconds <= 90 * 86400) {
                predictions.push({
                    id: 'olt01-traffic', kind: 'traffic', severity: current / olt01.capacity > 0.7 ? 'warning' : 'info',
                    title: `Saturação de Link — ${olt01.name}`,
                    detail: `Tráfego de entrada em ${current.toFixed(0)} Mbps de ${olt01.capacity} Mbps (${(current / olt01.capacity * 100).toFixed(1)}%) • Em crescimento`,
                    etaLabel: formatDuration(seconds), confidence: Math.round(Math.min(95, Math.max(35, r2 * 100))),
                    deviceTarget: `${olt01.id} — ${olt01.model}`,
                    hasActiveAlert: activeAlerts.some(a => a.device === olt01.id || a.device === olt01.name),
                });
            }
        }
    }

    const latencySamples = (history?.latency || []).slice(-lookback);
    if (latencySamples.length >= 12) {
        const { slope, r2 } = linearRegression(latencySamples);
        const threshold = MONITORING_PARAM_TYPES.latencyHigh.defaultThreshold;
        const current = latencySamples[latencySamples.length - 1];
        if (slope > 0.002 && r2 >= 0.3 && current < threshold) {
            const seconds = ((threshold - current) / slope) * SAMPLE_INTERVAL_SEC;
            if (seconds > 0 && seconds <= 90 * 86400) {
                predictions.push({
                    id: 'olt01-latency', kind: 'latency', severity: 'warning',
                    title: 'Aumento de Latência — Rede GPON',
                    detail: `Latência média atual: ${current.toFixed(1)} ms • Tendência de alta`,
                    etaLabel: formatDuration(seconds), confidence: Math.round(Math.min(95, Math.max(35, r2 * 100))),
                    deviceTarget: `${olt01?.id || 'OLT-01'} — ${olt01?.model || 'MA5800-X2'}`,
                    hasActiveAlert: activeAlerts.some(a => (a.title || '').toLowerCase().includes('latência')),
                });
            }
        }
    }

    const sevOrder = { critical: 0, warning: 1, info: 2 };
    predictions.sort((a, b) => sevOrder[a.severity] - sevOrder[b.severity]);
    _lastPredictions = predictions;

    if (listEl)  listEl.innerHTML  = renderPredictionItems(predictions);
    if (panelEl) panelEl.innerHTML = renderRecommendationsPanel(predictions);

    const modelsGridEl = document.getElementById('ai-models-grid');
    if (modelsGridEl) {
        const avgConfidence = predictions.length ? Math.round(predictions.reduce((sum, p) => sum + p.confidence, 0) / predictions.length) : null;
        modelsGridEl.innerHTML = renderAiModelCard(avgConfidence);
    }
    if (badgeEl) badgeEl.textContent = `${predictions.length} Previs${predictions.length === 1 ? 'ão' : 'ões'} Ativa${predictions.length === 1 ? '' : 's'}`;

    const updatedEl = document.getElementById('analysis-updated-at');
    if (updatedEl) updatedEl.innerHTML = `<i class="fas fa-clock" style="margin-right:0.35rem;"></i>Última análise: ${new Date().toLocaleTimeString('pt-BR')}`;

    if (showResultModal) {
        const critCount  = predictions.filter(p => p.severity === 'critical').length;
        const correlated = predictions.filter(p => p.hasActiveAlert).length;
        openModal('Análise Concluída', `
            <div style="text-align:center;padding:1rem;">
                <i class="fas fa-check-circle" style="font-size:3rem;color:var(--success-color);margin-bottom:1rem;display:block;"></i>
                <h3 style="margin-bottom:1rem;">Análise de IA Concluída</h3>
                <div style="color:var(--text-secondary);line-height:2;text-align:left;display:inline-block;">
                    <div>• ${predictions.length} previsão(ões) identificada(s) a partir da telemetria em tempo real</div>
                    <div>• ${critCount} de severidade crítica</div>
                    <div>• ${correlated} já correlacionada(s) a alertas ativos</div>
                    <div>• Modelo: Regressão Linear sobre RxPower, tráfego e latência</div>
                </div>
            </div>
        `, 'Fechar', closeModal);
    }

    return predictions;
}

document.addEventListener('DOMContentLoaded', function () {
    (async () => { _maintenances = await API.getMaintenances() || []; })();

    document.querySelectorAll('.time-range-selector .time-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.time-range-selector .time-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            AppState.currentTimeRange = this.getAttribute('data-range');

            const customCard = document.getElementById('custom-range-card');
            if (customCard) customCard.style.display = AppState.currentTimeRange === 'custom' ? '' : 'none';

            if (AppState.currentTimeRange !== 'custom') {
                showToast(`Período alterado para: ${this.textContent.trim()}`, 'info');
                runPredictiveAnalysis();
            }
        });
    });

    document.getElementById('apply-custom-range')?.addEventListener('click', () => {
        const start = document.getElementById('custom-start')?.value;
        const end   = document.getElementById('custom-end')?.value;
        if (!start || !end) { showToast('Selecione as datas de início e fim.', 'warning'); return; }
        if (new Date(start) > new Date(end)) { showToast('A data de início deve ser anterior à data fim.', 'warning'); return; }
        showToast(`Filtro aplicado: ${start} até ${end}`, 'success');
        runPredictiveAnalysis();
    });

    const runBtn = document.getElementById('run-analysis-btn');
    if (runBtn) {
        runBtn.addEventListener('click', async function () {
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analisando...';
            this.disabled  = true;
            await runPredictiveAnalysis(true);
            this.innerHTML = '<i class="fas fa-play"></i> Executar Análise';
            this.disabled  = false;
        });
    }

    runPredictiveAnalysis();
});
