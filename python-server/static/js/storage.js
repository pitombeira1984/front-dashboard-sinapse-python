// ===== PREFERÊNCIA DE TEMA (cookie, lido pelo servidor no próximo render) =====
// O servidor é a fonte de verdade de todo o resto do estado (dispositivos, alertas,
// parâmetros de monitoramento, manutenções, histórico, backups, configurações) —
// não existe mais camada de cache em localStorage. O tema é a única exceção: é uma
// preferência puramente de exibição, guardada em cookie para o Jinja2 já renderizar
// data-theme correto no HTML inicial (sem flash de tema errado).
const CookieStore = {
    set(name, value, days = 365) {
        const expires = new Date(Date.now() + days * 86400000).toUTCString();
        document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
    },
    get(name) {
        const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
        return match ? decodeURIComponent(match[1]) : null;
    },
};

const ThemeManager = {
    init() {
        const current = document.documentElement.getAttribute('data-theme') || 'dark';
        this._updateBtn(current);
        document.getElementById('theme-toggle-btn')?.addEventListener('click', () => this.toggle());
    },
    toggle() {
        const current = document.documentElement.getAttribute('data-theme') || 'dark';
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        CookieStore.set('sinapse_theme', next);
        this._updateBtn(next);
    },
    _updateBtn(theme) {
        const icon = document.getElementById('theme-icon');
        const label = document.getElementById('theme-label');
        if (!icon) return;
        if (theme === 'light') {
            icon.className = 'fas fa-moon';
            if (label) label.textContent = 'Tema Escuro';
        } else {
            icon.className = 'fas fa-sun';
            if (label) label.textContent = 'Tema Claro';
        }
    },
};
