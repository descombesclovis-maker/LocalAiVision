import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeMode, qualityProfile, renderPixelRatio, adaptResolution, lerpDamp, smoothstep} from '../local_app/web/templates/cinematic3d/quality.mjs';

test('invalid quality modes fall back to automatic instead of introducing unknown settings',()=>{
  assert.equal(normalizeMode('ultra'), 'auto');
  assert.equal(normalizeMode('quality'), 'quality');
});
test('desktop machines can render premium PBR while mobile defaults to balanced',()=>{
  assert.equal(qualityProfile('auto',{mobile:false,hardwareConcurrency:12,deviceMemory:8}).selected, 'quality');
  assert.equal(qualityProfile('auto',{mobile:true}).selected,'balanced');
  assert.equal(qualityProfile('auto',{mobile:false,saveData:true}).selected,'balanced');
  assert.equal(qualityProfile('performance',{mobile:false}).realtimeShadows,false);
  assert.equal(qualityProfile('quality',{mobile:false}).realtimeShadows,true);
});
test('effective render ratio is always bounded and honors device and mobile limits',()=>{
  const mobile=qualityProfile('quality',{mobile:true});
  assert.ok(renderPixelRatio(mobile,3)<=1.35);
  assert.equal(renderPixelRatio(qualityProfile('performance',{}),2),1);
  assert.ok(renderPixelRatio(qualityProfile('performance',{}),.8,.3)>=.5);
});
test('adaptive resolution lowers quality under sustained overload and recovers slowly',()=>{
  const profile=qualityProfile('balanced',{mobile:true});
  const slower=adaptResolution(1,65,42,profile);
  assert.ok(slower<1);
  assert.ok(slower>=profile.minScale);
  const recovered=adaptResolution(slower,12,42,profile);
  assert.ok(recovered>slower);
  assert.ok(recovered<=1);
  assert.equal(adaptResolution(.8,40,42,profile),.8);
});
test('frame-independent damping and smoothstep are bounded',()=>{
  assert.equal(lerpDamp(5,5,.016),5);
  assert.ok(lerpDamp(0,10,.016,6)>0);
  assert.ok(lerpDamp(0,10,.033,6)>lerpDamp(0,10,.016,6));
  assert.equal(smoothstep(0,1,-10),0);
  assert.equal(smoothstep(0,1,10),1);
  assert.equal(smoothstep(0,1,.5),.5);
});
