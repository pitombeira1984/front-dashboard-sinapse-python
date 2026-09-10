// ===== CONFIGURAÇÕES =====
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.settings-nav .settings-tab').forEach(tab => {
        tab.addEventListener('click', function () {
            document.querySelectorAll('.settings-nav .settings-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            document.querySelectorAll('.settings-section').forEach(s => s.classList.remove('active'));
            document.getElementById(`settings-${this.getAttribute('data-tab')}`).classList.add('active');
            AppState.currentSettingsTab = this.getAttribute('data-tab');
        });
    });

    document.getElementById('save-settings-btn')?.addEventListener('click', async function () {
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
        this.disabled  = true;
        const settings = {
            nodeName:        document.getElementById('cfg-nodeName')?.value,
            timezone:        document.getElementById('cfg-timezone')?.value,
            language:        document.getElementById('cfg-language')?.value,
            pollingInterval: document.getElementById('cfg-pollingInterval')?.value,
            dataRetention:   document.getElementById('cfg-dataRetention')?.value,
            advancedMetrics: document.getElementById('cfg-advancedMetrics')?.checked,
            notifyEmail:     document.getElementById('cfg-notifyEmail')?.checked,
            notifyTelegram:  document.getElementById('cfg-notifyTelegram')?.checked,
            notifySMS:       document.getElementById('cfg-notifySMS')?.checked,
            email:           document.getElementById('cfg-email')?.value,
            ip:              document.getElementById('cfg-ip')?.value,
            mask:            document.getElementById('cfg-mask')?.value,
            gateway:         document.getElementById('cfg-gateway')?.value,
            dns1:            document.getElementById('cfg-dns1')?.value,
            dns2:            document.getElementById('cfg-dns2')?.value,
        };
        Object.keys(settings).forEach(k => settings[k] === undefined && delete settings[k]);
        const updated = await API.saveSettings(settings);
        if (updated) {
            window.SINAPSE_SETTINGS = updated;
            applyPollingIntervalFromSettings(updated.pollingInterval);
            const sidebarInfo = document.getElementById('sidebar-node-info');
            if (sidebarInfo) sidebarInfo.innerHTML = `${escHtml(updated.nodeName)}<br>${escHtml(updated.ip)}`;
        }

        this.innerHTML = '<i class="fas fa-save"></i> Salvar Configurações';
        this.disabled  = false;
        this.style.backgroundColor = 'var(--success-color)';
        setTimeout(() => { this.style.backgroundColor = ''; }, 1000);
        showToast('Configurações salvas com sucesso!', 'success');
    });

    document.getElementById('restart-services-btn')?.addEventListener('click', () => {
        openModal('Reiniciar Serviços', `
            <div style="text-align:center;padding:1rem;">
                <i class="fas fa-redo" style="font-size:2.5rem;color:var(--danger-color);margin-bottom:1rem;display:block;"></i>
                <p>Reiniciar os serviços de monitoramento (polling SNMP e traps)?</p>
                <p style="color:var(--text-secondary);font-size:0.875rem;margin-top:0.5rem;">A coleta de métricas é interrompida por alguns segundos durante o reinício.</p>
            </div>
        `, 'Reiniciar', async () => {
            closeModal();
            showToast('Reiniciando serviços de monitoramento...', 'warning');
            await API.addHistory({ event: 'Serviços Reiniciados', device: 'SINAPSE-NMS', duration: '--', action: 'Reinício manual via Configurações', user: 'admin', type: 'device' });
            setTimeout(() => showToast('Serviços reiniciados com sucesso.', 'success'), 2000);
        });
    });

    document.getElementById('restart-system-btn')?.addEventListener('click', () => {
        openModal('Reiniciar Sistema', `
            <div style="text-align:center;padding:1rem;">
                <i class="fas fa-power-off" style="font-size:2.5rem;color:var(--danger-color);margin-bottom:1rem;display:block;"></i>
                <p>Tem certeza que deseja reiniciar o sistema SINAPSE?</p>
                <p style="color:var(--text-secondary);font-size:0.875rem;margin-top:0.5rem;">Todas as sessões e o monitoramento em andamento serão interrompidos até o sistema voltar.</p>
            </div>
        `, 'Reiniciar Sistema', async () => {
            closeModal();
            await API.addHistory({ event: 'Sistema Reiniciado', device: 'SINAPSE-NMS', duration: '--', action: 'Reinício manual via Configurações', user: 'admin', type: 'device' });
            showToast('Reiniciando o sistema...', 'error');
            API.stopPolling();
            API.stopTrapPolling();
            setTimeout(() => window.location.reload(), 2500);
        });
    });
});
