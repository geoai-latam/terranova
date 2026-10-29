// Utilidades compartidas de las escenas 3D: colores del tema, órbita por arrastre y movimiento reducido.
export const THREE_URL = 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js';
export const quieto = matchMedia('(prefers-reduced-motion: reduce)').matches;

// Arrastrar gira en azimut e inclinación; en táctil solo el arrastre horizontal, para no robar el scroll.
export function orbita(el, st) {
  let x0 = 0, y0 = 0, activo = false;
  el.addEventListener('pointerdown', e => {
    activo = true; x0 = e.clientX; y0 = e.clientY; st.toque = performance.now();
    if (e.pointerType === 'mouse') el.setPointerCapture(e.pointerId);
    el.style.cursor = 'grabbing';
  });
  el.addEventListener('pointermove', e => {
    if (!activo) return;
    st.az -= (e.clientX - x0) * 0.006;
    if (e.pointerType === 'mouse') st.pol = Math.min(st.polMax, Math.max(st.polMin, st.pol - (e.clientY - y0) * 0.004));
    x0 = e.clientX; y0 = e.clientY; st.toque = performance.now();
  });
  const fin = () => { activo = false; el.style.cursor = ''; };
  el.addEventListener('pointerup', fin); el.addEventListener('pointercancel', fin); el.addEventListener('pointerleave', fin);
}

// Solo dibuja mientras la escena está a la vista: ahorra batería y CPU.
export function visible(el, cb) {
  const io = new IntersectionObserver(es => es.forEach(e => cb(e.isIntersecting)), { rootMargin: '120px' });
  io.observe(el);
}

export async function cargarThree() {
  return import(THREE_URL);
}
