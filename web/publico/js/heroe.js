// Decide si el héroe pasa del póster (img/figuras/heroe.svg, la misma escena dibujada con el kit de
// Anatomy) a la escena 3D. Solo carga three.js y los linderos cuando el héroe está en vista, el
// navegador está ocioso y nada pide ahorro: ni ahorro de datos, ni movimiento reducido, ni poca
// memoria (< 4 GB), ni puntero grueso (táctil). En cualquier otro caso queda el póster, que pesa
// poco y es la misma imagen. ?heroe=3d o ?heroe=poster fuerzan uno u otro (para medir).
const esc = document.querySelector('[data-escena="predios"]');
const raiz = document.documentElement;
const pide = new URLSearchParams(location.search).get('heroe');
const ahorro = () =>
  (navigator.connection && navigator.connection.saveData) ||
  matchMedia('(prefers-reduced-motion: reduce)').matches ||
  (navigator.deviceMemory !== undefined && navigator.deviceMemory < 4) ||
  matchMedia('(pointer: coarse)').matches;

if (esc) {
  if (pide === 'poster' || (pide !== '3d' && ahorro())) raiz.dataset.heroe = 'poster';
  else {
    raiz.dataset.heroe = 'espera';
    const ocioso = (cb) => ('requestIdleCallback' in window ? requestIdleCallback(cb, { timeout: 1500 }) : setTimeout(cb, 400));
    const io = new IntersectionObserver((es) => {
      if (!es[es.length - 1].isIntersecting) return;
      io.disconnect();
      ocioso(() => import('./escena-predios.js').catch(() => { raiz.dataset.heroe = 'poster'; }));
    });
    io.observe(esc);
  }
}
