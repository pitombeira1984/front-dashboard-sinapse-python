// ===== SINAPSE — TRAP UI =====
const TRAP_SEVERITY_STYLE = {
    critical: { color: 'var(--danger-color)',  bg: 'rgba(220,38,38,0.1)',   border: 'rgba(220,38,38,0.3)',   icon: 'fa-exclamation-circle' },
    warning:  { color: 'var(--warning-color)', bg: 'rgba(245,158,11,0.1)',  border: 'rgba(245,158,11,0.3)',  icon: 'fa-exclamation-triangle' },
    info:     { color: 'var(--secondary-color)',bg: 'rgba(14,165,233,0.1)', border: 'rgba(14,165,233,0.3)',  icon: 'fa-info-circle' },
};

function updateTrapBadge(stats) {
    const count = stats?.unacknowledged || 0;
    const alertsNavItem = document.querySelector('.nav-item[data-page="alerts"]');
    if (!alertsNavItem) return;

    let badge = alertsNavItem.querySelector('.trap-badge');
    if (!badge) {
        badge = document.createElement('span');
        badge.className = 'trap-badge';
        badge.style.cssText = `
            display: inline-flex; align-items: center; justify-content: center;
            min-width: 18px; height: 18px; padding: 0 5px;
            background: var(--danger-color); color: white;
            border-radius: 9px; font-size: 0.7rem; font-weight: 700;
            margin-left: auto; line-height: 1;
        `;
        alertsNavItem.style.justifyContent = 'space-between';
        alertsNavItem.appendChild(badge);
    }

    if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.style.display = 'inline-flex';
    } else {
        badge.style.display = 'none';
    }
}

function showTrapToast(trap) {
    const style = TRAP_SEVERITY_STYLE[trap.severity] || TRAP_SEVERITY_STYLE.info;
    const existing = document.getElementById('sinapse-trap-toast');
    if (existing) existing.remove();

    if (!document.getElementById('toast-style')) {
        const s = document.createElement('style');
        s.id = 'toast-style';
        s.textContent = `
            @keyframes toastIn  { from { opacity:0; transform:translateX(20px); } to { opacity:1; transform:translateX(0); } }
            @keyframes toastOut { from { opacity:1; transform:translateX(0);    } to { opacity:0; transform:translateX(20px); } }
        `;
        document.head.appendChild(s);
    }

    const toast = document.createElement('div');
    toast.id = 'sinapse-trap-toast';
    toast.style.cssText = `
        position:fixed; bottom:2rem; right:2rem; z-index:9999;
        background:var(--bg-card); border:1px solid var(--border-color);
        border-left:4px solid ${style.color};
        border-radius:8px; padding:0.875rem 1.25rem;
        display:flex; flex-direction:column; gap:0.25rem;
        color:var(--text-primary); font-size:0.875rem;
        box-shadow:0 8px 32px rgba(0,0,0,0.5);
        animation:toastIn 0.3s ease; max-width:380px; min-width:300px;
        cursor:pointer;
    `;
    toast.innerHTML = `
        <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.25rem;">
            <i class="fas fa-broadcast-tower" style="color:${style.color};font-size:0.9rem;"></i>
            <span style="font-weight:700;font-size:0.8rem;color:${style.color};text-transform:uppercase;letter-spacing:0.05em;">
                SNMP Trap Recebido
            </span>
            <span style="margin-left:auto;font-size:0.75rem;color:var(--text-muted);">${trap.time?.split(' ')[1] || 'agora'}</span>
        </div>
        <div style="font-weight:600;">${trap.label}</div>
        <div style="color:var(--text-secondary);font-size:0.8rem;">${trap.description}</div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:0.25rem;">
            <span style="font-size:0.75rem;color:var(--text-muted);">
                <i class="fas fa-server" style="margin-right:0.25rem;"></i>${trap.device}
            </span>
            <span style="font-size:0.7rem;color:#475569;">OID: ${trap.oid}</span>
        </div>
    `;

    toast.addEventListener('click', () => { window.location.href = '/alerts'; });
    document.body.appendChild(toast);

    const duration = trap.severity === 'critical' ? 8000 : 5000;
    setTimeout(() => {
        if (!document.getElementById('sinapse-trap-toast')) return;
        toast.style.animation = 'toastOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

function renderTrapRow(trap) {
    const style = TRAP_SEVERITY_STYLE[trap.severity] || TRAP_SEVERITY_STYLE.info;
    return `
        <tr data-trap-id="${trap.id}" style="${trap.acknowledged ? 'opacity:0.6;' : ''}">
            <td>
                <span class="badge" style="background:${style.bg};color:${style.color};border:1px solid ${style.border};">
                    <i class="fas ${style.icon}" style="margin-right:0.25rem;font-size:0.7rem;"></i>
                    ${trap.severity === 'critical' ? 'Crítico' : trap.severity === 'warning' ? 'Aviso' : 'Info'}
                </span>
            </td>
            <td>
                <div style="font-weight:600;display:flex;align-items:center;gap:0.5rem;">
                    <i class="fas fa-broadcast-tower" style="color:${style.color};font-size:0.8rem;"></i>
                    ${trap.label}
                    ${!trap.acknowledged ? '<span style="font-size:0.65rem;background:var(--danger-color);color:white;padding:1px 6px;border-radius:4px;margin-left:0.25rem;">NOVO</span>' : ''}
                </div>
                <div style="font-size:0.8rem;color:var(--text-secondary);margin-top:0.2rem;">${trap.description}</div>
                <div style="font-size:0.7rem;color:#475569;margin-top:0.2rem;font-family:monospace;">OID: ${trap.oid}</div>
            </td>
            <td style="font-size:0.875rem;">${trap.device}<br><span style="font-size:0.75rem;color:var(--text-muted);">${trap.agentAddr}</span></td>
            <td style="font-size:0.8rem;color:var(--text-secondary);">${trap.rfc?.split(' — ')[0] || '--'}</td>
            <td style="font-size:0.875rem;">${trap.time}</td>
            <td>
                <div class="device-actions">
                    ${!trap.acknowledged ? `
                        <button class="action-btn" title="Reconhecer" onclick="acknowledgeTrap('${trap.id}')">
                            <i class="fas fa-check"></i>
                        </button>
                    ` : '<span style="color:#10b981;font-size:0.75rem;"><i class="fas fa-check-circle"></i> OK</span>'}
                    <button class="action-btn" title="Detalhes" onclick="viewTrapDetails('${trap.id}')">
                        <i class="fas fa-eye"></i>
                    </button>
                </div>
            </td>
        </tr>
    `;
}

function renderTrapsTable(traps) {
    if (!traps || !traps.length) {
        return `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:2rem;">
            <i class="fas fa-broadcast-tower" style="font-size:2rem;display:block;margin-bottom:0.5rem;"></i>
            Nenhum SNMP Trap recebido ainda.
        </td></tr>`;
    }
    return traps.map(renderTrapRow).join('');
}

function renderTrapSummaryCard(stats) {
    if (!stats) return '';
    const last = stats.lastTrap;
    return `
        <div class="card" id="trap-summary-card">
            <div class="section-header">
                <h2 class="section-title">
                    <i class="fas fa-broadcast-tower" style="color:var(--primary-color);margin-right:0.5rem;"></i>
                    SNMP Traps
                </h2>
                <div style="display:flex;gap:0.5rem;align-items:center;">
                    ${stats.critical > 0 ? `<div class="badge badge-critical">${stats.critical} Crítico${stats.critical > 1 ? 's' : ''}</div>` : ''}
                    ${stats.unacknowledged > 0 ? `<div class="badge badge-warning">${stats.unacknowledged} Pendente${stats.unacknowledged > 1 ? 's' : ''}</div>` : '<div class="badge badge-success">Todos reconhecidos</div>'}
                    <a class="btn btn-secondary" style="font-size:0.8rem;padding:0.35rem 0.75rem;" href="/alerts">
                        Ver todos <i class="fas fa-arrow-right" style="margin-left:0.25rem;"></i>
                    </a>
                </div>
            </div>

            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:1rem;margin-bottom:1.5rem;">
                ${[
                    ['Total', stats.total,          '#94a3b8',              'fa-list'],
                    ['Críticos', stats.critical,    'var(--danger-color)',   'fa-exclamation-circle'],
                    ['Avisos',   stats.warning,     'var(--warning-color)',  'fa-exclamation-triangle'],
                    ['Pendentes',stats.unacknowledged,'var(--warning-color)','fa-bell'],
                ].map(([label, val, color, icon]) => `
                    <div style="background:rgba(30,41,59,0.6);padding:1rem;border-radius:8px;text-align:center;">
                        <i class="fas ${icon}" style="color:${color};font-size:1.25rem;display:block;margin-bottom:0.5rem;"></i>
                        <div style="font-size:1.5rem;font-weight:700;color:${color};">${val}</div>
                        <div style="font-size:0.75rem;color:var(--text-secondary);">${label}</div>
                    </div>
                `).join('')}
            </div>

            ${last ? `
                <div style="background:rgba(30,41,59,0.4);padding:1rem;border-radius:8px;border-left:3px solid ${(TRAP_SEVERITY_STYLE[last.severity] || TRAP_SEVERITY_STYLE.info).color};">
                    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">ÚLTIMO TRAP RECEBIDO</div>
                    <div style="display:flex;align-items:center;gap:0.75rem;">
                        <i class="fas fa-broadcast-tower" style="color:${(TRAP_SEVERITY_STYLE[last.severity] || TRAP_SEVERITY_STYLE.info).color};font-size:1.1rem;"></i>
                        <div style="flex:1;">
                            <div style="font-weight:600;">${last.label}</div>
                            <div style="font-size:0.8rem;color:var(--text-secondary);">${last.device} • ${last.time}</div>
                        </div>
                        ${!last.acknowledged ? `<button class="btn btn-secondary" style="font-size:0.8rem;" onclick="acknowledgeTrap('${last.id}')"><i class="fas fa-check"></i> OK</button>` : '<span style="color:#10b981;font-size:0.875rem;"><i class="fas fa-check-circle"></i> Reconhecido</span>'}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

function renderTrapsSection(traps, stats) {
    const unack = stats?.unacknowledged || 0;
    return `
        <div class="card" id="traps-section">
            <div class="section-header">
                <h2 class="section-title">
                    <i class="fas fa-broadcast-tower" style="color:var(--primary-color);margin-right:0.5rem;"></i>
                    SNMP Traps Recebidos
                    ${unack > 0 ? `<span class="badge badge-critical" style="margin-left:0.5rem;">${unack} pendente${unack > 1 ? 's' : ''}</span>` : ''}
                </h2>
                <div style="display:flex;gap:0.5rem;align-items:center;flex-wrap:wrap;">
                    <select id="trap-filter-severity" class="form-control" style="width:140px;">
                        <option value="">Todos</option>
                        <option value="critical">Críticos</option>
                        <option value="warning">Avisos</option>
                        <option value="info">Info</option>
                    </select>
                    <select id="trap-filter-type" class="form-control" style="width:180px;">
                        <option value="">Todos os tipos</option>
                        <option value="coldStart">coldStart</option>
                        <option value="warmStart">warmStart</option>
                        <option value="linkDown">linkDown</option>
                        <option value="linkUp">linkUp</option>
                        <option value="authenticationFailure">authFailure</option>
                        <option value="opticalDegradation">opticalDegradation</option>
                        <option value="highTemperature">highTemperature</option>
                        <option value="highCPU">highCPU</option>
                    </select>
                    <button class="btn btn-secondary" style="font-size:0.875rem;" onclick="filterTraps()">
                        <i class="fas fa-filter"></i> Filtrar
                    </button>
                    ${unack > 0 ? `
                        <button class="btn btn-primary" style="font-size:0.875rem;" onclick="acknowledgeAllTrapsUI()">
                            <i class="fas fa-check-double"></i> Reconhecer Todos
                        </button>
                    ` : ''}
                </div>
            </div>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Severidade</th><th>Trap</th><th>Dispositivo</th><th>RFC/MIB</th><th>Recebido em</th><th>Ações</th>
                        </tr>
                    </thead>
                    <tbody id="traps-table-body">${renderTrapsTable(traps)}</tbody>
                </table>
            </div>

            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:1.5rem;">
                <div style="color:var(--text-secondary);font-size:0.875rem;" id="traps-count">
                    Mostrando <strong>${traps?.length || 0}</strong> trap(s)
                </div>
                <div style="display:flex;gap:1rem;font-size:0.8rem;color:var(--text-muted);">
                    ${stats ? Object.entries(stats.counters || {}).filter(([,v])=>v>0).map(([k,v])=>`<span>${k}: <strong style="color:var(--text-secondary);">${v}</strong></span>`).join(' • ') : ''}
                </div>
            </div>
        </div>
    `;
}

async function acknowledgeTrap(id) {
    await API.acknowledgeTraps([id]);
    const row = document.querySelector(`tr[data-trap-id="${id}"]`);
    if (row) {
        const newBadgeCell = row.querySelector('td:last-child');
        if (newBadgeCell) newBadgeCell.innerHTML = '<span style="color:#10b981;font-size:0.75rem;"><i class="fas fa-check-circle"></i> OK</span>';
        row.style.opacity = '0.6';
        const novoBadge = row.querySelector('span[style*="danger"]');
        if (novoBadge) novoBadge.remove();
    }
    const res = await API.getTrapStats();
    const stats = res?.data ?? res;
    if (stats) updateTrapBadge(stats);
    showToast('Trap reconhecido.', 'success');
}

async function acknowledgeAllTrapsUI() {
    await API.acknowledgeAllTraps();
    showToast('Todos os traps reconhecidos.', 'success');
    const traps = await API.getTraps();
    const res = await API.getTrapStats();
    const stats = res?.data ?? res;
    const tbody = document.getElementById('traps-table-body');
    const count = document.getElementById('traps-count');
    if (tbody && traps) tbody.innerHTML = renderTrapsTable(traps);
    if (count && traps) count.innerHTML = `Mostrando <strong>${traps.length}</strong> trap(s)`;
    if (stats) updateTrapBadge(stats);
}

async function filterTraps() {
    const severity = document.getElementById('trap-filter-severity')?.value || '';
    const type     = document.getElementById('trap-filter-type')?.value     || '';
    const filters = {};
    if (severity) filters.severity = severity;
    if (type)     filters.type     = type;

    const traps = await API.getTraps(filters);
    const tbody = document.getElementById('traps-table-body');
    const count = document.getElementById('traps-count');
    if (tbody) tbody.innerHTML = renderTrapsTable(traps);
    if (count) count.innerHTML = `Mostrando <strong>${traps?.length || 0}</strong> trap(s)`;
}

async function viewTrapDetails(id) {
    const traps = await API.getTraps();
    const trap = traps?.find(t => t.id === id);
    if (!trap) return;

    const style = TRAP_SEVERITY_STYLE[trap.severity] || TRAP_SEVERITY_STYLE.info;
    const varbinds = trap.varbinds || {};

    openModal(`Detalhes do Trap — ${trap.label}`, `
        <div style="display:flex;flex-direction:column;gap:1rem;">
            <div style="display:flex;gap:1rem;align-items:center;padding:1rem;background:${style.bg};border-radius:8px;border:1px solid ${style.border};">
                <i class="fas ${trap.icon || style.icon}" style="color:${style.color};font-size:1.75rem;"></i>
                <div>
                    <div style="font-weight:700;font-size:1rem;">${trap.label}</div>
                    <div style="color:var(--text-secondary);font-size:0.875rem;">${trap.description}</div>
                </div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
                ${[
                    ['OID',        trap.oid],
                    ['Dispositivo',trap.device],
                    ['Agent Addr', trap.agentAddr],
                    ['Community',  trap.community],
                    ['Severidade', trap.severity],
                    ['Recebido',   trap.time],
                    ['Status',     trap.acknowledged ? 'Reconhecido' : 'Pendente'],
                    ['RFC/MIB',    trap.rfc],
                ].map(([k,v]) => `
                    <div style="background:var(--bg-base);padding:0.75rem;border-radius:6px;">
                        <div style="color:var(--text-muted);font-size:0.7rem;text-transform:uppercase;margin-bottom:0.25rem;">${k}</div>
                        <div style="font-size:0.875rem;word-break:break-all;">${v || '--'}</div>
                    </div>
                `).join('')}
            </div>

            ${Object.keys(varbinds).length > 0 ? `
                <div>
                    <div style="color:var(--text-muted);font-size:0.75rem;text-transform:uppercase;margin-bottom:0.75rem;letter-spacing:0.05em;">
                        Varbinds (Variáveis SNMP)
                    </div>
                    <div style="background:var(--bg-base);padding:1rem;border-radius:6px;font-family:monospace;font-size:0.8rem;line-height:2;">
                        ${Object.entries(varbinds).map(([k,v]) => `
                            <div style="display:flex;gap:1rem;">
                                <span style="color:#0ea5e9;min-width:180px;">${k}</span>
                                <span style="color:#10b981;">${JSON.stringify(v)}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `, 'Fechar', closeModal);
}
