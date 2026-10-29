// Utilidades compartidas de las escenas 3D: órbita por arrastre, movimiento reducido, luces de
// maqueta y el parche de crecimiento y onda que corre en la GPU.
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

export const suave = k => 1 - Math.pow(1 - Math.min(1, Math.max(0, k)), 3);

// Luz de maqueta: cielo y suelo suaves y un sol bajo que proyecta sombras blandas. Las sombras van
// solo en pantallas anchas, donde se notan.
export function luces(THREE, renderer, scene, { sombras, lado, sol = [-0.5, 0.9, 0.55] }) {
  renderer.shadowMap.enabled = sombras;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  scene.add(new THREE.HemisphereLight('#FFFFFF', '#AEB9B1', 2.1));
  const luz = new THREE.DirectionalLight('#FFF8EC', 1.5);
  luz.position.set(sol[0] * lado * 2, sol[1] * lado * 2, sol[2] * lado * 2);
  luz.castShadow = sombras;
  Object.assign(luz.shadow.camera, { left: -lado, right: lado, top: lado, bottom: -lado, near: 1, far: lado * 6 });
  luz.shadow.mapSize.set(2048, 2048);
  luz.shadow.bias = -0.0005; luz.shadow.normalBias = 0.5;
  scene.add(luz);
  return luz;
}

// Crecimiento y onda en la GPU. Cada vértice trae aDist, su distancia (m) al punto consultado:
// uCrece (s) hace crecer los predios desde ese punto hacia afuera y uOnda (m) es el radio de una
// onda que levanta y tiñe lo que va tocando. El mismo parche va en el material de sombra.
export function parchar(mat, U, tinte) {
  mat.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, U);
    sh.vertexShader = 'attribute float aDist;\nuniform float uCrece;\nuniform float uOnda;\n' +
      (tinte ? 'varying float vOnda;\n' : '') +
      sh.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
        float crece = clamp((uCrece - aDist * 0.0026) / 0.8, 0.0, 1.0);
        crece = 1.0 - pow(1.0 - crece, 3.0);
        float dO = (aDist - uOnda) / 34.0;
        float onda = uOnda < 0.0 ? 0.0 : exp(-dO * dO) * clamp(1.0 - uOnda / 900.0, 0.0, 1.0);
        transformed.y = position.y > 0.01 ? position.y * crece + onda * 9.0 : 0.0;
        ${tinte ? 'vOnda = onda;' : ''}`);
    if (tinte) {
      sh.fragmentShader = 'uniform vec3 uTinte;\nvarying float vOnda;\n' + sh.fragmentShader.replace(
        '#include <color_fragment>', '#include <color_fragment>\n  diffuseColor.rgb = mix(diffuseColor.rgb, uTinte, clamp(vOnda * 1.1, 0.0, 0.85));');
    }
  };
  mat.customProgramCacheKey = () => 'terranova-' + (tinte ? 't' : 's');
  return mat;
}
