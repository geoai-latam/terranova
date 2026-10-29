// Comportamiento común del sitio: menú móvil, pestañas de código y el buscador del catálogo.
const barra = document.querySelector('.barra');
const abrir = document.querySelector('.abrir');
if (barra && abrir) {
  abrir.addEventListener('click', () => {
    const si = barra.classList.toggle('abierta');
    abrir.setAttribute('aria-expanded', String(si));
  });
}

document.querySelectorAll('.codigo [role="tablist"]').forEach(lista => {
  const panel = lista.closest('.panel');
  const botones = [...lista.querySelectorAll('[role="tab"]')];
  const elegir = b => {
    botones.forEach(x => { x.setAttribute('aria-selected', String(x === b)); x.tabIndex = x === b ? 0 : -1; });
    panel.querySelectorAll('pre[data-t]').forEach(p => { p.hidden = p.dataset.t !== b.dataset.t; });
  };
  botones.forEach((b, i) => {
    b.addEventListener('click', () => elegir(b));
    b.addEventListener('keydown', e => {
      const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      if (d) { const n = botones[(i + d + botones.length) % botones.length]; elegir(n); n.focus(); }
    });
  });
});

// Catálogo: filtra las herramientas por texto y familia sobre /datos/catalogo.json (generado del catálogo real).
const cat = document.querySelector('[data-catalogo]');
if (cat) {
  const entrada = cat.querySelector('input[type="search"]');
  const lista = cat.querySelector('.herramientas');
  const conteo = cat.querySelector('.conteo');
  const mas = cat.querySelector('.mas');
  const fichas = cat.querySelectorAll('[data-familia]');
  let familia = new URLSearchParams(location.search).get('familia') || '';
  let datos = null, limite = 40;
  const norm = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const esc = s => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const COBRO = { codigo: 'código', registro: 'registro', agregado: 'agregado', punto: 'punto', zona: 'zona' };
  function pintar() {
    const q = norm(entrada.value.trim());
    const hs = datos.herramientas.filter(h => (!familia || h.familia === familia) && (!q || h.texto.includes(q)));
    conteo.textContent = hs.length === 1 ? '1 herramienta' : hs.length.toLocaleString('es-CO') + ' herramientas';
    lista.innerHTML = hs.slice(0, limite).map(h => {
      const f = datos.fuentes[h.fuente] || {};
      return `<div class="herr-fila"><div><h3>${esc(h.pregunta)}</h3><code>${esc(h.id)} · ${esc(h.familia)}</code></div>` +
        `<div class="ent">${esc(f.entidad_corta || f.entidad || h.fuente)}<small>${esc(f.licencia || 'licencia por verificar')}</small></div>` +
        `<div class="cr">${h.creditos}<small>${COBRO[h.cobro] || ''}</small></div></div>`;
    }).join('') || '<p class="tenue" style="padding:18px 0">Ninguna herramienta coincide. Prueba con otra palabra o quita el filtro de familia.</p>';
    mas.hidden = hs.length <= limite;
  }
  fichas.forEach(b => {
    b.setAttribute('aria-pressed', String(b.dataset.familia === familia));
    b.addEventListener('click', () => {
      familia = b.dataset.familia === familia ? '' : b.dataset.familia;
      fichas.forEach(x => x.setAttribute('aria-pressed', String(x.dataset.familia === familia)));
      limite = 40; if (datos) pintar();
    });
  });
  entrada.addEventListener('input', () => { limite = 40; if (datos) pintar(); });
  mas.addEventListener('click', () => { limite += 60; pintar(); });
  fetch('/datos/catalogo.json').then(r => r.json()).then(d => {
    d.herramientas.forEach(h => { const f = d.fuentes[h.fuente] || {}; h.texto = norm([h.pregunta, h.id, h.familia, f.entidad, f.titulo].join(' ')); });
    datos = d; pintar();
  }).catch(() => { conteo.textContent = 'No se pudo cargar el catálogo. Está también en /v1/herramientas.'; });
}
