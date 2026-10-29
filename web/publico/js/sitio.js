// Comportamiento común del sitio: menú móvil, pestañas, copiar, la consola del héroe y el buscador del catálogo.
const barra = document.querySelector('.barra');
const abrir = document.querySelector('.abrir');
if (barra && abrir) {
  abrir.addEventListener('click', () => {
    const si = barra.classList.toggle('abierta');
    abrir.setAttribute('aria-expanded', String(si));
  });
}

// Pestañas: un solo patrón para el código, los sectores y la consola. El panel de cada pestaña sale
// de aria-controls o, en los bloques de código, del <pre> con el mismo data-t.
function pestanas(lista, alElegir) {
  const botones = [...lista.querySelectorAll('[role="tab"]')];
  const vertical = lista.getAttribute('aria-orientation') === 'vertical';
  const paneles = b => b.hasAttribute('aria-controls')
    ? [document.getElementById(b.getAttribute('aria-controls'))]
    : [...lista.closest('.panel').querySelectorAll(`pre[data-t="${b.dataset.t}"]`)];
  const elegir = (b, porUsuario) => {
    botones.forEach(x => {
      x.setAttribute('aria-selected', String(x === b)); x.tabIndex = x === b ? 0 : -1;
      paneles(x).forEach(p => { p.hidden = x !== b; });
    });
    if (alElegir) alElegir(botones.indexOf(b), porUsuario);
  };
  botones.forEach((b, i) => {
    b.addEventListener('click', () => elegir(b, true));
    b.addEventListener('keydown', e => {
      const atras = vertical ? 'ArrowUp' : 'ArrowLeft', adelante = vertical ? 'ArrowDown' : 'ArrowRight';
      const d = e.key === adelante ? 1 : e.key === atras ? -1 : 0;
      if (d) { e.preventDefault(); const n = botones[(i + d + botones.length) % botones.length]; elegir(n, true); n.focus(); }
    });
  });
  return i => elegir(botones[i], false);
}
document.querySelectorAll('.codigo [role="tablist"], .sectores [role="tablist"]').forEach(l => pestanas(l));

// Copiar: la instrucción para el agente o el bloque de código visible.
async function copiar(boton, texto) {
  const antes = boton.textContent;
  try { await navigator.clipboard.writeText(texto); boton.textContent = 'Copiado'; }
  catch { boton.textContent = 'No se pudo copiar'; }
  setTimeout(() => { boton.textContent = antes; }, 1800);
}
document.querySelectorAll('[data-copiar]').forEach(b => b.addEventListener('click', () => {
  copiar(b, document.querySelector(b.dataset.copiar).textContent.trim());
}));
document.querySelectorAll('[data-copiar-pre]').forEach(b => b.addEventListener('click', () => {
  const pre = [...b.closest('.panel').querySelectorAll('pre')].find(p => !p.hidden);
  copiar(b, pre.textContent.trim());
}));

// Consola del héroe: reproduce por turnos dos respuestas reales. Escribe la pregunta, muestra la
// herramienta que llama y luego la respuesta; avisa a la escena 3D (terranova:turno, y el último
// turno en <html data-turno>) para que el predio suba cuando llega su respuesta. Se pausa con el
// puntero o el foco encima y fuera de la vista, y se detiene cuando alguien elige una pestaña.
// Con movimiento reducido, todo queda quieto.
const con = document.querySelector('[data-consola]');
if (con) {
  const quieto = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const turnos = [...con.querySelectorAll('.turno')];
  const avisar = k => {
    document.documentElement.dataset.turno = k;
    document.dispatchEvent(new CustomEvent('terranova:turno', { detail: k }));
  };
  let auto = !quieto, gen = 0, pausa = false, enVista = true, actual = 0;
  const dormir = ms => new Promise(r => setTimeout(r, ms));
  const sigue = async (g, ms) => {
    await dormir(ms);
    while (g === gen && (pausa || !enVista)) await dormir(150);
    return g === gen;
  };
  const piezas = t => [t.querySelector('.llama'), ...t.querySelectorAll('dt, dd'), t.querySelector('.pie')];
  const completo = t => {
    const x = t.querySelector('.txt');
    x.textContent = x.dataset.texto || x.textContent; x.classList.remove('escribe');
    piezas(t).forEach(e => e.classList.remove('espera'));
  };
  async function reproducir(i) {
    const g = ++gen, t = turnos[i], x = t.querySelector('.txt');
    x.dataset.texto = x.dataset.texto || x.textContent;
    const texto = x.dataset.texto;
    piezas(t).forEach(e => { e.classList.add('espera'); e.classList.remove('aparece'); });
    x.textContent = ''; x.classList.add('escribe');
    con.style.setProperty('--avance', '0%');
    avisar('espera');
    if (!await sigue(g, 450)) return;
    for (let c = 1; c <= texto.length; c++) { x.textContent = texto.slice(0, c); if (!await sigue(g, 24)) return; }
    x.classList.remove('escribe');
    const [llama, ...resto] = piezas(t);
    if (!await sigue(g, 250)) return;
    llama.classList.replace('espera', 'aparece');
    if (!await sigue(g, 700)) return;
    avisar(t.dataset.k);
    for (const e of resto) { e.classList.replace('espera', 'aparece'); if (!await sigue(g, e.tagName === 'DD' ? 70 : 0)) return; }
    const dura = 7000;
    for (let s = 0; s <= dura; s += 100) { con.style.setProperty('--avance', (s / dura * 100) + '%'); if (!await sigue(g, 100)) return; }
    if (auto) elegir((actual + 1) % turnos.length);
  }
  const elegir = pestanas(con.querySelector('[role="tablist"]'), (i, porUsuario) => {
    actual = i;
    if (porUsuario) { auto = false; con.classList.remove('corre'); }
    if (auto) { reproducir(i); return; }
    gen++; completo(turnos[i]); avisar(turnos[i].dataset.k);
    if (porUsuario) turnos[i].querySelector('dl').classList.add('aparece');
  });
  con.addEventListener('pointerenter', () => { pausa = true; });
  con.addEventListener('pointerleave', () => { pausa = false; });
  con.addEventListener('focusin', () => { pausa = true; });
  con.addEventListener('focusout', () => { pausa = false; });
  new IntersectionObserver(es => es.forEach(e => { enVista = e.isIntersecting; })).observe(con.closest('.heroe') || con);
  if (auto) con.classList.add('corre');
  elegir(0);
}

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
