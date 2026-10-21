// ===== GRÁFICOS COM CHART.JS =====
// Só os gráficos realmente usados por alguma página (dashboard): consumo de banda
// por OLT e latência média GPON. As demais funções de gráfico do protótipo original
// (disponibilidade, latência genérica) nunca eram chamadas por nenhuma página e
// foram descartadas na migração.

const ChartRegistry = {};

function destroyChart(id) {
    if (ChartRegistry[id]) {
        ChartRegistry[id].destroy();
        delete ChartRegistry[id];
    }
}

const getCssVar = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

function getChartDefaults() {
    const cs = getComputedStyle(document.documentElement);
    const cv = (v) => cs.getPropertyValue(v).trim();
    const grid = cv('--chart-grid') || 'rgba(51,65,85,0.4)';
    return {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 400, easing: 'easeInOutQuart' },
        plugins: {
            legend: { labels: { color: cv('--text-secondary'), font: { size: 12 }, boxWidth: 14 } },
            tooltip: {
                backgroundColor: cv('--bg-card'),
                borderColor: cv('--border-color'),
                borderWidth: 1,
                titleColor: cv('--text-primary'),
                bodyColor: cv('--text-secondary'),
            },
        },
        scales: {
            x: { ticks: { color: cv('--text-muted'), maxRotation: 0, maxTicksLimit: 8 }, grid: { color: grid } },
            y: { ticks: { color: cv('--text-muted') }, grid: { color: grid } },
        },
    };
}

// ===== LATÊNCIA GPON (linha, atualizada ao vivo via polling) =====
function initLatencyGPONChartEmpty() {
    destroyChart('latencyGpon');
    const canvas = document.getElementById('chart-latency-gpon');
    if (!canvas) return;
    ChartRegistry['latencyGpon'] = new Chart(canvas, {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'Latência Média (ms)', data: [], borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.1)', fill: true, tension: 0.4, pointRadius: 0, pointHoverRadius: 4 }] },
        options: {
            ...getChartDefaults(),
            plugins: { ...getChartDefaults().plugins, tooltip: { ...getChartDefaults().plugins.tooltip, callbacks: { label: ctx => ` Latência: ${ctx.parsed.y} ms` } } },
            scales: { ...getChartDefaults().scales, y: { ...getChartDefaults().scales.y, title: { display: true, text: 'ms', color: getCssVar('--text-muted') } } },
        },
    });
}

function pushGPONChartPoints(liveData) {
    const label = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const latChart = ChartRegistry['latencyGpon'];
    if (latChart && liveData.avgLatency) {
        latChart.data.labels.push(label);
        latChart.data.datasets[0].data.push(parseFloat(liveData.avgLatency));
        if (latChart.data.labels.length > 30) { latChart.data.labels.shift(); latChart.data.datasets[0].data.shift(); }
        latChart.update('none');
    }
}

// ===== RXPOWER DA ONU REAL (linha, um ponto por leitura nova do painel web) =====
function initOnuRealChartEmpty() {
    destroyChart('onuRealRx');
    const canvas = document.getElementById('chart-onu-real-rx');
    if (!canvas) return;
    ChartRegistry['onuRealRx'] = new Chart(canvas, {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'RxPower real (dBm)', data: [], borderColor: '#0ea5e9', backgroundColor: 'rgba(14,165,233,0.1)', fill: true, tension: 0.3, pointRadius: 2, pointHoverRadius: 4 }] },
        options: {
            ...getChartDefaults(),
            plugins: { ...getChartDefaults().plugins, tooltip: { ...getChartDefaults().plugins.tooltip, callbacks: { label: ctx => ` RxPower: ${ctx.parsed.y} dBm` } } },
            scales: { ...getChartDefaults().scales, y: { ...getChartDefaults().scales.y, title: { display: true, text: 'dBm', color: getCssVar('--text-muted') } } },
        },
    });
}

function pushOnuRealPoint(timestampSec, rxPower) {
    const chart = ChartRegistry['onuRealRx'];
    if (!chart || rxPower == null) return;
    chart.data.labels.push(new Date(timestampSec * 1000).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    chart.data.datasets[0].data.push(rxPower);
    if (chart.data.labels.length > 60) { chart.data.labels.shift(); chart.data.datasets[0].data.shift(); }
    chart.update('none');
}

// ===== CONSUMO DE BANDA POR OLT (barras) =====
function renderOLTBandwidthChart(olts) {
    destroyChart('oltBandwidth');
    const canvas = document.getElementById('chart-olt-bandwidth');
    if (!canvas || !olts || !olts.length) return;

    const _inColor   = pct => pct >= 80 ? 'rgba(220,38,38,0.75)'  : pct >= 50 ? 'rgba(245,158,11,0.75)' : 'rgba(37,99,235,0.75)';
    const _inBorder  = pct => pct >= 80 ? '#dc2626'                : pct >= 50 ? '#f59e0b'               : '#2563eb';
    const _outColor  = pct => pct >= 80 ? 'rgba(220,38,38,0.65)'  : pct >= 50 ? 'rgba(245,158,11,0.65)' : 'rgba(16,185,129,0.65)';
    const _outBorder = pct => pct >= 80 ? '#dc2626'                : pct >= 50 ? '#f59e0b'               : '#10b981';

    ChartRegistry['oltBandwidth'] = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: olts.map(o => o.name),
            datasets: [
                { label: 'Tráfego IN (Mbps)',  data: olts.map(o => o.inRate),
                  backgroundColor: olts.map(o => _inColor(o.inPct ?? (o.inRate / o.capacity * 100))),
                  borderColor: olts.map(o => _inBorder(o.inPct ?? (o.inRate / o.capacity * 100))),
                  borderWidth: 1, borderRadius: 4 },
                { label: 'Tráfego OUT (Mbps)', data: olts.map(o => o.outRate),
                  backgroundColor: olts.map(o => _outColor(o.outPct ?? (o.outRate / o.capacity * 100))),
                  borderColor: olts.map(o => _outBorder(o.outPct ?? (o.outRate / o.capacity * 100))),
                  borderWidth: 1, borderRadius: 4 },
            ],
        },
        options: {
            ...getChartDefaults(),
            plugins: {
                ...getChartDefaults().plugins,
                tooltip: {
                    ...getChartDefaults().plugins.tooltip,
                    callbacks: {
                        label: ctx => {
                            const olt = olts[ctx.dataIndex];
                            const pct = ((ctx.parsed.y / olt.capacity) * 100).toFixed(1);
                            return ` ${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString('pt-BR')} Mbps (${pct}% de ${(olt.capacity / 1000).toFixed(1)} Gbps)`;
                        },
                        afterBody: ctx => {
                            if (!ctx.length) return [];
                            const olt = olts[ctx[0].dataIndex];
                            return [`  Capacidade total: ${(olt.capacity / 1000).toFixed(1)} Gbps  •  ${olt.model}`];
                        },
                    },
                },
            },
            scales: {
                ...getChartDefaults().scales,
                y: {
                    ...getChartDefaults().scales.y,
                    title: { display: true, text: 'Mbps', color: getCssVar('--text-muted') },
                    ticks: { color: getCssVar('--text-muted'), callback: v => v >= 1000 ? `${(v / 1000).toFixed(1)} Gbps` : `${v} Mbps` },
                },
            },
        },
    });
}

function updateOLTBandwidthChart(olts) {
    const chart = ChartRegistry['oltBandwidth'];
    if (!chart || !olts || !olts.length) return;
    const _inColor  = pct => pct >= 80 ? 'rgba(220,38,38,0.75)'  : pct >= 50 ? 'rgba(245,158,11,0.75)' : 'rgba(37,99,235,0.75)';
    const _outColor = pct => pct >= 80 ? 'rgba(220,38,38,0.65)'  : pct >= 50 ? 'rgba(245,158,11,0.65)' : 'rgba(16,185,129,0.65)';
    chart.data.datasets[0].data            = olts.map(o => o.inRate);
    chart.data.datasets[0].backgroundColor = olts.map(o => _inColor(o.inPct   ?? (o.inRate  / o.capacity * 100)));
    chart.data.datasets[1].data            = olts.map(o => o.outRate);
    chart.data.datasets[1].backgroundColor = olts.map(o => _outColor(o.outPct ?? (o.outRate / o.capacity * 100)));
    chart.update('none');
}
