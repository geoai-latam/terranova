// Las cuatro decisiones: el expediente en three.js en miniatura y tres figuras
// tipográficas con datos reales (la cifra con su corte, la bitácora, el índice del catálogo). Corren
// de una en una; solo la que corre lleva el ámbar.
import { figura, grupo, sola } from './tipo.js?v=6f554fa24c';

const fmt = new Intl.NumberFormat('es-CO');
const fecha = iso => iso.slice(8, 10) + '-' + iso.slice(5, 7) + '-' + iso.slice(0, 4);
const NOMBRES = { territorio: 'Territorio', estadisticas: 'Estadísticas', contratacion: 'Contratación', justicia: 'Justicia', ambiente: 'Ambiente', empresas: 'Empresas', normativa: 'Normativa' };

export async function montar(secc) {
  const [P, C] = await Promise.all([fetch('/datos/portada.json').then(r => r.json()), fetch('/datos/catalogo.json').then(r => r.json())]);
  P.indice = familias(C);
  // en el orden de la página: el contrato, la ley, el municipio y el lote
  const exEl = secc.querySelector('[data-f3="expediente"]');
  const ex = await import('./fig-expediente.js?v=0560e23e74').then(m => m.montar(exEl));
  const figs = [bitacora(secc.querySelector('.bi3'), P), indice(secc.querySelector('.in3'), P), cifra(secc.querySelector('.ci3'), P), ex];
  if (matchMedia('(max-width: 760px)').matches) {
    // en una columna se ven de a una: cada una corre al entrar en vista
    figs.forEach(f => (f.nombre === 'expediente' ? sola3d(f) : sola(f)));
  } else grupo(figs);
}

function sola3d(f) {
  let visto = false;
  new IntersectionObserver(es => es.forEach(e => { if (!visto && e.intersectionRatio >= 0.35) { visto = true; f.correr(); } }), { threshold: [0.35] }).observe(f.el);
  f.el.addEventListener('click', () => f.correr());
}

function cifra(el, P) {
  const I = P.indicadores, tip = el.querySelector('.ci3-tip'), dl = tip.querySelector('dl');
  const v = el.querySelector('.ci3-i.nuevo .v'), c = el.querySelector('.ci3-i.nuevo .c');
  const lect = el.querySelector('[data-lectura]');
  const num = x => (Number.isInteger(x) ? fmt.format(x) : String(x).replace('.', ','));
  // el indicador que cambia de corte: el que lleva la marca .nuevo (su índice en data-i)
  const iN = +el.querySelector('.ci3-i.nuevo').dataset.i, dN = I[iN];
  const txtNuevo = `IRCA de ${P.municipio.nombre}: ${num(dN.antes)} en ${dN.corte_antes}, ${num(dN.v)} en ${dN.corte} · ${dN.entidad}${dN.nota ? ' · ' + dN.nota.toLowerCase() : ''}`;
  const mostrar = (i, ancla) => {
    const d = I[i];
    dl.innerHTML = `<dt>indicador</dt><dd>${d.k}</dd><dt>entidad</dt><dd>${d.entidad}</dd><dt>licencia</dt><dd>${d.licencia}</dd><dt>corte</dt><dd>${d.corte}${d.antes !== undefined ? ` · antes ${num(d.antes)} (${d.corte_antes})` : ''}</dd><dt>capturado</dt><dd>${fecha(d.grabado)}</dd>`;
    const r = ancla.getBoundingClientRect(), fr = el.getBoundingClientRect();
    tip.style.left = Math.min(fr.width - 250, Math.max(0, r.left - fr.left + 8)) + 'px';
    tip.style.top = (r.bottom - fr.top - 6) + 'px';
    tip.classList.add('ver');
  };
  el.querySelectorAll('.ci3-i').forEach(b => {
    b.addEventListener('pointerenter', () => mostrar(+b.dataset.i, b));
    b.addEventListener('pointerleave', () => { if (!el.classList.contains('tiempo4')) tip.classList.remove('ver'); else mostrar(1, el.querySelector('.ci3-i.nuevo')); });
  });
  return figura(el, {
    nombre: 'cifra',
    pasos: [[0, 'tiempo1'], [900, 'tiempo2'], [1900, 'tiempo3'], [3000, 'tiempo4']],
    al: (k, _, amb) => {
      const nuevo = k === 'tiempo3' || k === 'tiempo4';
      v.textContent = nuevo ? v.dataset.v : v.dataset.antes;
      c.textContent = 'INS · ' + (nuevo ? c.dataset.c : c.dataset.cantes);
      if (k === 'tiempo4' && amb) mostrar(1, el.querySelector('.ci3-i.nuevo')); else tip.classList.remove('ver');
      lect.textContent = nuevo ? txtNuevo : `${P.municipio.nombre}: cuatro indicadores, cada uno con su entidad y su corte`;
    },
  });
}

function bitacora(el, P) {
  const B = P.bitacora, cal = el.querySelector('.bi3-cal');
  const porDia = {};
  B.mods.forEach(m => { (porDia[m.f] = porDia[m.f] || []).push(m); });
  // el día clave: la última prórroga publicada (la del aviso)
  const clave = B.mods.filter(m => m.estado === 'Publicado' && m.dias > 0).reduce((a, m) => (m.f > a.f ? m : a));
  const CLAVE = clave.f, txtClave = `${fecha(clave.f)}: prórroga de ${clave.dias} días`;
  // del mes del primer registro al del último
  const f0 = B.mods[0].f, f1 = B.mods[B.mods.length - 1].f, a1 = +f1.slice(0, 4), m1 = +f1.slice(5, 7);
  const meses = [];
  for (let a = +f0.slice(0, 4), m = +f0.slice(5, 7); a < a1 || (a === a1 && m <= m1); m++) { if (m > 12) { m = 1; a++; } if (a > a1 || (a === a1 && m > m1)) break; meses.push([a, m]); }
  const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
  let html = '';
  meses.forEach(([a, m], i) => {
    const dias = new Date(a, m, 0).getDate();
    html += `<div class="bi3-mes" style="--i:${i}"><span class="bi3-et">${m === 1 || i === 0 ? MES[m - 1] + ' ' + a : MES[m - 1]}</span>`;
    for (let d = 1; d <= 31; d++) {
      if (d > dias) { html += '<i class="x"></i>'; continue; }
      const k = `${a}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`, r = porDia[k];
      const cls = k === CLAVE ? 'd clave' : r ? (r.some(x => x.estado === 'Publicado') ? 'd p' : 'd c') : 'd';
      html += `<i class="${cls}" title="${fecha(k)}${r ? ': ' + r.map(x => x.estado.toLowerCase()).join(', ') : ': sin cambios'}"></i>`;
    }
    html += '</div>';
  });
  cal.innerHTML = html;
  const lect = el.querySelector('[data-lectura]');
  return figura(el, {
    nombre: 'bitacora',
    pasos: [[0, 'tiempo1'], [300, 'tiempo2'], [2100, 'tiempo3'], [2900, 'tiempo4']],
    al: k => {
      lect.textContent = k === 'tiempo2' ? 'cada día, revisado: casi siempre, nada' : k === 'tiempo3' || k === 'tiempo4' ? txtClave : 'lo que sigues, con su fuente';
    },
  });
}

// El índice sale del catálogo publicado (datos/catalogo.json, lo escribe construir.py): una raya por
// herramienta, agrupadas por familia, de la más grande a la más chica.
function familias(C) {
  const fam = {};
  C.herramientas.forEach(h => (fam[h.familia] ||= []).push([h.id, (C.fuentes[h.fuente] || {}).entidad_corta || '']));
  return Object.keys(fam).sort((a, b) => fam[b].length - fam[a].length).map(k => ({ familia: k, h: fam[k] }));
}
function indice(el, P) {
  const svg = el.querySelector('.in3-svg'), tip = el.querySelector('.in3-tip');
  const fam = P.indice, W = 560, H = 290, n = fam.length, cw = W / n, top = 22, baja = 34;
  const max = Math.max(...fam.map(f => f.h.length)), paso = (H - top - baja) / max;
  let s = '';
  fam.forEach((f, i) => {
    const x = i * cw + 6, w = cw - 16;
    f.h.forEach(([id, ent], j) => {
      const y = H - baja - (j + 1) * paso;
      const cls = f.familia === 'normativa' ? (id === 'suin_norma' ? 'r fam elegida' : 'r fam') : 'r';
      s += `<rect class="${cls}" x="${x}" y="${(y + 0.5).toFixed(1)}" width="${w}" height="${Math.max(1.2, paso - 1.6).toFixed(1)}" data-id="${id}" data-ent="${ent}"></rect>`;
    });
    s += `<text class="n" x="${x}" y="${H - baja + 15}">${f.h.length}</text><text class="f" x="${x}" y="${H - baja + 29}">${NOMBRES[f.familia] || f.familia}</text>`;
  });
  // la guía a la herramienta elegida
  const iN = fam.findIndex(f => f.familia === 'normativa'), jS = fam[iN].h.findIndex(h => h[0] === 'suin_norma');
  const xs = iN * cw + 6 + (cw - 16) / 2, ys = H - baja - (jS + 0.5) * paso;
  s += `<path class="guia" d="M${xs} ${ys.toFixed(1)}V${top + 4}H${xs - 70}"></path><text class="et" x="${xs - 74}" y="${top + 8}" text-anchor="end">suin_norma</text>`;
  s += `<text class="tot" x="6" y="12">${fam.reduce((a, f) => a + f.h.length, 0)} herramientas, ${n} familias</text>`;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.innerHTML = s;
  svg.addEventListener('pointerover', e => {
    const r = e.target.closest('rect'); if (!r) return;
    tip.hidden = false; tip.innerHTML = `<b>${r.dataset.id}</b> ${r.dataset.ent}`;
    const rr = r.getBoundingClientRect(), fr = el.getBoundingClientRect();
    tip.style.transform = `translate(${Math.min(fr.width - 200, Math.max(0, rr.left - fr.left)).toFixed(0)}px, ${(rr.top - fr.top - 26).toFixed(0)}px)`;
    el.querySelectorAll('rect.sobre').forEach(x => x.classList.remove('sobre')); r.classList.add('sobre');
  });
  svg.addEventListener('pointerleave', () => { tip.hidden = true; el.querySelectorAll('rect.sobre').forEach(x => x.classList.remove('sobre')); });
  const lect = el.querySelector('[data-lectura]');
  const total = fam.reduce((a, f) => a + f.h.length, 0);
  return figura(el, {
    nombre: 'indice',
    pasos: [[0, 'tiempo1'], [500, 'tiempo2'], [1600, 'tiempo3'], [2600, 'tiempo4']],
    al: k => { lect.textContent = k === 'tiempo3' || k === 'tiempo4' ? '¿Sigue vigente esta ley? → Normativa → suin_norma → MinJusticia' : `${total} herramientas, ${n} familias: cada raya es una`; },
  });
}
