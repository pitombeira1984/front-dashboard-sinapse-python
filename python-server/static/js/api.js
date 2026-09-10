// ===== CLIENTE DA API SINAPSE =====
// O FastAPI serve as páginas E a API no mesmo processo/origem — sempre same-origin,
// sem precisar apontar para um host diferente em desenvolvimento.
const API = {
    BASE_URL: '',
    POLL_INTERVAL: 5000,

    connected: false,
    pollTimer: null,
    listeners: [],

    async _request(path, { raw = false } = {}) {
        try {
            const res = await fetch(`${this.BASE_URL}${path}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();
            if (!this.connected) {
                this.connected = true;
                this._notify('connected', null);
                updateServerStatus(true);
            }
            return raw ? json : (json.data ?? json);
        } catch (err) {
            if (this.connected) {
                this.connected = false;
                this._notify('disconnected', err.message);
                updateServerStatus(false);
            }
            return null;
        }
    },

    async _fetchPost(path, body) {
        try {
            const res = await fetch(`${this.BASE_URL}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        } catch (err) { console.warn('API POST error:', err); return null; }
    },
    async _fetchPut(path, body) {
        try {
            const res = await fetch(`${this.BASE_URL}${path}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        } catch (err) { console.warn('API PUT error:', err); return null; }
    },
    async _fetchDelete(path) {
        try {
            const res = await fetch(`${this.BASE_URL}${path}`, { method: 'DELETE' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return await res.json();
        } catch (err) { console.warn('API DELETE error:', err); return null; }
    },

    // ── Telemetria ─────────────────────────────────────────────────────────
    async getStatus()     { return this._request('/api/status'); },
    async getDevice()     { return this._request('/api/device'); },
    async getHistory()    { return this._request('/api/device/history'); },
    async getLive(port)   { const qs = port ? `?port=${encodeURIComponent(port)}` : ''; return this._request(`/api/metrics/live${qs}`); },

    // ── GPON / ONUs ────────────────────────────────────────────────────────
    async getONUs(port)          { const qs = port ? `?port=${encodeURIComponent(port)}` : ''; return this._request(`/api/onus${qs}`); },
    async getGponPorts()         { return this._request('/api/gpon/ports'); },
    async getOLTsBandwidth()     { return this._request('/api/olts/bandwidth'); },

    // ── Clientes ───────────────────────────────────────────────────────────
    async getClient(id) { return this._request(`/api/clients/${id}`); },

    // ── SNMP Traps ─────────────────────────────────────────────────────────
    async getTraps(filters = {}) {
        const params = new URLSearchParams();
        if (filters.type)           params.set('type',           filters.type);
        if (filters.severity)       params.set('severity',       filters.severity);
        if (filters.unacknowledged) params.set('unacknowledged', 'true');
        if (filters.limit)          params.set('limit',          filters.limit);
        const qs = params.toString();
        const res = await this._request(`/api/traps${qs ? '?' + qs : ''}`, { raw: true });
        return res?.data ?? [];
    },
    async getTrapStats()        { return this._request('/api/traps/stats', { raw: true }); },
    async acknowledgeTraps(ids) { return this._fetchPut('/api/traps/acknowledge',     { ids }); },
    async acknowledgeAllTraps() { return this._fetchPut('/api/traps/acknowledge-all', {}); },

    // ── CRUD Dispositivos ──────────────────────────────────────────────────
    async getDevices()           { return this._request('/api/devices'); },
    async addDevice(d)           { const r = await this._fetchPost('/api/devices', d); return r?.data ?? null; },
    async scanDevices(range, protocol) { const r = await this._fetchPost('/api/devices/scan', { range, protocol }); return r?.data ?? []; },
    async getLocalRanges()       { return this._request('/api/devices/scan/local-ranges'); },
    async updateDevice(id, f)    { const r = await this._fetchPut(`/api/devices/${id}`, f); return r?.data ?? null; },
    async deleteDevice(id)       { return this._fetchDelete(`/api/devices/${id}`); },
    async addOLT(data)           { const r = await this._fetchPost('/api/olts', data); return r?.data ?? null; },
    async addONU(data)           { const r = await this._fetchPost('/api/onus', data); return r?.data ?? null; },

    // ── CRUD Alertas ───────────────────────────────────────────────────────
    async getAllAlerts()          { return this._request('/api/alerts/all'); },
    async resolveAlert(id)       { return this._fetchPut(`/api/alerts/${id}/resolve`, {}); },
    async deleteAlert(id)        { return this._fetchDelete(`/api/alerts/${id}`); },

    // ── Parâmetros de Monitoramento ────────────────────────────────────────
    async getMonitoringParams()      { return this._request('/api/monitoring-params'); },
    async addMonitoringParam(p)      { const r = await this._fetchPost('/api/monitoring-params', p); return r?.data ?? null; },
    async updateMonitoringParam(id,f){ const r = await this._fetchPut(`/api/monitoring-params/${id}`, f); return r?.data ?? null; },
    async toggleMonitoringParam(id)  { const r = await this._fetchPut(`/api/monitoring-params/${id}/toggle`, {}); return r?.data ?? null; },
    async deleteMonitoringParam(id)  { return this._fetchDelete(`/api/monitoring-params/${id}`); },

    // ── Manutenções ────────────────────────────────────────────────────────
    async getMaintenances()      { return this._request('/api/maintenances'); },
    async addMaintenance(item)   { const r = await this._fetchPost('/api/maintenances', item); return r?.data ?? null; },
    async deleteMaintenance(id)  { return this._fetchDelete(`/api/maintenances/${id}`); },

    // ── Histórico ──────────────────────────────────────────────────────────
    async getAppHistory()        { return this._request('/api/history'); },
    async addHistory(item)       { const r = await this._fetchPost('/api/history', item); return r?.data ?? null; },

    // ── Configurações ──────────────────────────────────────────────────────
    async saveSettings(s)        { const r = await this._fetchPut('/api/settings', s); return r?.data ?? null; },

    // ── Backups ────────────────────────────────────────────────────────────
    async createBackup()         { const r = await this._fetchPost('/api/backups', {}); return r?.data ?? null; },
    async restoreBackup(id)      { return this._fetchPost(`/api/backups/${id}/restore`, {}); },
    async deleteBackup(id)       { return this._fetchDelete(`/api/backups/${id}`); },

    // ── Polling ────────────────────────────────────────────────────────────
    startPolling(callback) {
        this.stopPolling();
        const poll = async () => {
            const data = await this.getLive(AppState.currentGponPort);
            if (data) callback(data);
        };
        poll();
        this.pollTimer = setInterval(poll, this.POLL_INTERVAL);
    },
    stopPolling() {
        if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null; }
    },

    // ── Trap Polling (5s) — separado do polling de métricas ───────────────
    trapTimer: null,
    trapLastId: null,
    startTrapPolling(callback) {
        this.stopTrapPolling();
        const poll = async () => {
            const res = await this.getTrapStats();
            if (!res) return;
            const stats = res.data ?? res;
            const lastTrap = stats.lastTrap;
            if (lastTrap && lastTrap.id !== this.trapLastId) {
                this.trapLastId = lastTrap.id;
                callback(stats, lastTrap);
            }
        };
        poll();
        this.trapTimer = setInterval(poll, this.POLL_INTERVAL);
    },
    stopTrapPolling() {
        if (this.trapTimer) { clearInterval(this.trapTimer); this.trapTimer = null; }
    },

    // ── Eventos ────────────────────────────────────────────────────────────
    on(event, fn) { this.listeners.push({ event, fn }); },
    _notify(event, data) { this.listeners.filter(l => l.event === event).forEach(l => l.fn(data)); },
};

// ── Atualizar indicador de status do servidor na sidebar ─────────────────────
function updateServerStatus(online) {
    const dot  = document.querySelector('.status-dot');
    const text = document.querySelector('.status-indicator span');
    if (dot)  dot.style.backgroundColor = online ? 'var(--success-color)' : 'var(--danger-color)';
    if (text) text.textContent = online ? 'Servidor Conectado' : 'Servidor Offline';
}
