import copy
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch, MagicMock
from urllib.request import Request, urlopen

TEST_DATA = tempfile.TemporaryDirectory()
os.environ['LOCALVISIONAI_DATA'] = TEST_DATA.name
os.environ['LOCALVISIONAI_SKIP_SETUP'] = '1'
from local_app import server, workflows, llm, bootstrap_windows as boot
ROOT = Path(__file__).resolve().parents[1]


def spec(**entries):
    return {'input': {'required': entries}, 'input_order': {'required': list(entries)}}


class Workflows(unittest.TestCase):
    def test_linked_widgets_do_not_shift_batch_size(self):
        wf={'nodes':[{'id':1,'type':'Dims','inputs':[],'widgets_values':[832,480,81]},
            {'id':2,'type':'Latent','inputs':[{'name':'width','link':1},{'name':'height','link':2},{'name':'length','link':3}], 'widgets_values':[832,480,81,1]}],
            'links':[[1,1,0,2,0,'INT'],[2,1,1,2,1,'INT'],[3,1,2,2,2,'INT']]}
        info={'Dims':spec(width=['INT'],height=['INT'],length=['INT']), 'Latent':spec(width=['INT'],height=['INT'],length=['INT'],batch_size=['INT'])}
        api=workflows.to_api(wf,info)
        self.assertEqual(api['2']['inputs']['batch_size'],1)
        self.assertEqual(api['2']['inputs']['width'],['1',0])

    def test_seed_control_is_skipped_but_prompt_fixed_preserved(self):
        info={'KSampler':spec(seed=['INT'],steps=['INT']), 'CLIPTextEncode':spec(text=['STRING'])}
        wf={'nodes':[{'id':1,'type':'KSampler','widgets_values':[123,'randomize',20]}, {'id':2,'type':'CLIPTextEncode','widgets_values':['fixed']}]}
        result=workflows.to_api(wf,info)
        self.assertEqual(result['1']['inputs'],{'seed':123,'steps':20})
        self.assertEqual(result['2']['inputs']['text'],'fixed')

    def test_default_steps_preserved_and_explicit_zero_seed(self):
        wf=json.loads((ROOT/'Video Wan texte.json').read_text())
        old=copy.deepcopy(wf)
        workflows.apply_inputs(wf,'une forêt',settings={'seed':0})
        self.assertEqual(wf['8']['inputs']['steps'],old['8']['inputs']['steps'])
        self.assertEqual(wf['6']['inputs'],old['6']['inputs'])
        self.assertEqual(wf['8']['inputs']['seed'],0)
        self.assertEqual(wf['4']['inputs']['text'],'une forêt')

    def test_negative_cleared_and_custom_negative_not_overwritten(self):
        wf=json.loads((ROOT/'Retouche SDXL masque.json').read_text())
        wf['5']['inputs']['text']='color, colored'
        wf['custom']={'class_type':'Custom','inputs':{'prompt':'old','negative_prompt':'bad'}}
        workflows.apply_inputs(wf,'une veste bleue',negative='')
        self.assertEqual(wf['5']['inputs']['text'],'')
        self.assertEqual(wf['custom']['inputs']['negative_prompt'],'')
        self.assertEqual(wf['custom']['inputs']['prompt'],'une veste bleue')

    def test_wan_frames_and_fps_defaults(self):
        wf=json.loads((ROOT/'Video Wan texte.json').read_text())
        workflows.apply_inputs(wf,settings={'duration':5})
        self.assertEqual(wf['6']['inputs']['length'],81)
        self.assertEqual(wf['10']['inputs']['fps'],16)

    def test_schnell_preset_and_manual_steps(self):
        wf={'1':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':'flux1-schnell-fp8.safetensors'}},'2':{'class_type':'KSampler','inputs':{'steps':7}}}
        workflows.apply_inputs(wf,settings={'quality':'quality'})
        self.assertEqual(wf['2']['inputs']['steps'],4)
        workflows.apply_inputs(wf,settings={'quality':'quality','steps':6})
        self.assertEqual(wf['2']['inputs']['steps'],6)

    def test_reroutes_resolved_and_bypassed_savers_ignored(self):
        wf={'nodes':[{'id':1,'type':'Source'},{'id':2,'type':'Reroute','inputs':[{'name':'x','link':1}]},{'id':3,'type':'Save','inputs':[{'name':'x','link':2}]},{'id':4,'type':'Save','mode':4}], 'links':[[1,1,0,2,0,'IMAGE'],[2,2,0,3,0,'IMAGE']]}
        result=workflows.to_api(wf,{'Source':spec(),'Save':spec(x=['IMAGE'])})
        self.assertEqual(result['3']['inputs']['x'],['1',0]);self.assertNotIn('4',result)

    def test_subgraph_actionable_error(self):
        wf=json.loads((ROOT/'Text_to_Video_LTX.json').read_text(encoding='utf-8'))
        with self.assertRaisesRegex(ValueError,'Export \\(API\\)'):
            workflows.to_api(wf,{'present':{}})

    def test_uploaded_filename_not_rejected_by_cached_listing(self):
        wf={'1':{'class_type':'LoadImage','inputs':{'image':'newly_uploaded.png'}}}
        workflows.preflight(wf,{'LoadImage':spec(image=[['old_file.png']])})

    def test_savevideo_legacy_optional_codec_uses_new_default(self):
        wf={'1':{'class_type':'SaveVideo','inputs':{'codec':'auto','format':'auto'}}}
        workflows.preflight(wf,{'SaveVideo':{'input':{'required':{'format':['COMFY_DYNAMICCOMBO_V3']},'optional':{'codec':['COMFY_DYNAMICCOMBO_V3']}}}})
        self.assertNotIn('codec',wf['1']['inputs'])

    def test_missing_model_clear_error(self):
        with self.assertRaisesRegex(ValueError,'model.safetensors'):
            workflows.preflight({'1':{'class_type':'Loader','inputs':{'name':'model.safetensors'}}},{'Loader':spec(name=[['other.safetensors']])})

    def test_retouch_separate_mask_and_composite(self):
        wf=json.loads((ROOT/'Retouche SDXL masque.json').read_text())
        workflows.apply_inputs(wf,image_ref={'name':'source.png'},mask_ref={'name':'paint.png'})
        self.assertEqual(wf['2']['inputs']['image'],'source.png')
        self.assertEqual(wf['3']['inputs'],{'image':'paint.png','channel':'red'})
        self.assertEqual(wf['9']['inputs']['destination'],['2',0])
        self.assertEqual(wf['9']['inputs']['mask'],['3',0])


    def test_vace_profile_and_reference_video_are_supported(self):
        wf=json.loads((ROOT/'Video Motion VACE 1.3B.json').read_text())
        self.assertEqual(workflows.profile(wf), 'vace')
        workflows.apply_inputs(wf, prompt='un personnage qui suit le mouvement',
                               image_ref={'name':'subject.png'},
                               video_ref={'name':'motion.mp4'})
        self.assertEqual(wf['6']['inputs']['file'], 'motion.mp4')
        self.assertEqual(wf['8']['inputs']['image'], 'subject.png')
        self.assertEqual(wf['9']['inputs']['control_video'], ['16',0])
        self.assertEqual(wf['16']['class_type'], 'Canny')

    def test_preflight_accepts_newly_copied_video_filename(self):
        wf={'1':{'class_type':'LoadVideo','inputs':{'file':'lva_new_reference.mp4'}}}
        workflows.preflight(wf,{'LoadVideo':spec(file=[['old_video.mp4']])})


class VisualPromptPreparation(unittest.TestCase):
    def test_explicit_photo_overrides_stale_watercolor_without_rewriting_request(self):
        raw = "génère moi une photo de femme complètement nue"
        prompt, negative, style = server.prepare_visual_request(raw, "watercolor", "")
        self.assertEqual(style, "photo")
        self.assertIn(raw, prompt)
        self.assertNotIn("adult subject", prompt)
        self.assertNotIn("full-body", prompt)
        self.assertNotIn("Watercolor painting", prompt)
        self.assertIn("Technical quality only:", prompt)
        self.assertIn("malformed hands", negative)

    def test_technical_quality_can_be_disabled_for_exact_prompt(self):
        raw = "un portrait éclairé par une fenêtre"
        prompt, negative, style = server.prepare_visual_request(raw, "none", None, technical_quality=False)
        self.assertEqual(prompt, raw)
        self.assertIsNone(negative)
        self.assertIsNone(style)

    def test_explicit_watercolor_keeps_user_wording(self):
        raw = "une aquarelle d'un phare dans la tempête"
        prompt, negative, style = server.prepare_visual_request(raw, "photo", None)
        self.assertEqual(style, "watercolor")
        self.assertTrue(prompt.startswith(raw))
        self.assertNotIn("Watercolor painting", prompt)
        self.assertIn("rendering artifacts", negative)

    def test_selected_style_remains_opt_in_default_without_explicit_medium(self):
        prompt, negative, style = server.prepare_visual_request(
            "un château au sommet d'une falaise", "cinema", "sans texte")
        self.assertEqual(style, "cinema")
        self.assertIn("Visual rendering style only:", prompt)
        self.assertIn("Cinematic", prompt)
        self.assertEqual(negative, "sans texte")

    def test_prompt_semantics_are_not_expanded(self):
        raw = "photo portrait d'une femme adulte nue de face en grand angle"
        prompt, _, _ = server.prepare_visual_request(raw, "none", "")
        self.assertTrue(prompt.startswith(raw))
        self.assertNotIn("strict front view", prompt)
        self.assertNotIn("24mm lens", prompt)
        self.assertNotIn("age 25+", prompt)
        self.assertNotIn("fully nude", prompt)

    def test_user_negative_prompt_is_preserved_verbatim(self):
        raw_negative = "sans texte, sans watermark, pas de flou"
        _, negative, _ = server.prepare_visual_request("portrait photo", "none", raw_negative)
        self.assertEqual(negative, raw_negative)

    def test_realvis_profile_is_sdxl_family(self):
        api={'1':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':'RealVisXL_V5.0_fp16.safetensors'}}}
        self.assertEqual(workflows.profile(api), 'sdxl')

    def test_animagine_profile_does_not_inject_semantics(self):
        api={'1':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':'animagine-xl-4.0-opt.safetensors'}}}
        self.assertEqual(workflows.profile(api), 'animagine')
        raw = "une héroïne sur un balcon"
        prompt, _, style = server.prepare_visual_request(raw, "none", "", "companion-anime")
        self.assertTrue(prompt.startswith(raw))
        self.assertNotIn("anime illustration", prompt)
        self.assertIsNone(style)

    def test_nsfw_workspace_is_isolated_and_preserves_user_prompt(self):
        raw = "portrait studio avec éclairage latéral"

        prompt, negative, style = server.prepare_visual_request(
            raw,
            "none",
            None,
            "nsfw"
        )

        self.assertTrue(prompt.startswith(raw))
        self.assertIn("Prompt fidelity only:", prompt)
        self.assertIn("Technical quality only:", prompt)
        self.assertIn("malformed hands", negative)
        self.assertIsNone(style)

        self.assertTrue((ROOT / "LAB Photo - Juggernaut XL v9.json").is_file())
        self.assertTrue((ROOT / "LAB Video - Wan 2.2 TI2V 5B.json").is_file())

class ServerHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.url='http://127.0.0.1:'+str(cls.httpd.server_port)
        cls.thread=threading.Thread(target=cls.httpd.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown();cls.httpd.server_close()
    def call(self,path,payload=None):
        req=Request(self.url+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urlopen(req,timeout=4) as r:return json.load(r)
    def test_ping_opens_without_engines(self):
        with patch.object(server,'ensure_comfyui',side_effect=AssertionError('must not launch')):
            self.assertEqual(self.call('/api/ping')['app'],'LocalVisionAI')
    def test_health_does_not_launch_engines(self):
        with patch.object(server,'ensure_comfyui',side_effect=AssertionError('must not launch')),patch.object(server,'comfy_online',return_value=(False,'offline')),patch.object(llm,'status',return_value={'online':False}):
            self.assertFalse(self.call('/api/health')['online'])
    def test_import_roundtrip_outside_bundle_and_duplicate_names(self):
        wf={'1':{'class_type':'SaveImage','inputs':{'filename_prefix':'test'}}}
        a=self.call('/api/import-workflow',{'name':'../test.json','workflow':wf})
        b=self.call('/api/import-workflow',{'name':'../test.json','workflow':wf})
        self.assertNotEqual(a['id'],b['id'])
        self.assertTrue(a['id'].startswith('imported/'))
        self.assertEqual(server.load_workflow(a['id']),wf)
        self.assertIn(a['id'],[x['id'] for x in self.call('/api/workflows')['workflows']])
    def test_traversal_rejected(self):
        with self.assertRaises(ValueError):server.load_workflow('imported/../../secret.json')
    def test_chat_stop_endpoint_sets_cancel_flag(self):
        with patch.object(llm,'cancel_chat') as cancel:
            self.assertTrue(self.call('/api/chat/stop',{})['ok'])
            cancel.assert_called_once()

    def test_chat_stream_sends_incremental_ndjson(self):
        req=Request(self.url+'/api/chat/stream',data=json.dumps({'messages':[{'role':'user','content':'salut'}]}).encode(),headers={'Content-Type':'application/json'})
        with patch.object(server,'run_chat_stream',return_value=iter(['Bon','jour'])):
            with urlopen(req,timeout=4) as r:
                lines=[json.loads(line.decode()) for line in r if line.strip()]
        self.assertEqual(lines[0],{'ready':True})
        self.assertEqual([x.get('delta') for x in lines if 'delta' in x],['Bon','jour'])
        self.assertTrue(lines[-1].get('done'))

    def test_logs_readable(self):
        self.assertIn('text',self.call('/api/logs'))


class Lifecycle(unittest.TestCase):
    def test_portable_python_selected_not_application_exe(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'python_embeded').mkdir();(root/'ComfyUI').mkdir()
            (root/'python_embeded/python.exe').touch();(root/'ComfyUI/main.py').touch()
            with patch.object(server.sys,'frozen',True,create=True):
                cmd,cwd=server._comfy_command(root)
                self.assertEqual(Path(cmd[0]).name,'python.exe')
                self.assertEqual(cwd,root/'ComfyUI')
    def test_stop_only_owned_llm_process(self):
        with patch.object(llm,'_proc',None),patch.object(llm,'online',return_value=(True,{})):
            llm.stop_server()
        proc=MagicMock();proc.poll.return_value=None
        with patch.object(llm,'_proc',proc):
            llm.stop_server();proc.terminate.assert_called_once();proc.wait.assert_called_once()
    def test_setup_components_independent(self):
        server._setup_lock.acquire()
        with patch.object(boot,'ensure_comfy',side_effect=RuntimeError('offline')),patch.object(boot,'ensure_llama') as llama,patch.object(boot,'ensure_model') as model:
            server._setup_worker('engines')
            llama.assert_called_once();model.assert_called_once()
            self.assertEqual(server.STARTUP['state'],'error')
            self.assertFalse(server._setup_lock.locked())
    def test_media_validation_precedes_llm_stop(self):
        wf={'1':{'class_type':'LoadImage','inputs':{'image':'old.png'}}}
        with patch.object(server,'ensure_comfyui',return_value=True),patch.object(server,'load_workflow',return_value=wf),patch.object(server,'object_info',return_value={}),patch.object(llm,'stop_server') as stop:
            with self.assertRaisesRegex(ValueError,'image de référence'):
                server.run_generation({'workflow':'x'})
            stop.assert_not_called()
    def test_resume_download_and_repair_incomplete_existing(self):
        class Response(io.BytesIO):
            status=206
            headers={'Content-Length':'3','Content-Range':'bytes 3-5/6'}
        with tempfile.TemporaryDirectory() as folder:
            dest=Path(folder)/'model.gguf';dest.write_bytes(b'x');dest.with_suffix('.gguf.part').write_bytes(b'abc')
            with patch.object(boot.urllib.request,'urlopen',return_value=Response(b'def')) as opener:
                boot._download('https://example.test/file',dest,'test',min_bytes=6)
                self.assertEqual(dest.read_bytes(),b'abcdef')
                self.assertEqual(opener.call_args.args[0].get_header('Range'),'bytes=3-')

    def test_media_status_reports_missing_and_ready_files(self):
        with tempfile.TemporaryDirectory() as folder:
            model_dir=Path(folder)
            with patch.object(boot,'_media_model_dir',return_value=model_dir):
                self.assertFalse(boot.media_status('image')['ready'])
                target=model_dir/'checkpoints'/'RealVisXL_V5.0_fp16.safetensors'
                target.parent.mkdir(parents=True);target.write_bytes(b'x'*(1024**2))
                self.assertTrue(boot.media_status('image')['ready'])

    def test_preflight_auto_installs_missing_sdxl_then_retries(self):
        current={'1':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':'RealVisXL_V5.0_fp16.safetensors'}}}
        missing={'CheckpointLoaderSimple':spec(ckpt_name=[['other.safetensors']])}
        ready={'CheckpointLoaderSimple':spec(ckpt_name=[['RealVisXL_V5.0_fp16.safetensors']])}
        with patch.object(server,'object_info',side_effect=[missing,ready]), patch.object(boot,'ensure_media') as install, patch.object(server,'_restart_owned_comfyui',return_value=False):
            server._preflight_with_media_repair(current)
            install.assert_called_once_with('image')

    def test_preflight_auto_installs_missing_animagine_then_retries(self):
        current={'1':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':'animagine-xl-4.0-opt.safetensors'}}}
        missing={'CheckpointLoaderSimple':spec(ckpt_name=[['other.safetensors']])}
        ready={'CheckpointLoaderSimple':spec(ckpt_name=[['animagine-xl-4.0-opt.safetensors']])}
        with patch.object(server,'object_info',side_effect=[missing,ready]), patch.object(boot,'ensure_media') as install, patch.object(server,'_restart_owned_comfyui',return_value=False):
            server._preflight_with_media_repair(current)
            install.assert_called_once_with('anime')

    def test_preflight_auto_installs_missing_vace_then_retries(self):
        current={'1':{'class_type':'UNETLoader','inputs':{'unet_name':'wan2.1_vace_1.3B_fp16.safetensors'}}}
        missing={'UNETLoader':spec(unet_name=[['other.safetensors']])}
        ready={'UNETLoader':spec(unet_name=[['wan2.1_vace_1.3B_fp16.safetensors']])}
        with patch.object(server,'object_info',side_effect=[missing,ready]), patch.object(boot,'ensure_media') as install, patch.object(server,'_restart_owned_comfyui',return_value=False):
            server._preflight_with_media_repair(current)
            install.assert_called_once_with('motion')

    def test_motion_media_reuses_wan_shared_files(self):
        names=[name for _folder,name,_url in boot.MEDIA_MODELS['motion']]
        self.assertIn('wan2.1_vace_1.3B_fp16.safetensors', names)
        self.assertIn('wan_2.1_vae.safetensors', names)
        self.assertIn('umt5_xxl_fp8_e4m3fn_scaled.safetensors', names)


if __name__=='__main__':unittest.main()
