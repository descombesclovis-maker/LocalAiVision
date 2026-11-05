"""Read-only local CLI diagnostics. Never opens or prints credential files."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from local_app import integrations_cli

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    cmd=integrations_cli._codex_cmd()
    report={'schema':1,'platform':os.name,'codex':integrations_cli.coding_agent_status('codex')['codex'],
            'launcher':cmd,'node':integrations_cli._which('node','node.exe'),
            'custom_codex_home':bool(os.environ.get('CODEX_HOME')),
            'limits':'Authentication status is the CLI local account check; successful site generation and network access require separate validation. No credential file was read.'}
    data=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(data+'\n',encoding='utf-8')
    print(data)

if __name__=='__main__':main()
