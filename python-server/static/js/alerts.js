// MONITORING_PARAM_TYPES (catálogo de tipos de parâmetro) vem de utils.js —
// carregado em todas as páginas porque analysis.js também depende dele.

let _alerts = [];
let _monitoringParams = [];

function renderAlertRows(alerts) {
    if (!alerts.length) return `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:2rem;">Nenhum alerta encontrado.</td></tr>`;
    return alerts.map(a => `
        <tr data-alert-id="${a.id}">
            <td><span class="badge ${a.severity === 'critical' ? 'badge-critical' : a.severity === 'warning' ? 'badge-warning' : 'badge-success'}">
                ${a.severity === 'critical' ? 'Crítico' : a.severity === 'warning' ? 'Aviso' : a.severity === 'resolved' ? 'Resolvido' : 'Info'}
            </span></td>
            <td><div style="font-weight:600;">${a.title}</div><div style="font-size:0.875rem;color:var(--text-secondary);">${a.description}</div></td>
            <td>${a.device}</td>
            <td>${a.time}</td>
            <td>${a.resolvedAt || '--'}</td>
            <td>
                <div class="device-actions">
                    ${a.severity !== 'resolved' ? `
                        <button class="action-btn" title="Resolver" onclick="resolveAlert(${a.id})"><i class="fas fa-check"></i></button>
                        <button class="action-btn" title="Ignorar"  onclick="ignoreAlert(${a.id})"><i class="fas fa-times"></i></button>
                    ` : ''}
                    <button class="action-btn" title="Detalhes" onclick="viewAlertDetails(${a.id})"><i class="fas fa-eye"></i></button>
                </div>
            </td>
        </tr>`).join('');
}

function renderMonitoringParamRows(params) {
    if (!params.length) return `<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:2rem;">Nenhum parâmetro configurado. Clique em <strong>Novo Parâmetro</strong> para começar.</td></tr>`;
    return params.map(p => {
        const def = MONITORING_PARAM_TYPES[p.paramType] || {};
        const sevColor = p.severity === 'critical' ? 'var(--danger-color)' : p.severity === 'warning' ? 'var(--warning-color)' : 'var(--secondary-color)';
        const condLabel = def.hasThreshold
            ? `<code style="background:var(--bg-base);padding:0.15rem 0.45rem;border-radius:4px;font-size:0.8rem;">${p.operator} ${p.threshold} ${p.unit}</code>`
            : `<span style="font-size:0.8rem;color:var(--text-muted);">baseado em evento</span>`;
        const durationLabel = p.duration > 0 ? `<div style="font-size:0.7rem;color:var(--text-muted);margin-top:0.2rem;">por ${p.duration} min</div>` : '';
        return `
        <tr data-param-id="${p.id}">
            <td>
                <div style="display:flex;align-items:center;gap:0.6rem;">
                    <i class="fas ${def.icon || 'fa-bell'}" style="color:${sevColor};font-size:0.95rem;flex-shrink:0;"></i>
                    <div>
                        <div style="font-weight:600;">${p.name}</div>
                        <div style="font-size:0.75rem;color:var(--text-muted);">${def.label || p.paramType}</div>
                    </div>
                </div>
            </td>
            <td style="font-size:0.875rem;">${p.target === 'all' ? 'Todos' : p.target}</td>
            <td>${condLabel}${durationLabel}</td>
            <td><span class="badge ${p.severity === 'critical' ? 'badge-critical' : p.severity === 'warning' ? 'badge-warning' : 'badge-success'}">${p.severity === 'critical' ? 'Crítico' : p.severity === 'warning' ? 'Aviso' : 'Info'}</span></td>
            <td style="font-size:0.8rem;color:var(--text-secondary);">${p.action}</td>
            <td>
                <div style="display:flex;flex-direction:column;gap:0.2rem;">
                    <span class="badge ${p.active ? 'badge-success' : ''}" style="${!p.active ? 'background:rgba(100,116,139,0.15);color:#64748b;border:1px solid rgba(100,116,139,0.3);' : ''}">${p.active ? 'Ativo' : 'Inativo'}</span>
                    ${p.triggerCount > 0 ? `<span style="font-size:0.7rem;color:var(--text-muted);">${p.triggerCount}× disparado</span>` : ''}
                </div>
            </td>
            <td>
                <div class="device-actions">
                    <button class="action-btn" title="Editar" onclick="editMonitoringParam(${p.id})"><i class="fas fa-edit"></i></button>
                    <button class="action-btn" title="${p.active ? 'Desativar' : 'Ativar'}" onclick="toggleMonitoringParam(${p.id})">
                        <i class="fas ${p.active ? 'fa-toggle-on' : 'fa-toggle-off'}"></i>
                    </button>
                    <button class="action-btn" title="Remover" style="color:var(--danger-color);" onclick="removeMonitoringParam(${p.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>`;
    }).join('');
}

function _refreshAlertViews() {
    const tbody = document.getElementById('alerts-table-body');
    if (tbody) {
        tbody.innerHTML = renderAlertRows(_alerts);
        const count = document.getElementById('alerts-count');
        const badge = document.getElementById('alerts-critical-count');
        if (count) count.innerHTML = `Mostrando <strong>${_alerts.length}</strong> alerta(s)`;
        if (badge) badge.textContent = `${_alerts.filter(a => a.severity === 'critical').length} Críticos`;
    }
}

function applyAlertFilters() {
    const filter = AppState.currentAlertFilter;
    const query  = (document.getElementById('alert-search')?.value || '').toLowerCase().trim();
    let alerts   = _alerts;
    if (filter !== 'all') alerts = alerts.filter(a => a.severity === filter);
    if (query)            alerts = alerts.filter(a =>
        a.title.toLowerCase().includes(query) ||
        a.description.toLowerCase().includes(query) ||
        a.device.toLowerCase().includes(query)
    );
    const tbody = document.getElementById('alerts-table-body');
    const count = document.getElementById('alerts-count');
    if (tbody) tbody.innerHTML = renderAlertRows(alerts);
    if (count) count.innerHTML = `Mostrando <strong>${alerts.length}</strong> alerta(s)`;
}

async function resolveAlert(id) {
    await API.resolveAlert(id);
    _alerts = _alerts.map(a => a.id === id ? { ...a, severity: 'resolved', resolvedAt: new Date().toLocaleString('pt-BR') } : a);
    showToast('Alerta resolvido.', 'success');
    applyAlertFilters();
}

async function ignoreAlert(id) {
    await API.deleteAlert(id);
    _alerts = _alerts.filter(a => a.id !== id);
    showToast('Alerta removido.', 'warning');
    applyAlertFilters();
}

function viewAlertDetails(id) {
    const a = _alerts.find(x => x.id === id);
    if (!a) return;
    openModal('Detalhes do Alerta', `
        <div style="display:flex;flex-direction:column;gap:1rem;">
            <div><div style="color:var(--text-secondary);font-size:0.8rem;margin-bottom:0.25rem;">TÍTULO</div><div style="font-weight:600;">${a.title}</div></div>
            <div><div style="color:var(--text-secondary);font-size:0.8rem;margin-bottom:0.25rem;">DESCRIÇÃO</div><div>${a.description}</div></div>
            <div><div style="color:var(--text-secondary);font-size:0.8rem;margin-bottom:0.25rem;">DISPOSITIVO</div><div>${a.device}</div></div>
            <div><div style="color:var(--text-secondary);font-size:0.8rem;margin-bottom:0.25rem;">STATUS</div>
                <span class="badge ${a.severity === 'critical' ? 'badge-critical' : a.severity === 'warning' ? 'badge-warning' : 'badge-success'}">
                    ${a.severity === 'resolved' ? 'Resolvido' : a.severity === 'critical' ? 'Crítico' : a.severity === 'warning' ? 'Aviso' : 'Info'}
                </span>
            </div>
            <div><div style="color:var(--text-secondary);font-size:0.8rem;margin-bottom:0.5rem;">RECOMENDAÇÕES</div>
                <div style="background:var(--bg-base);padding:1rem;border-radius:8px;color:var(--text-secondary);font-size:0.875rem;line-height:1.8;">
                    1. Verificar conexões físicas<br>
                    2. Reiniciar o equipamento se necessário<br>
                    3. Contatar suporte técnico se persistir
                </div>
            </div>
        </div>
    `, 'Fechar', closeModal);
}

// ── Parâmetros de Monitoramento ───────────────────────────────────────────────
function openMonitoringParamModal(paramId = null) {
    const param  = paramId ? _monitoringParams.find(p => p.id === paramId) : null;
    const isEdit = !!param;

    const typeOptions = Object.entries(MONITORING_PARAM_TYPES).map(([key, def]) =>
        `<option value="${key}" ${param?.paramType === key ? 'selected' : ''}>${def.label}</option>`
    ).join('');

    const actionOptions = ['Email', 'Telegram', 'Email + Telegram', 'Dashboard', 'Alerta Dashboard + Telegram', 'SMS', 'Email + SMS + Telegram']
        .map(a => `<option ${param?.action === a ? 'selected' : ''}>${a}</option>`).join('');

    openModal(isEdit ? 'Editar Parâmetro de Monitoramento' : 'Novo Parâmetro de Monitoramento', `
        <div class="form-group">
            <label class="form-label">Tipo de Parâmetro *</label>
            <select class="form-control" id="mp-type" onchange="onMonitoringParamTypeChange()">${typeOptions}</select>
        </div>
        <div id="mp-type-desc" style="background:var(--bg-base);padding:0.65rem 0.85rem;border-radius:6px;margin-bottom:1rem;font-size:0.8rem;color:var(--text-secondary);border-left:3px solid var(--primary-color);">
            <i class="fas fa-info-circle" style="margin-right:0.4rem;"></i><span id="mp-type-desc-text"></span>
        </div>
        <div class="form-group">
            <label class="form-label">Nome *</label>
            <input type="text" class="form-control" id="mp-name" value="${param?.name || ''}" placeholder="Ex: Sinal Óptico Crítico">
        </div>
        <div class="form-group">
            <label class="form-label">Dispositivo Alvo</label>
            <select class="form-control" id="mp-target"><option value="all">Todos os dispositivos</option></select>
        </div>
        <div id="mp-threshold-group" class="form-group">
            <label class="form-label">Limiar — <span id="mp-threshold-desc" style="color:var(--text-muted);font-weight:400;"></span></label>
            <div style="display:flex;align-items:center;gap:0.6rem;">
                <span id="mp-operator" style="font-family:monospace;font-size:1.25rem;font-weight:700;color:var(--text-secondary);min-width:18px;text-align:center;"></span>
                <input type="number" class="form-control" id="mp-threshold" value="${param?.threshold ?? ''}" step="0.1" style="flex:1;max-width:140px;">
                <span id="mp-unit" style="color:var(--text-secondary);white-space:nowrap;min-width:30px;font-weight:600;"></span>
            </div>
        </div>
        <div class="form-group">
            <label class="form-label">Duração mínima</label>
            <div style="display:flex;align-items:center;gap:0.6rem;">
                <input type="number" class="form-control" id="mp-duration" value="${param?.duration ?? 0}" min="0" max="60" style="width:90px;">
                <span style="color:var(--text-secondary);font-size:0.875rem;">minutos &nbsp;·&nbsp; 0 = disparo imediato</span>
            </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
            <div class="form-group" style="margin:0;">
                <label class="form-label">Severidade</label>
                <select class="form-control" id="mp-severity">
                    <option value="critical" ${param?.severity === 'critical' ? 'selected' : ''}>Crítico</option>
                    <option value="warning"  ${param?.severity === 'warning'  ? 'selected' : ''}>Aviso</option>
                    <option value="info"     ${param?.severity === 'info'     ? 'selected' : ''}>Info</option>
                </select>
            </div>
            <div class="form-group" style="margin:0;">
                <label class="form-label">Ação</label>
                <select class="form-control" id="mp-action">${actionOptions}</select>
            </div>
        </div>
    `, isEdit ? 'Salvar Alterações' : 'Criar Parâmetro', () => _saveMonitoringParam(paramId));

    onMonitoringParamTypeChange(param);

    API.getDevices().then(devices => {
        const sel = document.getElementById('mp-target');
        if (sel && devices) {
            const options = ['all', ...devices.map(d => d.name)];
            sel.innerHTML = options.map(t => `<option value="${t}" ${(param?.target || 'all') === t ? 'selected' : ''}>${t === 'all' ? 'Todos os dispositivos' : t}</option>`).join('');
        }
    }).catch(() => {});
}

function onMonitoringParamTypeChange(existingParam = null) {
    const typeEl = document.getElementById('mp-type');
    if (!typeEl) return;
    const def = MONITORING_PARAM_TYPES[typeEl.value];
    if (!def) return;

    const descText    = document.getElementById('mp-type-desc-text');
    const threshGroup = document.getElementById('mp-threshold-group');
    const threshDesc  = document.getElementById('mp-threshold-desc');
    const operatorEl  = document.getElementById('mp-operator');
    const thresholdEl = document.getElementById('mp-threshold');
    const unitEl      = document.getElementById('mp-unit');
    const nameEl      = document.getElementById('mp-name');
    const severityEl  = document.getElementById('mp-severity');

    if (descText) descText.textContent = def.description;
    if (threshGroup) threshGroup.style.display = def.hasThreshold ? '' : 'none';

    if (def.hasThreshold) {
        if (operatorEl) operatorEl.textContent = def.operator;
        if (unitEl)     unitEl.textContent      = def.unit;
        if (threshDesc) threshDesc.textContent  = `valor ${def.operator === '<' ? 'mínimo aceitável' : 'máximo aceitável'}`;
        if (thresholdEl && !thresholdEl.value && !existingParam) thresholdEl.value = def.defaultThreshold;
    }

    if (nameEl && !nameEl.value) nameEl.value = def.label;
    if (severityEl && !existingParam) severityEl.value = def.defaultSeverity;
}

async function _saveMonitoringParam(paramId) {
    const type     = document.getElementById('mp-type')?.value;
    const name     = document.getElementById('mp-name')?.value?.trim();
    const target   = document.getElementById('mp-target')?.value || 'all';
    const duration = parseInt(document.getElementById('mp-duration')?.value || '0', 10);
    const severity = document.getElementById('mp-severity')?.value;
    const action   = document.getElementById('mp-action')?.value;

    if (!type || !name) { showToast('Preencha o tipo e o nome do parâmetro.', 'warning'); return; }

    const def = MONITORING_PARAM_TYPES[type];
    let threshold = null, operator = null, unit = null;
    if (def.hasThreshold) {
        threshold = parseFloat(document.getElementById('mp-threshold')?.value);
        if (isNaN(threshold)) { showToast('Informe um valor de limiar válido.', 'warning'); return; }
        operator = def.operator;
        unit     = def.unit;
    }

    const fields = { name, paramType: type, target, operator, threshold, unit, duration, severity, action };

    if (paramId) {
        const updated = await API.updateMonitoringParam(paramId, fields);
        _monitoringParams = _monitoringParams.map(p => p.id === paramId ? updated : p);
        showToast(`Parâmetro "${name}" atualizado.`, 'success');
    } else {
        const created = await API.addMonitoringParam(fields);
        _monitoringParams.push(created);
        showToast(`Parâmetro "${name}" criado.`, 'success');
    }

    closeModal();
    const tbody = document.getElementById('monitoring-params-body');
    if (tbody) tbody.innerHTML = renderMonitoringParamRows(_monitoringParams);
}

function editMonitoringParam(id) { openMonitoringParamModal(id); }

async function toggleMonitoringParam(id) {
    const updated = await API.toggleMonitoringParam(id);
    _monitoringParams = _monitoringParams.map(p => p.id === id ? updated : p);
    const tbody = document.getElementById('monitoring-params-body');
    if (tbody) tbody.innerHTML = renderMonitoringParamRows(_monitoringParams);
    showToast('Status do parâmetro atualizado.', 'info');
}

function removeMonitoringParam(id) {
    openModal('Remover Parâmetro', `<p>Tem certeza que deseja remover este parâmetro de monitoramento?</p>`, 'Remover', async () => {
        await API.deleteMonitoringParam(id);
        _monitoringParams = _monitoringParams.filter(p => p.id !== id);
        closeModal();
        const tbody = document.getElementById('monitoring-params-body');
        if (tbody) tbody.innerHTML = renderMonitoringParamRows(_monitoringParams);
        showToast('Parâmetro removido.', 'warning');
    });
}

document.addEventListener('DOMContentLoaded', function () {
    (async () => {
        _alerts = await API.getAllAlerts() || [];
        _refreshAlertViews();
    })();

    (async () => {
        _monitoringParams = await API.getMonitoringParams() || [];
    })();

    (async () => {
        const [traps, statsRes] = await Promise.all([API.getTraps(), API.getTrapStats()]);
        const stats = statsRes?.data ?? statsRes;
        const placeholder = document.getElementById('traps-section-placeholder');
        if (placeholder) {
            placeholder.outerHTML = renderTrapsSection(traps, stats);
            document.getElementById('trap-filter-severity')?.addEventListener('change', filterTraps);
            document.getElementById('trap-filter-type')?.addEventListener('change', filterTraps);
        }
        if (stats) updateTrapBadge(stats);
    })();

    document.querySelectorAll('.filter-bar .filter-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.filter-bar .filter-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            AppState.currentAlertFilter = this.getAttribute('data-filter');
            applyAlertFilters();
        });
    });

    document.getElementById('alert-search')?.addEventListener('input', applyAlertFilters);
    document.getElementById('new-monitoring-param-btn')?.addEventListener('click', () => openMonitoringParamModal());
});
