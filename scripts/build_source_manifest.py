"""Record precisely which resources and Python sources enter a native build.

The manifest identifies sources, not a promise of bit-identical PE output.
The native CI smoke tests remain required. No binary patching is supported.
"""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def manifest(root=ROOT):
    paths=list((root/'local_app/web').rglob('*'))+list((root/'local_app/data').rglob('*'))+list((root/'local_app').glob('*.py'))+list(root.glob('*.json'))
    return {'schema':1,'product_build':'316','files':{
        p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths) if p.is_file() and not p.is_symlink() and p.name!='source_manifest.json'}}


if __name__=='__main__':
    data=manifest()
    data['commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    target=ROOT/'local_app/data/source_manifest.json'
    target.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(str(target),len(data['files']),'source/resource hashes')
