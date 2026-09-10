// ===== HISTÓRICO =====
let _historyItems = [];

function renderHistoryRows(items) {
    if (!items.length) return `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:2rem;">Nenhum evento encontrado.</td></tr>`;
    return items.map(item => `
        <tr>
            <td style="font-size:0.875rem;">${item.time}</td>
            <td><div style="font-weight:600;">${item.event}</div><div style="font-size:0.75rem;color:var(--text-muted);">ID: ${item.id}</div></td>
            <td>${item.device}</td>
            <td>${item.duration || '--'}</td>
            <td style="font-size:0.875rem;color:var(--text-secondary);">${item.action || '--'}</td>
            <td>${item.user || 'Sistema'}</td>
        </tr>`).join('');
}

function renderBackupOptions(backups) {
    if (!backups.length) return `<option value="">Nenhum backup disponível</option>`;
    return backups.map(b => `<option value="${b.id}">${b.filename} — ${b.date} (${b.size})</option>`).join('');
}

async function _performRestore(id, filename) {
    closeModal();
    showToast(`Restaurando backup${filename ? ' "' + filename + '"' : ''}...`, 'warning');
    const result = await API.restoreBackup(id);
    if (result) {
        showToast(`Backup${filename ? ' "' + filename + '"' : ''} restaurado com sucesso!`, 'success');
        window.location.reload();
    } else {
        showToast('Erro ao restaurar backup. Verifique o servidor.', 'error');
    }
}

function quickRestoreBackup(id) {
    const select = document.getElementById('backup-select');
    const opt = select ? Array.from(select.options).find(o => o.value == id) : null;
    openModal('Confirmar Restauração', `
        <div style="text-align:center;padding:1rem;">
            <i class="fas fa-exclamation-triangle" style="font-size:2.5rem;color:var(--warning-color);margin-bottom:1rem;display:block;"></i>
            <p>Restaurar este backup?</p>
            <p style="color:var(--text-secondary);font-size:0.875rem;margin-top:0.5rem;">Esta ação substituirá os dados atuais.</p>
        </div>
    `, 'Restaurar', () => _performRestore(id, opt?.textContent));
}

function removeBackup(id) {
    openModal('Remover Backup', `<p>Tem certeza que deseja remover este backup?</p><p style="color:var(--text-secondary);font-size:0.875rem;">Esta ação não pode ser desfeita.</p>`, 'Remover', async () => {
        await API.deleteBackup(id);
        showToast('Backup removido.', 'warning');
        closeModal();
        window.location.reload();
    });
}

document.addEventListener('DOMContentLoaded', function () {
    const applyHistoryFilters = () => {
        const query  = (document.getElementById('history-search')?.value || '').toLowerCase().trim();
        const type   = document.getElementById('history-filter-type')?.value   || '';
        const period = document.getElementById('history-filter-period')?.value || '';
        let items    = _historyItems;

        if (query) items = items.filter(i =>
            (i.event  || '').toLowerCase().includes(query) ||
            (i.device || '').toLowerCase().includes(query) ||
            (i.action || '').toLowerCase().includes(query)
        );
        if (type) items = items.filter(i => i.type === type);
        if (period) {
            if (period === 'today') {
                const today = new Date().toLocaleDateString('pt-BR');
                items = items.filter(i => String(i.time).includes(today));
            } else {
                const cutoff = Date.now() - parseInt(period) * 86400000;
                items = items.filter(i => {
                    const d = new Date(i.time);
                    return isNaN(d.getTime()) || d.getTime() >= cutoff;
                });
            }
        }

        const tbody = document.getElementById('history-table-body');
        const count = document.getElementById('history-count');
        if (tbody) tbody.innerHTML = renderHistoryRows(items);
        if (count) count.innerHTML = `Mostrando <strong>${items.length}</strong> evento(s)`;
    };

    document.getElementById('history-search')?.addEventListener('input', applyHistoryFilters);
    document.getElementById('history-filter-type')?.addEventListener('change', applyHistoryFilters);
    document.getElementById('history-filter-period')?.addEventListener('change', applyHistoryFilters);
    document.getElementById('apply-history-filters')?.addEventListener('click', applyHistoryFilters);

    (async () => {
        _historyItems = await API.getAppHistory() || [];
        applyHistoryFilters();
    })();

    document.getElementById('export-history-btn')?.addEventListener('click', () => {
        openModal('Exportar Histórico', `
            <div class="form-group">
                <label class="form-label">Formato</label>
                <select class="form-control" id="export-format">
                    <option value="csv">CSV (Excel)</option>
                    <option value="json">JSON</option>
                    <option value="pdf">PDF (Impressão)</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Período</label>
                <select class="form-control" id="export-period">
                    <option value="7">Últimos 7 dias</option>
                    <option value="30" selected>Últimos 30 dias</option>
                    <option value="90">Últimos 90 dias</option>
                    <option value="all">Todo o histórico</option>
                </select>
            </div>
            <div style="color:var(--text-secondary);font-size:0.875rem;margin-top:1rem;">
                <i class="fas fa-info-circle" style="margin-right:0.5rem;"></i>
                CSV e JSON serão baixados automaticamente. PDF abrirá para impressão.
            </div>
        `, 'Exportar', () => {
            const format = document.getElementById('export-format')?.value;
            const period = document.getElementById('export-period')?.value;
            exportData(format, period, 'history');
            showToast(`Exportação ${format.toUpperCase()} iniciada!`, 'success');
            closeModal();
        });
    });

    document.getElementById('create-backup-btn')?.addEventListener('click', async function () {
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Criando backup...';
        this.disabled  = true;
        const backup = await API.createBackup();
        this.innerHTML = '<i class="fas fa-database"></i> Criar Backup Agora';
        this.disabled  = false;
        if (backup) {
            showToast(`Backup criado: ${backup.filename} (${backup.size})`, 'success');
            window.location.reload();
        } else {
            showToast('Erro ao criar backup. Verifique o servidor.', 'error');
        }
    });

    document.getElementById('restore-backup-btn')?.addEventListener('click', () => {
        const select   = document.getElementById('backup-select');
        const backupId = parseInt(select?.value);
        if (!backupId) { showToast('Selecione um backup para restaurar.', 'warning'); return; }
        const opt = Array.from(select.options).find(o => o.value == backupId);
        openModal('Confirmar Restauração', `
            <div style="text-align:center;padding:1rem;">
                <i class="fas fa-exclamation-triangle" style="font-size:2.5rem;color:var(--warning-color);margin-bottom:1rem;display:block;"></i>
                <p>Restaurar o backup <strong>${opt?.textContent}</strong>?</p>
                <p style="color:var(--text-secondary);font-size:0.875rem;margin-top:0.5rem;">
                    Os dados atuais de dispositivos, alertas, regras e configurações serão substituídos pelos dados do backup.
                </p>
            </div>
        `, 'Restaurar', () => _performRestore(backupId, opt?.textContent));
    });
});
