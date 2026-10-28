"""Regressions for ComfyUI-style project selection and the file-based agent loop."""
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from local_app import web_builder, web_hybrid

ROOT = Path(__file__).resolve().parent.parent


class WebProjectHubTests(unittest.TestCase):
    def test_web_entry_opens_hub_before_editor(self):
        server = (ROOT / "local_app/server.py").read_text(encoding="utf-8")
        hub = (ROOT / "local_app/web/localaiweb-projects.html").read_text(encoding="utf-8")
        editor = (ROOT / "local_app/web/localaiweb.html").read_text(encoding="utf-8")
        hub_js = (ROOT / "local_app/web/localaiweb-projects.js").read_text(encoding="utf-8")
        editor_js = (ROOT / "local_app/web/localaiweb.js").read_text(encoding="utf-8")
        self.assertIn('if u.path in ("/localaiweb", "/localaiweb/"):', server)
        self.assertIn('if u.path == "/localaiweb/editor":', server)
        self.assertIn('localaiweb-projects.html', server)
        self.assertIn('id="createProject"', hub)
        self.assertIn('id="projectsGrid"', hub)
        self.assertIn('id="projectSearch"', hub)
        self.assertIn('id="createDialog"', hub)
        self.assertIn('id="projectName"', hub)
        self.assertIn('/api/web/projects', hub_js)
        self.assertIn('/api/web/project/create', hub_js)
        self.assertIn('/localaiweb/editor?id=', hub_js)
        self.assertIn('encodeURIComponent(p.id)', hub_js)
        self.assertIn('id="lawPreview"', editor)
        self.assertIn('id="lawChat"', editor)
        self.assertEqual(editor.count('data-view='), 3)
        self.assertIn("new URLSearchParams(window.location.search)", editor_js)
        self.assertNotIn("projects[0].id", editor_js)
        self.assertNotIn("name:'Mon site web'", editor_js)
        self.assertNotIn("name:'Mon expérience 3D'", editor_js)

    def test_project_files_remain_isolated_and_browser_thumbnails_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=web_builder.LocalAiWebStore(tmp,lambda *_:'{}')
            a=store.create('Projet A')
            b=store.create('Projet B')
            aid,bid=a['project']['id'],b['project']['id']
            path=store.project_dir(aid)/'site'/'.localaiweb-qa'
            path.mkdir()
            (path/'ordinateur.png').write_bytes(b'png-test')
            with zipfile.ZipFile(io.BytesIO(store.export_zip(aid))) as archive:
                self.assertNotIn('.localaiweb-qa/ordinateur.png',archive.namelist())
            with zipfile.ZipFile(io.BytesIO(store.export_zip(bid))) as archive:
                self.assertNotIn('.localaiweb-qa/ordinateur.png',archive.namelist())
            self.assertEqual(store.meta(aid)['name'],'Projet A')
            self.assertEqual(store.meta(bid)['name'],'Projet B')
            self.assertNotEqual(aid,bid)


class CodingAgentWorkflowTests(unittest.TestCase):
    def test_requires_an_authenticated_agent_in_premium_mode(self):
        self.assertEqual(web_hybrid.select_coding_agent('auto',{'claude':{'ready':True},
                                                             'codex':{'ready':True}}),'claude')
        self.assertEqual(web_hybrid.select_coding_agent('codex',{'codex':{'ready':True}}),'codex')
        self.assertEqual(web_hybrid.select_coding_agent('local',{}),'local')
        with self.assertRaisesRegex(RuntimeError,'Claude Code'):
            web_hybrid.select_coding_agent('auto',{'codex':{'ready':True}})
        with self.assertRaisesRegex(RuntimeError,'Claude Code'):
            web_hybrid.select_coding_agent('auto',{},allow_local_fallback=True)
        with self.assertRaisesRegex(RuntimeError,'Aucun agent professionnel'):
            web_hybrid.select_coding_agent('auto',{})
        with self.assertRaisesRegex(RuntimeError,'Claude Code'):
            web_hybrid.select_coding_agent('claude',{'codex':{'ready':True}})

    def test_successful_agent_uses_real_browser_screenshots_for_critique(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=web_builder.LocalAiWebStore(tmp,lambda *_:'{}')
            pid=store.create('Premium')['project']['id']
            requests=[]
            def agent(site,prompt):
                requests.append(prompt)
                return {'summary':'Site créé'}
            report={'ok':True,'findings':[],'syntax':{'ok':True,'issues':[]},
                    'preflight':{'ok':True,'score':95,'blockers':[]},
                    'build':{'ok':True,'kind':'static'}}
            screenshot={'status':'passed','issues':[],'reviewed':True,'screenshots':[
                {'mode':'ordinateur','path':'.localaiweb-qa/ordinateur.png'},
                {'mode':'telephone','path':'.localaiweb-qa/telephone.png'}]}
            with patch('local_app.web_hybrid.code_quality_report',return_value=report), \
                 patch('local_app.web_browser_qa.review',return_value=screenshot):
                output=web_hybrid.build_with_agent(store,pid,'Site Poisson-Trap en bleu et vert',agent,
                                                     object(),{'generated':[],'notes':[]})
            self.assertEqual(len(requests),2)
            self.assertIn('QUALITY GATE',requests[-1])
            self.assertIn('.localaiweb-qa/telephone.png',requests[-1])
            self.assertTrue(output['hybrid_validation']['visual']['reviewed'])
            self.assertEqual(output['hybrid_validation']['repairs'],1)
            self.assertIn('visual',store.meta(pid)['last_agent_quality'])

    def test_playwright_qa_availability_is_never_faked(self):
        from local_app import web_browser_qa
        with tempfile.TemporaryDirectory() as tmp:
            result=web_browser_qa.review(Path(tmp))
            self.assertEqual(result['status'],'failed')
            self.assertFalse(result['reviewed'])


if __name__=="__main__":
    unittest.main()
