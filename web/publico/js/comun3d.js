// Lo común de las escenas 3D: de dónde sale three.js. Se importa solo cuando heroe.js decide que la
// escena se carga (en vista, navegador ocioso y un equipo que la aguanta); si no, queda el póster.
export const THREE_URL = 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js';

export async function cargarThree() {
  return import(THREE_URL);
}
