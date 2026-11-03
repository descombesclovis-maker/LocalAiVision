"""Reproducible true-path vector traces; never overwrite the locked masters.

Raster originals contain no source curves. Traced gradients are approximated
by colour regions, so derivatives are explicitly distinguished from originals.
Runtime UI deliberately uses original PNGs for exact brand fidelity.
"""
from pathlib import Path
import hashlib
import json
import re
from PIL import Image
import vtracer

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'local_app/web/assets/brand-reference'
OUTPUT = ROOT / 'build/brand314'

def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = {'method':'VTracer 0.6.15, spline colour contours, no embedded raster',
                'fidelity':'Same source composition and proportions; traced glow gradients have colour-region approximation. Not pixel-identical. UI and Windows use originals.',
                'logos':{}}
    for universe in ['Studio','Web','Vision']:
        master = SOURCE / f'LocalAI{universe}_Official_Original.png'
        before = hashlib.sha256(master.read_bytes()).hexdigest()
        name = 'localai-' + universe.lower()
        static = OUTPUT / (name + '-static.svg')
        vtracer.convert_image_to_svg_py(str(master), str(static), colormode='color',
            hierarchical='stacked', mode='spline', filter_speckle=0,
            color_precision=8, layer_difference=6, corner_threshold=60,
            length_threshold=3.0, max_iterations=10, splice_threshold=45, path_precision=3)
        svg = static.read_text()
        if '<image' in svg or 'data:image' in svg or '<path' not in svg:
            raise RuntimeError('A real path-only vector trace is required.')
        svg = re.sub(r'<svg\b', '<svg viewBox="0 0 724 724" role="img" aria-label="LocalAI '+universe+' — vector trace"', svg, count=1)
        static.write_text(svg)
        start=svg.index('>',svg.index('<svg'))+1
        body=svg[start:svg.rindex('</svg>')]
        # The moving reflection is clipped by the luminance of the same vector
        # geometry. The logo and its words do not move, warp or change shape.
        animated=svg[:start]+'''<defs><linearGradient id="reflection"><stop stop-color="#fff" stop-opacity="0"/><stop offset=".48" stop-color="#fff" stop-opacity=".4"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient><mask id="material" maskUnits="userSpaceOnUse" x="0" y="0" width="724" height="724" style="mask-type:luminance"><use href="#art"/></mask></defs><style>.reflection{animation:light 7s ease-in-out infinite;transform:translateX(-250px)}@keyframes light{0%,20%{transform:translateX(-250px)}75%,100%{transform:translateX(750px)}}@media(prefers-reduced-motion:reduce){.reflection{animation:none;display:none}}svg[data-paused="true"] .reflection{animation-play-state:paused}</style><g id="art">'''+body+'''</g><g mask="url(#material)"><rect class="reflection" x="0" y="0" width="220" height="724" fill="url(#reflection)"/></g><script><![CDATA[document.addEventListener('visibilitychange',()=>document.documentElement.setAttribute('data-paused',String(document.hidden)));window.addEventListener('message',e=>{if(e.source===parent&&e.origin===location.origin)document.documentElement.setAttribute('data-paused',String(Boolean(e.data&&e.data.pauseBrandMotion)))});]]></script></svg>'''
        (OUTPUT / (name+'-animated.svg')).write_text(animated)
        with Image.open(master) as image:
            for size in [96,256,4096]:
                image.resize((size,size),Image.Resampling.LANCZOS).save(OUTPUT/(name+f'-original-{size}.png'))
        after=hashlib.sha256(master.read_bytes()).hexdigest()
        if before != after:raise RuntimeError('Master changed during export.')
        manifest['logos'][universe]={'master_sha256':before,'viewBox':'0 0 724 724','static_svg_bytes':static.stat().st_size}
    (OUTPUT/'provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(OUTPUT)

if __name__=='__main__':build()
