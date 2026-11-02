// Las figuras tipográficas sueltas de la portada: el problema (cinco portales, una pregunta) y
// cómo trabajamos (un dato del INS en cuatro destinos). Sin three.js.
import { figura, sola } from './tipo.js?v=6f554fa24c';

const pr = document.querySelector('.pr3');
if (pr) {
  const lect = pr.querySelector('[data-lectura]');
  const txt = { tiempo1: 'cinco portales, cinco formas de llamar al mismo dato', tiempo2: 'los cinco pasos, a mano, en cada portal', tiempo3: 'los cinco, detrás de una sola puerta', tiempo4: 'una respuesta, con su prueba' };
  sola(figura(pr, { nombre: 'problema', pasos: [[0, 'tiempo1'], [1000, 'tiempo2'], [3300, 'tiempo3'], [4300, 'tiempo4']], al: k => { if (txt[k]) lect.textContent = txt[k]; } }));
}
// cómo trabajamos: los cuatro destinos entran de uno en uno; luego la cita, la misma en los cuatro
const en = document.querySelector('.en3');
if (en) sola(figura(en, { nombre: 'entrega', pasos: [[0, 'tiempo1'], [300, 'tiempo2'], [1500, 'tiempo3'], [4200, 'tiempo4']] }));
