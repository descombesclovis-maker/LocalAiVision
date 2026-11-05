"""Inspect or benchmark EXISTING public ComfyUI workflows. Never installs anything.

Default: read-only readiness. --run explicitly submits one public render.
No private workflow/LoRA/prompt settings are read or changed. Outputs stay local.
"""
import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_app import workflows, engine_qualification, media_validation
from local_app.atomic_storage import atomic_write

PUBLIC={
    'sdxl':'text to image sdxl.json',
    'hunyuan-image':'Isolated HunyuanImage 2.1.json',
    'hunyuan-t2v':'HunyuanVideo 1.5 T2V.json',
    'wan-t2v':'Video Wan texte.json',
}


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine',choices=PUBLIC,default='sdxl')
    parser.add_argument('--url',default='http://127.0.0.1:8188')
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--case',default='dog-grass')
    parser.add_argument('--seed',type=int,default=314159)
    parser.add_argument('--quality',choices=['draft','balanced','quality','workflow'],default='workflow')
    parser.add_argument('--model-root',type=Path,help='Optional existing ComfyUI models directory: full SHA-256 hashing, no modification.')
    parser.add_argument('--output',type=Path,default=ROOT/'benchmark-results')
    parser.add_argument('--timeout',type=int,default=3600)
    args=parser.parse_args()
    url=urlparse(args.url)
    if url.scheme!='http' or url.hostname not in ('127.0.0.1','localhost','::1') or url.username or url.password:
        parser.error('ComfyUI doit rester sur une adresse loopback HTTP sans identifiants.')
    base=args.url.rstrip('/')
    def request(path,data=None):
        req=Request(base+path,data=json.dumps(data).encode() if data is not None else None,
                    headers={'Content-Type':'application/json'})
        with urlopen(req,timeout=30) as response:return json.load(response)
    receipt={'schema':1,'engine':args.engine,'executed':False,'success':False,
             'outputs_verified':False,'created_at_utc_epoch':time.time(),
             'quality_review':None,'status':'unavailable'}
    args.output.mkdir(parents=True,exist_ok=True)
    report_path=args.output/(args.engine+'-'+str(time.time_ns())+'.json')
    try:
        runtime=request('/system_stats'); info=request('/object_info')
        document=json.loads((ROOT/PUBLIC[args.engine]).read_text(encoding='utf-8'))
        graph=workflows.to_api(document,info)
        workflows.preflight(graph,info)
        cases=json.loads((ROOT/'benchmarks/public-cases.json').read_text())
        case=next((row for row in cases['photo']+cases['video'] if row['id']==args.case),None)
        if case is None:raise ValueError('Cas de référence inconnu.')
        is_video=args.engine.endswith('t2v')
        if bool(case.get('seconds'))!=is_video:raise ValueError('Le scénario doit correspondre au type photo/vidéo du moteur.')
        settings={'seed':args.seed,'quality':args.quality}
        if is_video:settings.update(duration=case['seconds'],fps=16)
        graph=workflows.apply_inputs(graph,case['prompt'],None,None,settings)
        workflows.preflight(graph,info)
        graph_hash=hashlib.sha256(json.dumps(graph,sort_keys=True).encode()).hexdigest()
        model_names=sorted({str(value) for node in graph.values() for key,value in node.get('inputs',{}).items()
                            if key in ('ckpt_name','unet_name','vae_name','clip_name','clip_name1','clip_name2') and isinstance(value,str)})
        models=[]
        for name in model_names:
            row={'name':name,'sha256':None}
            if args.model_root:
                matches=[p for p in args.model_root.rglob(Path(name.replace('\\','/')).name)
                         if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(args.model_root.resolve())]
                if len(matches)==1:row['sha256']=sha(matches[0])
            models.append(row)
        identity_graph=json.loads(json.dumps(graph))
        for node in identity_graph.values():
            for key in ('seed','noise_seed','text'):
                node.get('inputs',{}).pop(key,None)
        configuration_hash=hashlib.sha256(json.dumps(identity_graph,sort_keys=True).encode()).hexdigest()
        identity=engine_qualification.fingerprint(configuration_hash,models,runtime)
        receipt.update(status='available',identity=identity,runtime=runtime,models=models,
                       graph=graph,graph_sha256=graph_hash,case=case,settings=settings,
                       disk_free_bytes=shutil.disk_usage(args.output).free,
                       qualification=engine_qualification.assess(installed=True,available=True,identity=identity))
        if args.run:
            queue=request('/queue')
            if queue.get('queue_running') or queue.get('queue_pending'):
                raise RuntimeError('Une génération est déjà active : benchmark refusé pour ne pas fausser la mesure.')
            started=time.monotonic(); result=request('/prompt',{'prompt':graph,'client_id':'localai-public-benchmark'})
            pid=result.get('prompt_id')
            if not pid:raise RuntimeError('ComfyUI a refusé le graphe : '+json.dumps(result))
            receipt.update(executed=True,prompt_id=pid,status='running')
            atomic_write(report_path,json.dumps(receipt,ensure_ascii=False,indent=2).encode())
            samples=[]
            while time.monotonic()-started<args.timeout:
                stats=request('/system_stats')
                samples.append({'elapsed_seconds':time.monotonic()-started,'system':stats.get('system'), 'devices':stats.get('devices')})
                history=request('/history/'+pid).get(pid)
                if history and (history.get('status',{}).get('completed') or history.get('status',{}).get('status_str') in ('error','failed')):break
                time.sleep(2)
            else:raise TimeoutError('Délai dépassé ; la tâche peut continuer dans ComfyUI. Ne pas relancer sans vérifier sa file.')
            receipt.update(elapsed_including_queue_seconds=time.monotonic()-started,
                           resource_samples=samples,resource_scope='Whole ComfyUI device/system snapshots, not process peaks or exact inference time.',
                           engine_status=history.get('status'))
            if history.get('status',{}).get('status_str') in ('error','failed'):raise RuntimeError('Échec ComfyUI ; consulter engine_status.')
            outputs=[]
            for node in history.get('outputs',{}).values():
                for kind in ('images','videos','gifs'):
                    for output in node.get(kind,[]):
                        name=output.get('filename')
                        if not name:continue
                        params=urlencode({'filename':name,'subfolder':output.get('subfolder',''),'type':output.get('type','output')})
                        destination=args.output/(pid+'-'+str(len(outputs))+Path(name).suffix)
                        with urlopen(base+'/view?'+params,timeout=120) as stream,destination.open('wb') as target:
                            shutil.copyfileobj(stream,target)
                        if not destination.stat().st_size:raise RuntimeError('Sortie vide.')
                        validation=media_validation.inspect_output(destination)
                        outputs.append({'file':destination.name,'sha256':sha(destination),'engine_output':output,
                                        'technical_validation':validation})
                        receipt['outputs']=outputs
                        if not validation['verified']:
                            raise RuntimeError('Sortie non validée techniquement : '+validation.get('error','décodage absent'))
            if not outputs:raise RuntimeError('Aucun fichier de sortie vérifiable.')
            receipt.update(outputs=outputs,outputs_verified=True,success=True,status='tested')
            receipt['qualification']=engine_qualification.assess(installed=True,available=True,reports=[receipt],identity=identity)
    except Exception as exc:
        receipt.update(error=str(exc),status='error' if receipt['executed'] else 'unavailable')
    finally:
        atomic_write(report_path,json.dumps(receipt,ensure_ascii=False,indent=2).encode())
    print(json.dumps({'report':str(report_path),'status':receipt['status'],'executed':receipt['executed'],'success':receipt['success']},ensure_ascii=False))
    return 0 if receipt['status'] in ('available','tested') else 2


if __name__=='__main__':raise SystemExit(main())
