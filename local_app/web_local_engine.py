"""Installed local inference only. Never installs, downloads or calls cloud agents."""
import json
import os
from urllib.request import Request, urlopen

OLLAMA='http://127.0.0.1:11434'


def _ollama(path, payload=None, timeout=2):
    request=Request(OLLAMA+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with urlopen(request,timeout=timeout) as response:return json.load(response)


def status():
    from local_app import llm
    native=llm.status()
    if native.get('online') or (native.get('model') and native.get('engine')):
        return {'installed':True,'ready':True,'backend':'llama.cpp','model':native.get('model_name'),
                'state':'available','detail':'Modèle local installé ; vitesse et qualité dépendent du matériel.'}
    try:
        models=_ollama('/api/tags').get('models',[])
        # Exclude cloud-tagged models: a local daemon is not proof of local inference.
        models=[m for m in models if str(m.get('name','')).strip() and not any('cloud' in str(m.get(k,'')).lower() for k in ('name','model','remote_host')) and not m.get('remote_model')]
        requested=os.getenv('LOCALAIWEB_LOCAL_MODEL','').strip()
        if requested:models=[m for m in models if m.get('name')==requested]
        models.sort(key=lambda m:('coder' not in m.get('name','').lower(),int(m.get('size') or 0)))
        if models:
            return {'installed':True,'ready':True,'backend':'Ollama','model':models[0]['name'],
                    'state':'available','detail':'Modèle installé dans Ollama, exécution locale ; aucun téléchargement automatique.'}
    except (OSError,ValueError,TypeError):pass
    return {'installed':False,'ready':False,'backend':None,'model':None,'state':'missing_model',
            'detail':'Moteur local : installe un modèle GGUF avec llama.cpp ou un modèle de code local dans Ollama. Aucun modèle ne sera téléchargé sans ton accord.'}


def generate(system,context,prompt,*,engine=None):
    active=engine or status()
    if not active.get('ready'):raise RuntimeError(active.get('detail') or 'Aucun modèle local installé.')
    messages=[{'role':'system','content':system},{'role':'user','content':'CURRENT PROJECT FILES:\n'+context+'\n\nREQUEST:\n'+prompt}]
    if active.get('backend')=='llama.cpp':
        from local_app import llm
        return llm.chat(messages,{'temperature':0.25,'top_p':0.9,'max_tokens':8192})
    if active.get('backend')!='Ollama':raise ValueError('Moteur local inconnu.')
    data=_ollama('/api/chat',{'model':active['model'],'messages':messages,'stream':False,'format':'json',
                           'options':{'temperature':0.25,'num_predict':8192,'num_ctx':16384}},timeout=300)
    text=(data.get('message') or {}).get('content')
    if not isinstance(text,str) or not text.strip():raise RuntimeError('Le modèle local n’a pas renvoyé de fichiers.')
    return text
