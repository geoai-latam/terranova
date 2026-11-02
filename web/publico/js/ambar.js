// El ámbar tiene un solo papel: «lo que se está probando». Fuera de las figuras es el botón
// principal; si un botón principal de la página está en vista, la figura termina su ciclo sin ámbar
// (DISENO.md: un ámbar por vista). El de la barra fija no cuenta: siempre está.
const vistos = new Set();
const io = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) vistos.add(e.target); else vistos.delete(e.target);
}), { threshold: 0.01 });
document.querySelectorAll('main .boton.p').forEach(b => io.observe(b));
export const ambarLibre = () => vistos.size === 0;
export const reducido = matchMedia('(prefers-reduced-motion: reduce)').matches;
