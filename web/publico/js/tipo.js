// Figuras tipográficas (HTML y SVG): cuatro tiempos (pregunta, fuente, prueba, reposo) puestos como
// clases con temporizadores; el movimiento lo hacen transiciones de CSS que terminan solas. No hay
// bucle de cuadros: entre ciclos no se pinta nada. Con movimiento reducido, el reposo directo.
import { ambarLibre, reducido } from './ambar.js?v=420978c8f1';

// pasos: [[ms, clase], ...]; la última clase es el reposo. al(t, clase) para lo que no es CSS.
export function figura(el, { pasos, al = () => {}, nombre = '' }) {
  const clases = pasos.map(p => p[1]);
  let timers = [], corre = false, finCb = null;
  const limpiar = () => { timers.forEach(clearTimeout); timers = []; };
  const poner = (k, conAmbar) => {
    clases.forEach((c, j) => el.classList.toggle(c, j <= k));
    el.classList.toggle('sin-ambar', !conAmbar);
    al(clases[k], k, conAmbar);
  };
  const f = {
    el, nombre,
    reposo(conAmbar = false) { limpiar(); corre = false; el.classList.add('quieta'); poner(clases.length - 1, conAmbar); },
    correr(cb) {
      // nada con texto se mueve antes de que Geist esté cargada
      if (document.fonts && document.fonts.status !== 'loaded') { document.fonts.ready.then(() => f.correr(cb)); return; }
      limpiar(); finCb = cb || null;
      if (reducido) { f.reposo(ambarLibre()); if (finCb) finCb(); return; }
      corre = true; el.classList.remove('quieta');
      // vuelve al principio sin transición, y arranca en el cuadro siguiente
      el.classList.add('sin-trans'); clases.forEach(c => el.classList.remove(c)); al('', -1, true);
      void el.offsetWidth; el.classList.remove('sin-trans');
      let amb = true;
      pasos.forEach(([ms, c], k) => timers.push(setTimeout(() => {
        if (k === pasos.length - 2) amb = ambarLibre(); // el ámbar se decide al llegar a la prueba
        poner(k, k >= pasos.length - 2 ? amb : true);
        if (k === pasos.length - 1) { corre = false; if (finCb) { const g = finCb; finCb = null; g(); } }
      }, ms)));
    },
    get corre() { return corre; },
  };
  return f;
}

// Una figura sola: un ciclo al entrar en vista (35 %), y otro al tocarla o con Enter.
export function sola(f) {
  let visto = false;
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (!visto && (e.intersectionRatio >= 0.35 || (e.isIntersecting && e.intersectionRect.height > innerHeight * 0.5))) { visto = true; f.correr(); }
  }), { threshold: [0, 0.35, 0.6] });
  io.observe(f.el);
  f.reposo(false);
  tocable(f.el, () => f.correr());
}
export function tocable(el, fn) {
  el.addEventListener('click', e => { if (!e.target.closest('a')) fn(); });
  el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fn(); } });
}

// Un grupo (los servicios): corren de una en una al entrar, y solo la que corre o la última lleva el
// ámbar; las demás quedan en su reposo sin ámbar.
export function grupo(figs, { hueco = 700 } = {}) {
  let visto = false, i = -1;
  const lanzar = k => {
    figs.forEach((g, j) => { if (j !== k && !g.corre) g.reposo(false); });
    i = k; figs[k].correr(() => {
      if (ronda && k + 1 < figs.length) setTimeout(() => { if (ronda) lanzar(k + 1); }, hueco); else ronda = false;
    });
  };
  let ronda = false;
  figs.forEach(g => g.reposo(false));
  if (reducido) { figs[0].reposo(ambarLibre()); }
  const caja = figs[0].el.closest('[data-f3-sec]') || figs[0].el;
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (!visto && e.isIntersecting && e.intersectionRect.height > Math.min(innerHeight * 0.45, e.boundingClientRect.height * 0.3)) {
      visto = true; if (!reducido) { ronda = true; lanzar(0); }
    }
  }), { threshold: [0, 0.1, 0.25, 0.4] });
  io.observe(caja);
  figs.forEach((g, k) => tocable(g.el, () => { ronda = false; lanzar(k); }));
  return { lanzar, get i() { return i; } };
}
