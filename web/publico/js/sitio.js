// Comportamiento común del sitio: menú móvil, pestañas, copiar, el sobre del héroe y el buscador del catálogo.
const barra = document.querySelector('.barra');
const abrir = document.querySelector('.abrir');
if (barra && abrir) {
  abrir.addEventListener('click', () => {
    const si = barra.classList.toggle('abierta');
    abrir.setAttribute('aria-expanded', String(si));
  });
}

// Pestañas: un solo patrón para el código y los sectores. El panel de cada pestaña sale
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

// El sobre del héroe: reproduce una vez la respuesta real del predio. Escribe la pregunta, muestra
// la herramienta y, cuando llega la respuesta, la avisa a la maqueta (terranova:turno y el último
// turno en <html data-turno>) en el mismo instante en que aparece el estado: el predio sube y sale
// el destello. Corre al entrar en vista; si la escena 3D viene en camino, la espera hasta 2 s. Con
// movimiento reducido no se reproduce: queda completo, que es el estado de la respuesta.
const sobre = document.querySelector('[data-sobre]');
if (sobre && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const raiz = document.documentElement;
  const avisar = k => {
    raiz.dataset.turno = k;
    document.dispatchEvent(new CustomEvent('terranova:turno', { detail: k }));
  };
  const dormir = ms => new Promise(r => setTimeout(r, ms));
  const x = sobre.querySelector('.txt'), texto = x.textContent;
  const llama = sobre.querySelector('.llama'), filas = [...sobre.querySelectorAll('.fila')], pie = sobre.querySelector('.pie');
  const piezas = [llama, ...filas, pie];
  piezas.forEach(e => e.classList.add('espera'));
  x.textContent = ''; x.classList.add('escribe');
  avisar('espera');
  async function reproducir() {
    await dormir(400);
    for (let c = 1; c <= texto.length; c++) { x.textContent = texto.slice(0, c); await dormir(22); }
    x.classList.remove('escribe');
    await dormir(240);
    llama.classList.replace('espera', 'aparece');
    await dormir(620);
    filas[0].classList.replace('espera', 'aparece');
    avisar('predio');
    for (const e of [...filas.slice(1), pie]) { await dormir(70); e.classList.replace('espera', 'aparece'); }
  }
  let ya = false;
  const empezar = () => { if (!ya) { ya = true; reproducir(); } };
  const io = new IntersectionObserver(es => {
    if (!es[es.length - 1].isIntersecting) return;
    io.disconnect();
    const viene = ['espera', 'cargando'].includes(raiz.dataset.heroe);
    if (!viene) { empezar(); return; }
    document.addEventListener('terranova:escena', () => setTimeout(empezar, 250), { once: true });
    setTimeout(empezar, 2000);
  });
  io.observe(sobre);
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
  let datos = null, limite = 12;
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
      limite = 12; if (datos) pintar();
    });
  });
  entrada.addEventListener('input', () => { limite = 12; if (datos) pintar(); });
  mas.addEventListener('click', () => { limite += 60; pintar(); });
  fetch('/datos/catalogo.json').then(r => r.json()).then(d => {
    d.herramientas.forEach(h => { const f = d.fuentes[h.fuente] || {}; h.texto = norm([h.pregunta, h.id, h.familia, f.entidad, f.titulo].join(' ')); });
    datos = d; pintar();
  }).catch(() => { conteo.textContent = 'No se pudo cargar el catálogo. Está también en /v1/herramientas.'; });
}

// Contacto: el asunto llega en ?asunto= desde los botones del sitio y se preselecciona.
const formAsunto = document.querySelector('[data-asunto] select[name="asunto"]');
if (formAsunto) {
  const pedido = new URLSearchParams(location.search).get('asunto');
  if (pedido && [...formAsunto.options].some(o => o.value === pedido)) formAsunto.value = pedido;
}
