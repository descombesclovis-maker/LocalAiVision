// LocalAiWeb immersive starter — real WebGL, scroll-linked motion and optional user GLB.
// Keep the Three.js version aligned with the import map in index.html.
const experience = document.querySelector('.experience');
const stage = document.getElementById('three-stage');
const status = document.getElementById('scene-status');
const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
const clamp = (n, lo, hi) => Math.min(hi, Math.max(lo, n));
const setStatus = text => { if (status) status.textContent = text; };
let active = true, onScreen = true, destroyed = false, renderer, scene, camera, three, rig, object3d;
let proceduralParts = [], modelClips = [], mixer = null, pointer = { x: 0, y: 0 };
let renderWidth = 0, renderHeight = 0, lastFrame = 0, progress = 0, resizeObserver;
const mobile = () => window.matchMedia('(max-width: 700px)').matches;
const perfPixelRatio = () => Math.min(window.devicePixelRatio || 1, mobile() ? 1.25 : 1.7);

function updateProgress() {
  const bounds = experience.getBoundingClientRect();
  progress = clamp(-bounds.top / Math.max(1, bounds.height - window.innerHeight), 0, 1);
  const hero = document.querySelector('.hero-copy');
  if (hero && !motionQuery.matches) {
    hero.style.opacity = String(1 - clamp(progress * 5.2, 0, 1));
    hero.style.transform = 'translate3d(0,' + (-55 * progress) + 'px,0)';
    hero.style.visibility = progress > .24 ? 'hidden' : 'visible';
  }
}
updateProgress();
window.addEventListener('scroll', updateProgress, { passive:true });
window.addEventListener('pointermove', e => {
  pointer.x = clamp((e.clientX / window.innerWidth - .5) * 2, -1, 1);
  pointer.y = clamp((e.clientY / window.innerHeight - .5) * 2, -1, 1);
}, {passive:true});
document.addEventListener('visibilitychange', () => { active = !document.hidden; });
const visible = new IntersectionObserver(entries => { onScreen = entries[0]?.isIntersecting ?? true; }, { rootMargin:'100px' });
visible.observe(experience);

async function bootScene() {
  if (motionQuery.matches) { setStatus('Animation 3D désactivée : préférence de réduction du mouvement respectée.'); return; }
  try {
    three = await import('three');
    if (destroyed) return;
    const THREE = three;
    renderer = new THREE.WebGLRenderer({ alpha:true, antialias:!mobile(), powerPreference:mobile()?'low-power':'high-performance' });
    renderer.setPixelRatio(perfPixelRatio());
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.38;
    renderer.setClearColor(0x080b14, 0);
    stage.appendChild(renderer.domElement);
    renderer.domElement.setAttribute('aria-hidden','true');
    renderer.domElement.addEventListener('webglcontextlost', event => {
      event.preventDefault();
      renderer.setAnimationLoop(null);
      experience.classList.remove('has-webgl');
      setStatus('Le moteur graphique a été interrompu. Aperçu alternatif affiché.');
    });

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(36, 1, .1, 120);
    camera.position.set(0, .2, 8.8);
    scene.add(new THREE.HemisphereLight(0xe7ecff, 0x0d1529, 2.15));
    const key = new THREE.DirectionalLight(0xfff6e0, 5.4);
    key.position.set(-3.5, 5, 5.5);
    scene.add(key);
    const rim = new THREE.PointLight(0x6f9ffd, 120, 18, 2);
    rim.position.set(3.8, 1.5, -3.5);
    scene.add(rim);
    const accent = new THREE.PointLight(0xd9ff87, 36, 10, 2);
    accent.position.set(-3, -2, 3);
    scene.add(accent);
    rig = new THREE.Group();
    scene.add(rig);

    const modelSrc = (experience.dataset.modelSrc || '').trim();
    if (modelSrc) {
      if (!/^assets\/[a-zA-Z0-9_./ -]+\.glb(?:[?#].*)?$/i.test(modelSrc) || modelSrc.split('/').includes('..')) {
        throw new Error('Chemin GLB incorrect : utilisez un fichier dans assets/.');
      }
      try {
        const {GLTFLoader} = await import('three/addons/loaders/GLTFLoader.js');
        const loader = new GLTFLoader();
        const gltf = await loader.loadAsync(modelSrc);
        if (destroyed) return;
        object3d = gltf.scene;
        const bounds = new THREE.Box3().setFromObject(object3d);
        if (bounds.isEmpty()) throw new Error('Le fichier GLB ne contient pas de géométrie.');
        const center = bounds.getCenter(new THREE.Vector3());
        const size = bounds.getSize(new THREE.Vector3());
        const unit = 3.45 / Math.max(size.x, size.y, size.z, .001);
        object3d.position.sub(center).multiplyScalar(unit);
        object3d.scale.multiplyScalar(unit);
        rig.add(object3d);
        modelClips = gltf.animations || [];
        if (modelClips.length) {
          mixer = new THREE.AnimationMixer(object3d);
          modelClips.slice(0, 2).forEach(clip => mixer.clipAction(clip).play());
        }
        setStatus('Modèle 3D chargé — défilez pour explorer.');
      } catch(error) {
        console.warn('LocalAiWeb: impossible de charger le GLB',error);
        createProcedural(THREE);
        setStatus('Modèle GLB indisponible : sculpture 3D de démonstration affichée.');
      }
    } else {
      createProcedural(THREE);
      setStatus('Scène 3D interactive prête — importez un GLB pour utiliser votre produit.');
    }

    function resize() {
      if (!renderer || destroyed) return;
      const rect = stage.getBoundingClientRect();
      const w = Math.max(1, Math.round(rect.width)), h = Math.max(1, Math.round(rect.height));
      if (w === renderWidth && h === renderHeight) return;
      renderWidth = w; renderHeight = h;
      renderer.setPixelRatio(perfPixelRatio());
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.fov = mobile()?43:36;
      camera.updateProjectionMatrix();
    }
    resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(stage);
    resize();
    renderer.setAnimationLoop(time => {
      if (destroyed || !active || !onScreen) return;
      const minimumGap = mobile() ? 33 : 16;
      if (time - lastFrame < minimumGap) return;
      const dt = Math.min((time - lastFrame) / 1000 || .016, .05);
      lastFrame = time;
      updateFrame(time/1000, dt);
      renderer.render(scene, camera);
      if (!experience.classList.contains('has-webgl')) experience.classList.add('has-webgl');
    });
  } catch(error) {
    console.warn('LocalAiWeb: WebGL indisponible',error);
    renderer?.setAnimationLoop(null);
    experience.classList.remove('has-webgl');
    setStatus('Aperçu graphique alternatif : moteur WebGL indisponible ou chargement réseau impossible.');
  }
}

function createProcedural(THREE) {
  // Product-neutral exhibition sculpture: works for any industry without implying a specific real product.
  const shell = new THREE.MeshPhysicalMaterial({color:0x7f9ab5, metalness:.82, roughness:.23, clearcoat:1, clearcoatRoughness:.15});
  const glass = new THREE.MeshPhysicalMaterial({color:0x121f35,metalness:.6,roughness:.17,clearcoat:1,clearcoatRoughness:.12});
  const lime = new THREE.MeshBasicMaterial({color:0xc6f75f, toneMapped:false});
  const chrome = new THREE.MeshStandardMaterial({color:0xd0e6ff,metalness:.95,roughness:.18});
  const center = new THREE.Group();
  const core = new THREE.Mesh(new THREE.IcosahedronGeometry(1.57, 4), shell);
  center.add(core);
  const darker = new THREE.Mesh(new THREE.IcosahedronGeometry(1.64, 1), glass);
  darker.material.wireframe = true;
  center.add(darker);
  const pulse = new THREE.Mesh(new THREE.SphereGeometry(.22, 32, 16), lime);
  pulse.position.set(.96,.97,1.35);
  center.add(pulse);
  rig.add(center);
  const rings = [
    {r:2.1,t:.043,rx:1.12,ry:.28,rz:.26,mat:chrome},
    {r:2.56,t:.015,rx:.32,ry:.7,rz:-.67,mat:chrome},
    {r:1.96,t:.022,rx:.6,ry:.1,rz:.83,mat:lime}
  ];
  rings.forEach(spec => {
    const mesh = new THREE.Mesh(new THREE.TorusGeometry(spec.r,spec.t,10,160),spec.mat);
    mesh.rotation.set(spec.rx,spec.ry,spec.rz);
    rig.add(mesh);
    proceduralParts.push(mesh);
  });
  const positions = new Float32Array(330*3);
  for(let i=0;i<330;i++) {
    const angle = i*2.399963229728653, radius = 2.75 + (i%17)*.035;
    positions[i*3] = Math.cos(angle)*radius;
    positions[i*3+1] = ((i*61)%330)/330*4.3-2.15;
    positions[i*3+2] = Math.sin(angle)*radius;
  }
  const stars = new THREE.BufferGeometry();
  stars.setAttribute('position',new THREE.BufferAttribute(positions,3));
  const points = new THREE.Points(stars,new THREE.PointsMaterial({color:0xa2d0ff,size:.019,transparent:true,opacity:.75,depthWrite:false}));
  rig.add(points);
  object3d = center;
}

function updateFrame(t, dt) {
  const p = progress, ease = p*p*(3 - 2*p);
  const mobileOffset = mobile() ? .2 : 1.15;
  const baseX = mobileOffset + (p > .5 ? -.75 * (p - .5) : .28*p);
  rig.position.x += (baseX - rig.position.x)*.055;
  rig.position.y += ((-.23 + Math.sin(p*Math.PI*2)*.27) - rig.position.y)*.055;
  rig.rotation.y += ((p*4.3 + pointer.x*.14 + Math.sin(t*.13)*.06) - rig.rotation.y)*.05;
  rig.rotation.x += ((p*1.08 - .16 - pointer.y*.085) - rig.rotation.x)*.045;
  const targetScale = 1 + Math.sin(p*Math.PI)*.18 + .42*p;
  rig.scale.setScalar(rig.scale.x + (targetScale-rig.scale.x)*.05);
  camera.position.z += ((8.8 - p*1.9) - camera.position.z)*.045;
  camera.position.x += ((p*.3 + pointer.x*.1) - camera.position.x)*.04;
  camera.lookAt(0,0,0);
  proceduralParts.forEach((part,index) => {
    const spread = Math.sin(p*Math.PI)*.27*(index+1);
    part.position.z = (index%2 ? -1 : 1)*spread;
    part.rotation.z += dt*(index%2 ? -.06:.055);
  });
  if (mixer) mixer.update(dt);
  const bg = document.querySelector('.experience');
  if (bg) bg.style.setProperty('--scroll', String(ease));
}

function destroy() {
  destroyed = true;
  visible.disconnect();
  resizeObserver?.disconnect();
  renderer?.setAnimationLoop(null);
  scene?.traverse(node => {
    node.geometry?.dispose?.();
    const materials = Array.isArray(node.material) ? node.material : node.material ? [node.material] : [];
    for (const material of materials) {
      for (const value of Object.values(material)) if (value?.isTexture) value.dispose();
      material.dispose();
    }
  });
  renderer?.dispose();
  renderer?.domElement?.remove();
}
window.addEventListener('pagehide', destroy, {once:true});
bootScene();
