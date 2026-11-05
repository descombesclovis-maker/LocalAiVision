"""Behavioral regressions from the first Build 316 human audit."""
import base64
from io import BytesIO
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from local_app import integrations_cli, media_director, workflows, brand_catalog, server, web_hybrid


class HumanAuditTests(unittest.TestCase):
    def test_auth_failure_types_do_not_expose_cli_secrets(self):
        for result, expected in [
            (SimpleNamespace(returncode=0,stdout='token=secret',stderr=''),'authenticated'),
            (SimpleNamespace(returncode=1,stdout='',stderr='Not logged in token=secret'),'authentication_required'),
            (SimpleNamespace(returncode=1,stdout='',stderr='Network unreachable token=secret'),'check_failed'),
            (subprocess.TimeoutExpired(['codex'],12),'timeout'),
            (OSError('token=secret'),'launch_failed'),
        ]:
            with self.subTest(expected=expected),patch.object(integrations_cli,'_codex_cmd',return_value=['codex']),patch.object(integrations_cli,'_run') as run:
                if isinstance(result,Exception):run.side_effect=result
                else:run.return_value=result
                state=integrations_cli.coding_agent_status('codex')['codex']
                self.assertEqual(state['state'],expected)
                self.assertEqual(state['ready'],expected=='authenticated')
                self.assertNotIn('secret',str(state))

    def test_missing_cli_is_not_authenticated(self):
        with patch.object(integrations_cli,'_codex_cmd',return_value=None):
            result=integrations_cli.coding_agent_status('codex')['codex']
        self.assertFalse(result['installed']);self.assertFalse(result['ready'])

    def test_timeout_is_not_reported_as_a_missing_login(self):
        with self.assertRaisesRegex(RuntimeError,'impossible à vérifier'):
            web_hybrid.select_coding_agent('codex',{'codex':{'installed':True,'ready':False,'state':'timeout','detail':'Vérification trop longue.'}})

    def test_public_conditioning_does_not_introduce_human_parts_or_blur(self):
        for prompt in ["Génère une photo d'une personne assise.","Génère-moi une photo d'un chien allongé dans l'herbe.","Génère-moi une photo de produits ménagers comme si c'était une pub."]:
            positive,negative,_=server.prepare_visual_request(prompt,'photo')
            self.assertTrue(positive.startswith(prompt))
            for term in ['hands','fingers','bokeh','depth of field','anatomy']:
                self.assertNotIn(term,positive)
            self.assertNotIn('hands',negative)

    def test_public_defaults_produce_three_seconds_with_model_frame_stride(self):
        import json
        root=Path(__file__).resolve().parents[1]
        graph=json.loads((root/'HunyuanVideo 1.5 T2V.json').read_text())
        settings=media_director.public_plan('Génère un homme qui marche de dos, se retourne et sourit.','hunyuan15',{'fps':None,'duration':None})
        graph=workflows.apply_inputs(graph,settings=settings)
        self.assertEqual(graph['13']['inputs']['length'],49)
        self.assertEqual(graph['17']['inputs']['fps'],16)
        self.assertEqual(graph['7']['inputs']['steps'],50)
        self.assertEqual(graph['14']['inputs']['cfg'],1)
        self.assertEqual(media_director.public_plan('vidéo de 5 secondes à 20 fps','hunyuan15')['duration'],5)
        self.assertEqual(media_director.public_plan('vidéo de 5 secondes à 20 fps','hunyuan15')['fps'],20)

    def test_private_planner_is_unchanged(self):
        before=media_director.plan('Une vidéo','hunyuan15',{'reserved_profile':'nsfw'})
        self.assertEqual(before['fps'],12)
        self.assertNotIn('duration',before)

    def test_uploaded_logo_original_bytes_survive_editing(self):
        from PIL import Image
        raw=BytesIO();Image.new('RGB',(33,17),'cyan').save(raw,'PNG');source=raw.getvalue()
        with tempfile.TemporaryDirectory() as folder:
            brand=brand_catalog.save_brand(folder,{'name':'Test original','logo_data':'data:image/png;base64,'+base64.b64encode(source).decode()})
            original=Path(folder)/'brands'/brand['id']/brand['logo_original_file']
            self.assertEqual(original.read_bytes(),source)
            edited=brand_catalog.save_brand(folder,{'id':brand['id'],'name':'Test modifié'})
            self.assertEqual(edited['logo_original_file'],brand['logo_original_file'])
            self.assertEqual(original.read_bytes(),source)
