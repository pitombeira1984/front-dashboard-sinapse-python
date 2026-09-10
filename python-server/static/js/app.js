// ===== INICIALIZAÇÃO COMUM A TODAS AS PÁGINAS =====
document.addEventListener('DOMContentLoaded', function () {
    ThemeManager.init();

    if (window.SINAPSE_SETTINGS) applyPollingIntervalFromSettings(window.SINAPSE_SETTINGS.pollingInterval);

    updateTime();
    setInterval(updateTime, 1000);

    // Ctrl+1..6 navega direto para a página correspondente (URLs reais agora,
    // diferente da versão anterior que só trocava o conteúdo em memória).
    document.addEventListener('keydown', function (e) {
        if (e.ctrlKey && e.key >= '1' && e.key <= '6') {
            e.preventDefault();
            const pages = ['/', '/devices', '/alerts', '/analysis', '/settings', '/history'];
            const p = pages[parseInt(e.key) - 1];
            if (p) window.location.href = p;
        }
    });

    window.addEventListener('offline', () => showToast('⚠️ Conexão perdida. Modo offline ativado.', 'warning'));
    window.addEventListener('online',  () => showToast('✅ Conexão restaurada. Sincronizando dados...', 'success'));
});
