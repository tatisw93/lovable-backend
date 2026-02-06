/* ===== API helpers ===== */
const API = {
    async get(url) {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    async postFile(url, file) {
        const form = new FormData();
        form.append('arquivo', file);
        const res = await fetch(url, { method: 'POST', body: form });
        return { status: res.status, data: await res.json() };
    },

    async post(url, body) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: body ? JSON.stringify(body) : undefined
        });
        return res.json();
    }
};

/* ===== Health check ===== */
async function checkHealth() {
    const el = document.getElementById('apiStatus');
    if (!el) return;
    try {
        await API.get('/api/health');
        el.innerHTML = '<span class="status-dot online"></span><span>API Online</span>';
    } catch {
        el.innerHTML = '<span class="status-dot offline"></span><span>API Offline</span>';
    }
}

/* ===== Format helpers ===== */
function formatBytes(bytes) {
    if (!bytes) return '-';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

function formatDate(iso) {
    if (!iso) return '-';
    const d = new Date(iso);
    return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function formatMoney(val) {
    if (val === null || val === undefined) return '-';
    return 'R$ ' + Number(val).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function statusBadge(status) {
    const map = {
        concluido: 'success', processando: 'warning', erro: 'danger',
        pendente: 'muted', duplicado: 'info'
    };
    return `<span class="badge badge-${map[status] || 'muted'}">${status}</span>`;
}

function nivelBadge(nivel) {
    return `<span class="badge badge-${nivel}">${nivel}</span>`;
}

function confiancaBadge(conf) {
    return `<span class="badge badge-${conf}">${conf}</span>`;
}

/* ===== Init ===== */
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    setInterval(checkHealth, 30000);
});
