// Las figuras tipográficas sueltas de la portada: el problema (cinco portales, una pregunta) y
// las tres formas de usarlo (la misma respuesta en tres lugares). Sin three.js.
import { figura, sola } from './tipo.js?v=6f554fa24c';

const pr = document.querySelector('.pr3');
if (pr) {
  const lect = pr.querySelector('[data-lectura]');
  const txt = { tiempo1: 'cinco portales, cinco formas de llamar al mismo dato', tiempo2: 'los cinco pasos, a mano, en cada portal', tiempo3: 'los cinco, detrás de una sola puerta', tiempo4: 'una respuesta, con su prueba' };
  sola(figura(pr, { nombre: 'problema', pasos: [[0, 'tiempo1'], [1000, 'tiempo2'], [3300, 'tiempo3'], [4300, 'tiempo4']], al: k => { if (txt[k]) lect.textContent = txt[k]; } }));
}
const tr = document.querySelector('.tr3');
if (tr) sola(figura(tr, { nombre: 'tres', pasos: [[0, 'tiempo1'], [700, 'tiempo2'], [1400, 'tiempo3'], [2100, 'tiempo4']] }));
