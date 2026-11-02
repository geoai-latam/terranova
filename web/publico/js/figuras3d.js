// Figuras 3D de la portada: solo donde hay geometría (la prueba, la criba, el
// expediente y la cobertura). Carga three.js y los datos cuando una figura se acerca a la vista.
import { three } from './motor3d.js?v=0cb2e43b98';

const cargas = {
  prueba: el => import('./fig-prueba.js?v=c02fd6c236').then(m => m.montar(el)),
  criba: el => import('./fig-criba.js?v=43bdb20f75').then(m => m.montar(el)),
  cobertura: el => import('./fig-cobertura.js?v=2757c97101').then(m => m.montar(el)),
  expediente: el => import('./servicios3.js?v=41d8765f8f').then(m => m.montar(el.closest('[data-f3-sec]'))),
};
const hechas = new Set();
function cargar(el) {
  const k = el.dataset.f3;
  if (hechas.has(k) || !cargas[k]) return;
  hechas.add(k);
  Promise.all([three(), document.fonts ? document.fonts.ready : null]).then(() => cargas[k](el)).then(() => el.closest('[data-f3-sec]')?.setAttribute('data-f3-lista', ''))
    .catch(err => console.warn('figura 3D', k, err));
}
const io = new IntersectionObserver(es => es.forEach(e => {
  if (!e.isIntersecting) return;
  io.unobserve(e.target); cargar(e.target);
}), { rootMargin: '700px 0px' });
document.querySelectorAll('[data-f3]').forEach(el => io.observe(el));
