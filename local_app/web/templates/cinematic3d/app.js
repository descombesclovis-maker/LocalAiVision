// LocalAiWeb Studio — immersive PBR product showcase, Three.js r186.
// A neutral procedural piece is rendered until a real product GLB is supplied.
// No commercial product geometry is fabricated from a photograph.
import {clamp, qualityProfile, renderPixelRatio, adaptResolution, lerpDamp, smoothstep} from './quality.mjs';

const root = document.querySelector('.experience');
const stage = document.getElementById('three-stage');
const status = document.getElementById('scene-status');
const modeSelect = document.getElementById('scene-quality');
const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
const mobileQuery = window.matchMedia('(max-width: 700px)');
const saveData = navigator.connection?.saveData === true;
const hardware = {get mobile(){return mobileQuery.matches}, saveData,
  deviceMemory:navigator.deviceMemory, hardwareConcurrency:navigator.hardwareConcurrency};
const pathKey = 'localaiweb-scene-quality:' + window.location.pathname;
const prefersMotion = () => !motion.matches;
const state = {
  started:false, destroyed:false, visible:true, active:!document.hidden,
  contextLost:false, mode:'auto', profile:null, adaptiveScale:1,
  progress:0, pointerX:0, pointerY:0, width:0, height:0,
  renderer:null, scene:null, camera:null, rig:null, object:null,
  mixer:null, procedural:[], environmentTarget:null, frameLast:0,
  statsSum:0, statsCount:0, sampleSince:0, lastTimestamp:0, shadowLight:null,
  observers:[], disposables:[],
};
const setStatus = text => {if(status) status.textContent = text;};
const templateMode = root?.dataset.quality || 'auto';
let storedMode = 'auto';
try{storedMode = sessionStorage.getItem(pathKey) || templateMode;}catch{storedMode = templateMode;}
state.mode = storedMode;
state.profile = qualityProfile(state.mode, hardware);
if(modeSelect) {
  modeSelect.value = ['auto','quality','balanced','performance'].includes(storedMode) ? storedMode : 'auto';
  modeSelect.addEventListener('change', () => {
    state.mode = modeSelect.value;
    state.profile = qualityProfile(state.mode, hardware);
    state.adaptiveScale = 1;
    state.statsCount = 0;
    state.statsSum = 0;
    try{sessionStorage.setItem(pathKey, state.mode);}catch{}
    configureQuality();
    setStatus('Rendu '+state.profile.selected+' activé.');
  });
}

function trackEvent(element, name, callback, options) {
  element.addEventListener(name, callback, options);
  state.disposables.push(() => element.removeEventListener(name, callback, options));
}

function updateProgress() {
  const bounds = root.getBoundingClientRect();
  state.progress = clamp(-bounds.top/Math.max(1,bounds.height-innerHeight),0,1);
  const hero = document.querySelector('.hero-copy');
  if(hero && prefersMotion()){
    hero.style.opacity = String(1 - smoothstep(.04,.24,state.progress));
    hero.style.transform = 'translate3d(0,'+ (-55*state.progress) +'px,0)';
    hero.style.visibility = state.progress > .25 ? 'hidden' : 'visible';
  }
}
updateProgress();
trackEvent(window,'scroll',updateProgress,{passive:true});
trackEvent(window,'resize',updateProgress,{passive:true});
trackEvent(window,'pointermove',e=>{
  state.pointerX=clamp((e.clientX/innerWidth-.5)*2,-1,1);
  state.pointerY=clamp((e.clientY/innerHeight-.5)*2,-1,1);
},{passive:true});
trackEvent(document,'visibilitychange',()=>{
  state.active=!document.hidden;
  state.frameLast=0;
  state.statsCount=0;
  state.statsSum=0;
});
const viewportObserver=new IntersectionObserver(entries=>{
  state.visible=entries[0]?.isIntersecting ?? true;
  if(state.visible) state.frameLast=0;
},{rootMargin:'80px'});
viewportObserver.observe(root);
state.observers.push(()=>viewportObserver.disconnect());

function configureQuality(){
  const {renderer,profile} = state;
  if(!renderer || !profile || state.destroyed) return;
  renderer.setPixelRatio(renderPixelRatio(profile,devicePixelRatio,state.adaptiveScale));
  if(state.width && state.height) renderer.setSize(state.width,state.height,false);
  renderer.shadowMap.enabled=profile.realtimeShadows && !hardware.mobile;
  renderer.shadowMap.type=state.three?.PCFSoftShadowMap;
  renderer.transmissionResolutionScale=profile.selected==='quality' ? .8 : .55;
  if(state.shadowLight) {
    state.shadowLight.castShadow=renderer.shadowMap.enabled;
    state.shadowLight.shadow.mapSize.set(Math.max(profile.shadowSize,256),Math.max(profile.shadowSize,256));
    if(state.shadowLight.shadow.map) {
      state.shadowLight.shadow.map.dispose();
      state.shadowLight.shadow.map=null;
    }
  }
}

function normalizeGeometry(THREE,object){
  // Re-centering a GLB without destroying the source hierarchy or its authored materials.
  object.updateWorldMatrix(true,true);
  const box=new THREE.Box3().setFromObject(object);
  if(box.isEmpty())throw Error('Modèle sans géométrie.');
  const size=box.getSize(new THREE.Vector3()), center=box.getCenter(new THREE.Vector3());
  const radius=Math.max(size.x,size.y,size.z);
  if(!Number.isFinite(radius) || radius<.00001)throw Error('Dimensions invalides pour le modèle.');
  const scale=3.15/radius;
  const wrapper=new THREE.Group();
  object.position.sub(center).multiplyScalar(scale);
  object.scale.multiplyScalar(scale);
  wrapper.add(object);
  object.traverse(node=>{
    if(!node.isMesh)return;
    node.castShadow=state.profile.realtimeShadows && !hardware.mobile;
    node.receiveShadow=true;
    const mats=Array.isArray(node.material)?node.material:[node.material];
    mats.forEach(mat=>{
      if(!mat)return;
      if('envMapIntensity' in mat)mat.envMapIntensity=Math.max(.9,mat.envMapIntensity||0);
      if('side' in mat && mat.side===THREE.DoubleSide)mat.needsUpdate=true;
      if(mat.map && 'anisotropy' in mat.map)mat.map.anisotropy=Math.min(8,state.renderer.capabilities.getMaxAnisotropy());
    });
  });
  return wrapper;
}

function buildProcedural(THREE){
  // A stylized PBR precision object, not a purported physical product replica.
  const metal = new THREE.MeshPhysicalMaterial({
    color:0x7e95b2,metalness:1,roughness:.18,clearcoat:.46,clearcoatRoughness:.08,
    envMapIntensity:1.65
  });
  const ceramic = new THREE.MeshPhysicalMaterial({
    color:0x10192b,metalness:.36,roughness:.18,clearcoat:1,clearcoatRoughness:.06,
    envMapIntensity:1.25
  });
  const trim = new THREE.MeshStandardMaterial({color:0xdaf2fa,metalness:1,roughness:.12,envMapIntensity:1.7});
  const lime=new THREE.MeshBasicMaterial({color:0xbde96b,toneMapped:false});
  const center=new THREE.Group();
  const shell=new THREE.Mesh(new THREE.IcosahedronGeometry(1.33,5),metal);
  shell.castShadow=true;
  center.add(shell);
  const seams=new THREE.Mesh(new THREE.IcosahedronGeometry(1.39,2),ceramic);
  seams.material.wireframe=true;
  center.add(seams);
  const core=new THREE.Mesh(new THREE.SphereGeometry(.17,32,20),lime);
  core.position.set(.9,.87,1.17);
  center.add(core);
  state.rig.add(center);
  const rings=[
    {radius:1.85,tube:.048,rot:[1.13,.26,.25],material:trim},
    {radius:2.28,tube:.018,rot:[.32,.7,-.67],material:metal},
    {radius:1.72,tube:.027,rot:[.6,.1,.83],material:lime},
  ];
  rings.forEach(spec=>{
    const mesh=new THREE.Mesh(new THREE.TorusGeometry(spec.radius,spec.tube,12,128),spec.material);
    mesh.rotation.set(...spec.rot);
    mesh.castShadow=true;
    state.rig.add(mesh);
    state.procedural.push(mesh);
  });
  // Sparse stars are static Points, not expensive object-per-star meshes.
  const positions=new Float32Array(210*3);
  for(let i=0;i<210;i++){
    const a=i*2.3999632297, r=2.9+(i%13)*.06;
    positions[i*3]=Math.cos(a)*r;
    positions[i*3+1]=((i*41)%210)/210*4.1-2.05;
    positions[i*3+2]=Math.sin(a)*r;
  }
  const geometry=new THREE.BufferGeometry();
  geometry.setAttribute('position',new THREE.BufferAttribute(positions,3));
  state.rig.add(new THREE.Points(geometry,new THREE.PointsMaterial({
    color:0xa3caff,size:.018,transparent:true,opacity:.65,depthWrite:false
  })));
  state.object=center;
}

async function loadProduct(THREE,path){
  if(!/^assets\/[a-zA-Z0-9_./ -]+\.glb$/i.test(path)||path.split('/').includes('..')){
    throw Error('Chemin GLB invalide : utilisez assets/nom.glb.');
  }
  const {GLTFLoader}=await import('three/addons/loaders/GLTFLoader.js');
  const loader=new GLTFLoader();
  // Official Three decoders support production assets using meshopt, Draco and Basis/KTX2.
  let draco,ktx2;
  try{
    const [{DRACOLoader},{KTX2Loader},meshopt] = await Promise.all([
      import('three/addons/loaders/DRACOLoader.js'),
      import('three/addons/loaders/KTX2Loader.js'),
      import('three/addons/libs/meshopt_decoder.module.js'),
    ]);
    draco=new DRACOLoader();
    draco.setDecoderPath('https://cdn.jsdelivr.net/npm/three@0.186.1/examples/jsm/libs/draco/');
    loader.setDRACOLoader(draco);
    ktx2=new KTX2Loader();
    ktx2.setTranscoderPath('https://cdn.jsdelivr.net/npm/three@0.186.1/examples/jsm/libs/basis/');
    ktx2.detectSupport(state.renderer);
    loader.setKTX2Loader(ktx2);
    loader.setMeshoptDecoder(meshopt.MeshoptDecoder);
  }catch(error){
    console.info('LocalAiWeb: compressed GLB decoders not available; standard GLB remains supported.',error);
  }
  try{
    setStatus('Chargement du modèle 3D...');
    const gltf=await loader.loadAsync(path,evt=>{
      if(evt.total)setStatus('Chargement 3D : '+Math.round(evt.loaded/evt.total*100)+' %');
    });
    if(state.destroyed)return;
    state.object=normalizeGeometry(THREE,gltf.scene);
    state.rig.add(state.object);
    if(gltf.animations?.length){
      state.mixer=new THREE.AnimationMixer(gltf.scene);
      gltf.animations.slice(0,2).forEach(clip=>state.mixer.clipAction(clip).play());
    }
    setStatus('Modèle GLB chargé : matière PBR et caméra cinématique actives.');
  }finally{
    // KTX2Loader worker resources and Draco worker resources can be released after parsing.
    draco?.dispose();
    ktx2?.dispose();
  }
}

async function setupEnvironment(THREE){
  try{
    const {RoomEnvironment}=await import('three/addons/environments/RoomEnvironment.js');
    const pmrem=new THREE.PMREMGenerator(state.renderer);
    const room=new RoomEnvironment();
    state.environmentTarget=pmrem.fromScene(room,0.04,.1,100,{size:state.profile.envSize});
    state.scene.environment=state.environmentTarget.texture;
    state.scene.environmentIntensity=1.05;
    pmrem.dispose();
    room.dispose();
  }catch(error){
    // Directional and hemispheric lights still make the scene usable offline.
    console.info('LocalAiWeb: studio environment fallback',error);
  }
}

function studioLights(THREE){
  state.scene.add(new THREE.HemisphereLight(0xdceaff,0x15152a,2.0));
  const key=new THREE.DirectionalLight(0xfff2de,4.2);
  key.position.set(-4,5,6);
  key.shadow.camera.left=-6;key.shadow.camera.right=6;
  key.shadow.camera.top=6;key.shadow.camera.bottom=-6;
  key.shadow.camera.near=.1;key.shadow.camera.far=20;
  key.shadow.bias=-.0002;
  key.shadow.normalBias=.025;
  key.shadow.radius=2.5;
  state.scene.add(key);
  state.shadowLight=key;
  const rim=new THREE.PointLight(0x80b6ff,65,17,2);
  rim.position.set(3,2,-4);
  state.scene.add(rim);
  const bounce=new THREE.PointLight(0xc8ee8c,28,10,2);
  bounce.position.set(-3,-2,3);
  state.scene.add(bounce);
  // A soft transparent contact shadow survives low-power mode without shadow maps.
  const canvas=document.createElement('canvas');
  canvas.width=128;canvas.height=128;
  const ctx=canvas.getContext('2d');
  if(ctx){
    const gradient=ctx.createRadialGradient(64,64,2,64,64,63);
    gradient.addColorStop(0,'rgba(0,0,0,.52)');
    gradient.addColorStop(.43,'rgba(0,0,0,.24)');
    gradient.addColorStop(1,'rgba(0,0,0,0)');
    ctx.fillStyle=gradient;ctx.fillRect(0,0,128,128);
    const shadowTexture=new THREE.CanvasTexture(canvas);
    const disk=new THREE.Mesh(new THREE.PlaneGeometry(5.3,4),new THREE.MeshBasicMaterial({
      map:shadowTexture,transparent:true,depthWrite:false,toneMapped:false,opacity:.75
    }));
    disk.rotation.x=-Math.PI/2;
    disk.position.set(.9,-2.2,0);
    state.scene.add(disk);
  }
}

function onResize(){
  if(!state.renderer || state.destroyed)return;
  const rect=stage.getBoundingClientRect();
  const width=Math.max(1,Math.round(rect.width));
  const height=Math.max(1,Math.round(rect.height));
  if(width===state.width && height===state.height)return;
  state.width=width;state.height=height;
  state.renderer.setSize(width,height,false);
  state.camera.aspect=width/height;
  state.camera.fov=hardware.mobile?43:36;
  state.camera.updateProjectionMatrix();
  configureQuality();
}

function updateScene(time,dt){
  const p=state.progress;
  const targetX=(hardware.mobile?.1:1.05)+Math.sin(p*Math.PI)*.26-(p>.52?(p-.52)*.7:0);
  state.rig.position.x=lerpDamp(state.rig.position.x,targetX,dt,6);
  state.rig.position.y=lerpDamp(state.rig.position.y,-.10+Math.sin(p*Math.PI*2)*.30,dt,6);
  state.rig.rotation.y=lerpDamp(state.rig.rotation.y,p*4.2+state.pointerX*.14+Math.sin(time*.16)*.05,dt,5);
  state.rig.rotation.x=lerpDamp(state.rig.rotation.x,p*.94-.12-state.pointerY*.08,dt,5);
  const targetScale=1+Math.sin(p*Math.PI)*.16+.31*p;
  state.rig.scale.setScalar(lerpDamp(state.rig.scale.x,targetScale,dt,6));
  state.camera.position.z=lerpDamp(state.camera.position.z,8.8-1.6*p,dt,4.5);
  state.camera.position.x=lerpDamp(state.camera.position.x,.35*p+state.pointerX*.07,dt,4);
  state.camera.lookAt(0,0,0);
  state.procedural.forEach((part,index)=>{
    part.position.z=(index%2?-1:1)*Math.sin(p*Math.PI)*.24*(index+1);
    part.rotation.z+=dt*(index%2?-.055:.04);
  });
  if(state.mixer)state.mixer.update(dt);
}

function frame(timeMs){
  if(state.destroyed||state.contextLost||!state.active||!state.visible)return;
  const minFrameGap=1000/state.profile.targetFPS;
  const elapsed=state.frameLast ? timeMs-state.frameLast : minFrameGap;
  // Skip work on 120/144 Hz screens if the scene only needs 60 FPS.
  if(state.frameLast && elapsed < minFrameGap*.91)return;
  state.frameLast=timeMs;
  const dt=Math.min(elapsed/1000,.06);
  updateScene(timeMs/1000,dt);
  state.renderer.render(state.scene,state.camera);
  if(!root.classList.contains('has-webgl'))root.classList.add('has-webgl');
  if(elapsed>0 && elapsed<130){
    state.statsSum+=elapsed;
    state.statsCount++;
    if(state.statsCount>=48){
      const average=state.statsSum/state.statsCount;
      const budget=Math.max(state.profile.frameBudget,1000/state.profile.targetFPS*1.25);
      const scale=adaptResolution(state.adaptiveScale,average,budget,state.profile);
      state.statsSum=0;state.statsCount=0;
      if(scale!==state.adaptiveScale){
        state.adaptiveScale=scale;
        configureQuality();
      }
    }
  }
}

async function bootScene(){
  if(!root||!stage)return;
  if(!prefersMotion()){
    setStatus('Mouvement réduit : rendu graphique statique pour votre confort.');
    return;
  }
  try{
    const THREE=await import('three');
    if(state.destroyed)return;
    state.three=THREE;
    state.renderer=new THREE.WebGLRenderer({
      alpha:true,antialias:state.profile.selected==='quality' && !hardware.mobile,
      powerPreference:hardware.mobile?'low-power':'high-performance',
      stencil:false,
    });
    state.renderer.outputColorSpace=THREE.SRGBColorSpace;
    state.renderer.toneMapping=THREE.ACESFilmicToneMapping;
    state.renderer.toneMappingExposure=1.16;
    state.renderer.setClearColor(0x080b14,0);
    state.renderer.domElement.setAttribute('aria-hidden','true');
    stage.appendChild(state.renderer.domElement);
    trackEvent(state.renderer.domElement,'webglcontextlost',event=>{
      event.preventDefault();
      state.contextLost=true;
      state.renderer.setAnimationLoop(null);
      root.classList.remove('has-webgl');
      setStatus('Contexte graphique interrompu : aperçu alternatif activé.');
    });
    trackEvent(state.renderer.domElement,'webglcontextrestored',()=>{
      // Rebuilding resources is safer than resuming with invalid GPU allocations.
      setStatus('Contexte graphique rétabli : rechargez la page pour réinitialiser la scène.');
    });
    state.scene=new THREE.Scene();
    state.camera=new THREE.PerspectiveCamera(36,1,.1,100);
    state.camera.position.set(0,.2,8.8);
    state.rig=new THREE.Group();
    state.scene.add(state.rig);
    studioLights(THREE);
    configureQuality();
    await setupEnvironment(THREE);
    const modelSrc=(root.dataset.modelSrc||'').trim();
    if(modelSrc){
      try{await loadProduct(THREE,modelSrc);}
      catch(error){
        console.warn('LocalAiWeb: GLB loading failed',error);
        buildProcedural(THREE);
        setStatus('Modèle GLB indisponible : démonstration 3D affichée.');
      }
    }else{
      buildProcedural(THREE);
      setStatus('Scène PBR prête — importez un modèle GLB pour votre produit.');
    }
    if(state.destroyed)return;
    const observer=new ResizeObserver(onResize);
    observer.observe(stage);
    state.observers.push(()=>observer.disconnect());
    onResize();
    state.renderer.setAnimationLoop(frame);
    state.started=true;
  }catch(error){
    console.warn('LocalAiWeb: WebGL fallback',error);
    state.renderer?.setAnimationLoop(null);
    root.classList.remove('has-webgl');
    setStatus('WebGL indisponible : aperçu graphique alternatif affiché.');
  }
}

function destroy(){
  if(state.destroyed)return;
  state.destroyed=true;
  state.observers.forEach(fn=>fn());
  state.disposables.forEach(fn=>fn());
  state.renderer?.setAnimationLoop(null);
  state.scene?.traverse(node=>{
    node.geometry?.dispose?.();
    const materials=Array.isArray(node.material)?node.material:(node.material?[node.material]:[]);
    materials.forEach(mat=>{
      Object.values(mat).forEach(value=>{if(value?.isTexture)value.dispose();});
      mat.dispose();
    });
  });
  state.environmentTarget?.dispose();
  state.renderer?.dispose();
  state.renderer?.domElement?.remove();
}
trackEvent(window,'pagehide',destroy,{once:true});
bootScene();
