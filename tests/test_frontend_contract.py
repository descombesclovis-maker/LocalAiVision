from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


class InterfaceContract(unittest.TestCase):
    def test_all_static_js_targets_exist_once(self):
        class IDs(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids = []

            def handle_starttag(self, tag, attrs):
                self.ids.extend(v for k, v in attrs if k == 'id')

        root = Path(__file__).resolve().parents[1] / 'local_app/web'
        p = IDs()
        p.feed((root / 'index.html').read_text(encoding='utf-8'))
        self.assertEqual(len(p.ids), len(set(p.ids)))
        js = (root / 'app.js').read_text(encoding='utf-8')
        refs = set(re.findall(r'''(?:\$|querySelector)\(["']#([\w-]+)["']\)''', js))
        # libraryBack is created dynamically by renderLibrary.
        optional_removed = {
            'attachBtn', 'videoAttachBtn', 'imageFile', 'videoFile', 'removeVideo',
            'retouchLibrary', 'retouchCount', 'nsfwPhotoCount', 'nsfwPhotosLibrary',
            'maskCanvas', 'maskSource', 'maskModal', 'editMask', 'maskState',
            'brushSize', 'undoMask', 'clearMask', 'closeMask'
        }
        self.assertEqual(refs - set(p.ids) - optional_removed, {'libraryBack'})

    def test_minimal_model_contract(self):
        root = Path(__file__).resolve().parents[1] / 'local_app/web'
        js = (root / 'app.js').read_text(encoding='utf-8')
        html = (root / 'index.html').read_text(encoding='utf-8')

        self.assertIn('id="modelAuto"', html)
        self.assertIn('id="modelRealistic"', html)
        self.assertIn('id="modelNsfw"', html)
        self.assertNotIn('id="modelAnime"', html)
        self.assertNotIn('id="modelMotion"', html)
        self.assertIn('RealVisXL V5', html)
        self.assertIn('Wan 2.1', html)
        self.assertIn('HY-OmniWeaving', html)
        self.assertIn('HunyuanImage 2.1', html)
        self.assertIn("text to image sdxl.json", js)
        self.assertIn("Video Wan texte.json", js)
        self.assertIn("Isolated HY-OmniWeaving T2V.json", js)
        self.assertIn("Isolated HY-OmniWeaving I2V.json", js)
        self.assertIn("Isolated HunyuanImage 2.1.json", js)
        self.assertNotIn("Isolated HunyuanVideo 1.5.json", js)
        self.assertNotIn("LAB Photo - Juggernaut XL v9.json", js)
        self.assertNotIn("LAB Video - Wan 2.2 TI2V 5B.json", js)
        self.assertNotIn('value="motion"', html)
        self.assertNotIn('value="retouch"', html)
        self.assertIn("exact_prompt:isIsolated", js)

    def test_chat_contract(self):
        root = Path(__file__).resolve().parents[1] / 'local_app/web'
        js = (root / 'app.js').read_text(encoding='utf-8')
        css = (root / 'style.css').read_text(encoding='utf-8')
        html = (root / 'index.html').read_text(encoding='utf-8')
        self.assertIn('dismissKeyboard();', js)
        self.assertIn('LocalAiVision vous répond', js)
        self.assertIn('renderAssistantText', js)
        self.assertIn('id="composerReplyState"', html)
        self.assertIn('stopActiveChat', js)
        self.assertIn('.chat-waiting', css)
        self.assertIn('.chat-stop', css)
        self.assertIn('renameConversation', js)
        self.assertIn('deleteConversation', js)
        self.assertIn('deleteLibraryItem', js)


if __name__ == '__main__':
    unittest.main()
