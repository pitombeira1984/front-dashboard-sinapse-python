// ===== GERENCIAMENTO DE ESTADO (client-side, só do necessário em runtime) =====
// currentPage não existe mais aqui: a navegação agora é feita por URLs reais,
// renderizadas pelo servidor (ver app/routers/pages.py).
const AppState = {
    currentAlertFilter: 'all',
    currentTimeRange: '24h',
    currentSettingsTab: 'general',
    currentGponPort: '0/1/0',
};
