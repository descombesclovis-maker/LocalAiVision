import copy
import io
import json
import os
from pathlib import Path
import tempfile
import threading
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
    def test_default_wan_settings_are_preserved(self):
        wf = json.loads((ROOT / 'Video Wan texte.json').read_text(encoding='utf-8'))
        old = copy.deepcopy(wf)
        workflows.apply_inputs(wf, 'a forest', settings={'seed': 0})
        self.assertEqual(wf['8']['inputs']['steps'], old['8']['inputs']['steps'])
        self.assertEqual(wf['8']['inputs']['seed'], 0)
        self.assertEqual(wf['4']['inputs']['text'], 'a forest')

    def test_omniweaving_t2v_profile_and_defaults(self):
        wf = json.loads((ROOT / 'Isolated HY-OmniWeaving T2V.json').read_text(encoding='utf-8'))
        self.assertEqual(workflows.profile(wf), 'omniweaving-t2v')
        text = next(n for n in wf.values() if n['class_type'] == 'HYOmniWeavingTextEncode' and n['_meta']['title'] == 'Positive Prompt')
        sampling = next(n for n in wf.values() if n['class_type'] == 'ModelSamplingSD3')
        guider = next(n for n in wf.values() if n['class_type'] == 'CFGGuider')
        scheduler = next(n for n in wf.values() if n['class_type'] == 'BasicScheduler')
        self.assertFalse(text['inputs']['think'])
        self.assertEqual(sampling['inputs']['shift'], 7)
        self.assertEqual(guider['inputs']['cfg'], 6)
        self.assertEqual(scheduler['inputs']['steps'], 50)

    def test_hunyuan_image_distilled_profile_and_defaults(self):
        wf = json.loads((ROOT / 'Isolated HunyuanImage 2.1.json').read_text(encoding='utf-8'))
        self.assertEqual(workflows.profile(wf), 'hunyuanimage21')
        sampler = next(n for n in wf.values() if n['class_type'] == 'KSampler')
        guidance = next(n for n in wf.values() if n['class_type'] == 'FluxGuidance')
        sampling = next(n for n in wf.values() if n['class_type'] == 'ModelSamplingSD3')
        self.assertEqual(sampler['inputs']['steps'], 8)
        self.assertEqual(sampler['inputs']['cfg'], 1.0)
        self.assertEqual(guidance['inputs']['guidance'], 3.25)
        self.assertEqual(sampling['inputs']['shift'], 4)

    def test_omniweaving_i2v_quality_presets_and_reference(self):
        wf = json.loads((ROOT / 'Isolated HY-OmniWeaving I2V.json').read_text(encoding='utf-8'))
        self.assertEqual(workflows.profile(wf), 'omniweaving-i2v')
        workflows.apply_inputs(wf, 'gentle camera motion', image_ref={'name': 'start.png'}, settings={'seed': 0, 'quality': 'quality'})
        scheduler = next(n for n in wf.values() if n['class_type'] == 'BasicScheduler')
        loader = next(n for n in wf.values() if n['class_type'] == 'LoadImage')
        text = next(n for n in wf.values() if n['class_type'] == 'HYOmniWeavingTextEncode' and n['_meta']['title'] == 'Positive Prompt')
        self.assertEqual(scheduler['inputs']['steps'], 50)
        self.assertEqual(loader['inputs']['image'], 'start.png')
        self.assertFalse(text['inputs']['think'])
        self.assertEqual(text['inputs']['prompt'], 'gentle camera motion')

    def test_negative_prompt_can_be_empty(self):
        wf = {'1': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'old'}, '_meta': {'title': 'Negative Prompt'}}}
        workflows.apply_inputs(wf, prompt='x', negative='')
        self.assertEqual(wf['1']['inputs']['text'], '')


class PromptTranslation(unittest.TestCase):
    def test_translation_uses_local_llm_faithfully(self):
        with patch.object(llm, 'chat', return_value='A person facing the camera in a red coat.') as chat:
            result = server.translate_visual_prompt_to_english('une personne de face avec un manteau rouge')
        self.assertEqual(result, 'A person facing the camera in a red coat.')
        system = chat.call_args.args[0][0]['content']
        self.assertIn('faithfully', system)
        self.assertIn('Return only the English translation', system)

    def test_exact_prompt_path_does_not_add_profile_text(self):
        raw = 'A studio portrait with side lighting'
        prompt, negative, style = server.prepare_visual_request(raw, 'none', None, technical_quality=False)
        self.assertEqual(prompt, raw)
        self.assertIsNone(negative)
        self.assertIsNone(style)


class MediaModels(unittest.TestCase):
    def test_only_minimal_media_components_remain(self):
        self.assertEqual(set(boot.MEDIA_MODELS), {'image', 'video', 'isolated-image', 'isolated-video', 'isolated-video-i2v'})
        self.assertIn('RealVisXL_V5.0_fp16.safetensors',
                      [n for _f, n, _u in boot.MEDIA_MODELS['image']])
        self.assertIn('wan2.1_t2v_1.3B_fp16.safetensors',
                      [n for _f, n, _u in boot.MEDIA_MODELS['video']])
        self.assertIn('hunyuanimage2.1_distilled_fp8_e4m3fn.safetensors',
                      [n for _f, n, _u in boot.MEDIA_MODELS['isolated-image']])
        self.assertIn('hy_omniweaving_hunyuanvideo15_transformer_fp8_e4m3fn_patched.safetensors',
                      [n for _f, n, _u in boot.MEDIA_MODELS['isolated-video']])
        self.assertIn('hy_omniweaving_hunyuanvideo15_transformer_fp8_e4m3fn_patched.safetensors',
                      [n for _f, n, _u in boot.MEDIA_MODELS['isolated-video-i2v']])
        self.assertIn('image_encoder.safetensors',
                      [n for _f, n, _u in boot.MEDIA_MODELS['isolated-video-i2v']])
        self.assertIn('image_embedder.safetensors',
                      [n for _f, n, _u in boot.MEDIA_MODELS['isolated-video-i2v']])

    def test_media_status_reports_ready_file(self):
        with tempfile.TemporaryDirectory() as folder:
            model_dir = Path(folder)
            with patch.object(boot, '_media_model_dir', return_value=model_dir):
                self.assertFalse(boot.media_status('image')['ready'])
                target = model_dir / 'checkpoints' / 'RealVisXL_V5.0_fp16.safetensors'
                target.parent.mkdir(parents=True)
                target.write_bytes(b'x' * (1024**2))
                self.assertTrue(boot.media_status('image')['ready'])

    def test_cleanup_only_targets_known_legacy_files(self):
        with tempfile.TemporaryDirectory() as folder:
            model_dir = Path(folder)
            old = model_dir / 'checkpoints' / 'animagine-xl-4.0-opt.safetensors'
            keep = model_dir / 'checkpoints' / 'RealVisXL_V5.0_fp16.safetensors'
            old.parent.mkdir(parents=True)
            old.write_bytes(b'old')
            keep.write_bytes(b'keep')
            with patch.object(boot, '_media_model_dir', return_value=model_dir):
                removed = boot.cleanup_obsolete_media()
            self.assertFalse(old.exists())
            self.assertTrue(keep.exists())
            self.assertTrue(any('animagine-xl-4.0-opt.safetensors' in x for x in removed))


class LoraLibrary(unittest.TestCase):
    def test_general_catalog_is_curated_and_described(self):
        rows = server._general_lora_catalog()
        self.assertGreater(len(rows), 20)
        self.assertTrue(all(x.get('description') and x.get('category') for x in rows))
        names = {x.get('name') for x in rows}
        self.assertNotIn('Super_Realistic_Ahegao_for_Hunyuan_Video', names)
        self.assertNotIn('Emma_Watson_Hunyuan_video_Lora', names)
        self.assertIn('Walking_Animation_Hunyuan_Video', names)
        self.assertIn('Orbit_Cam_Character_Hunyuan_Video', names)
        self.assertIn('Move_Enhancer_V3_20', names)
        move = next(x for x in rows if x.get('name') == 'Move_Enhancer_V3_20')
        self.assertEqual(move.get('category'), 'Mouvement')
        self.assertEqual(move.get('source'), 'TensorHub / NoArtifact')
        self.assertIn('8itchWalk4', move.get('trained_words') or [])
        self.assertIn('non garanti', move.get('compatibility') or '')

    def test_lora_stack_inserts_loader_between_hunyuan_sources_and_consumers(self):
        api = {
            '1': {'class_type': 'DualCLIPLoader', 'inputs': {}},
            '2': {'class_type': 'UNETLoader', 'inputs': {}},
            '3': {'class_type': 'CLIPTextEncode', 'inputs': {'clip': ['1', 0], 'text': 'x'}},
            '4': {'class_type': 'ModelSamplingSD3', 'inputs': {'model': ['2', 0], 'shift': 4}},
        }
        with patch.object(server, '_local_lora_metadata', return_value=[{'path': 'quality/test.safetensors'}]):
            out = server._apply_lora_stack(copy.deepcopy(api), [{'path': 'quality/test.safetensors', 'strength': 0.8}])
        loader = next(n for n in out.values() if n['class_type'] == 'LoraLoader')
        loader_id = next(k for k, n in out.items() if n is loader)
        self.assertEqual(out['3']['inputs']['clip'], [loader_id, 1])
        self.assertEqual(out['4']['inputs']['model'], [loader_id, 0])
        self.assertEqual(loader['inputs']['strength_model'], 0.8)

    def test_omniweaving_lora_stack_is_model_only(self):
        api = {
            '1': {'class_type': 'HYOmniWeavingTextEncoderLoader', 'inputs': {}},
            '2': {'class_type': 'HYOmniWeavingUNetLoader', 'inputs': {}},
            '3': {'class_type': 'ModelSamplingSD3', 'inputs': {'model': ['2', 0], 'shift': 7}},
        }
        with patch.object(server, '_local_lora_metadata', return_value=[{'path': 'motion/test.safetensors'}]):
            out = server._apply_lora_stack(copy.deepcopy(api), [{'path': 'motion/test.safetensors', 'strength': 0.5}])
        loader = next(n for n in out.values() if n['class_type'] == 'LoraLoaderModelOnly')
        loader_id = next(k for k, n in out.items() if n is loader)
        self.assertEqual(out['3']['inputs']['model'], [loader_id, 0])
        self.assertEqual(loader['inputs']['strength_model'], 0.5)

    def test_lora_stack_rejects_unknown_local_file(self):
        with patch.object(server, '_local_lora_metadata', return_value=[]):
            with self.assertRaises(ValueError):
                server._apply_lora_stack({'1': {'class_type': 'UNETLoader', 'inputs': {}}}, [{'path': 'missing.safetensors'}])


class ServerHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.url = 'http://127.0.0.1:' + str(cls.httpd.server_port)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def call(self, path, payload=None):
        req = Request(self.url + path,
                      data=None if payload is None else json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json'})
        with urlopen(req, timeout=4) as r:
            return json.load(r)

    def test_ping(self):
        self.assertEqual(self.call('/api/ping')['app'], 'LocalVisionAI')

    def test_health_does_not_launch_engines(self):
        with patch.object(server, 'ensure_comfyui', side_effect=AssertionError('must not launch')),              patch.object(server, 'comfy_online', return_value=(False, 'offline')),              patch.object(llm, 'status', return_value={'online': False}):
            self.assertFalse(self.call('/api/health')['online'])


class LauncherResilience(unittest.TestCase):
    def test_launcher_rejects_second_native_instance(self):
        source = (ROOT / 'local_app' / 'launcher.py').read_text(encoding='utf-8')
        self.assertIn('LocalVisionAI est déjà ouvert', source)
        self.assertIn('return', source)

    def test_http_handler_tolerates_client_disconnects(self):
        source = (ROOT / 'local_app' / 'server.py').read_text(encoding='utf-8')
        self.assertIn('ConnectionAbortedError', source)
        self.assertIn('ConnectionResetError', source)


class Lifecycle(unittest.TestCase):
    def test_portable_python_selected_not_application_exe(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'python_embeded').mkdir()
            (root / 'ComfyUI').mkdir()
            (root / 'python_embeded/python.exe').touch()
            (root / 'ComfyUI/main.py').touch()
            with patch.object(server.sys, 'frozen', True, create=True):
                cmd, cwd = server._comfy_command(root)
                self.assertEqual(Path(cmd[0]).name, 'python.exe')
                self.assertEqual(cwd, root / 'ComfyUI')

    def test_stop_only_owned_llm_process(self):
        proc = MagicMock()
        proc.poll.return_value = None
        with patch.object(llm, '_proc', proc):
            llm.stop_server()
        proc.terminate.assert_called_once()


if __name__ == '__main__':
    unittest.main()
