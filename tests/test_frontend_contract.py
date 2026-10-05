from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

class InterfaceContract(unittest.TestCase):
    def test_all_static_js_targets_exist_once(self):
        class IDs(HTMLParser):
            def __init__(self):super().__init__();self.ids=[]
            def handle_starttag(self,tag,attrs):
                self.ids.extend(v for k,v in attrs if k=='id')
        root=Path(__file__).resolve().parents[1]/'local_app/web'
        p=IDs();p.feed((root/'index.html').read_text(encoding='utf-8'))
        self.assertEqual(len(p.ids),len(set(p.ids)))
        js=(root/'app.js').read_text(encoding='utf-8')+(root/'mask.js').read_text(encoding='utf-8')
        refs=set(re.findall(r'''(?:\$|querySelector)\(["']#([\w-]+)["']\)''',js))
        self.assertEqual(refs-set(p.ids),{'libraryBack'}) # inserted by renderLibrary

    def test_chat_v13_contract(self):
        root=Path(__file__).resolve().parents[1]/'local_app/web'
        js=(root/'app.js').read_text(encoding='utf-8')
        css=(root/'style.css').read_text(encoding='utf-8')
        html=(root/'index.html').read_text(encoding='utf-8')
        self.assertIn('dismissKeyboard();',js)
        self.assertIn('LocalAiVision vous répond',js)
        self.assertIn('renderAssistantText',js)
        self.assertNotIn('.slice(-40)',js)
        self.assertIn('id="composerReplyState"',html)
        self.assertIn('stopActiveChat',js)
        self.assertIn('m.text||m.streaming',js)
        self.assertIn('.chat-waiting',css)
        self.assertIn('.chat-stop',css)
        self.assertIn('.assistant .bubble strong',css)
        self.assertIn('id="modelAuto"',html)
        self.assertIn('id="modelRealistic"',html)
        self.assertIn('id="modelAnime"',html)
        self.assertIn('id="modelMotion"',html)
        self.assertIn('id="modelNsfw"',html)
        self.assertIn('id="nsfwGate"',html)
        self.assertIn('LAB Photo - Juggernaut XL v9.json',js)
        self.assertIn('LAB Video - Wan 2.2 TI2V 5B.json',js)
        self.assertIn('NSFW Image to Image.json',js)
        self.assertIn('NSFW Motion Video.json',js)
        self.assertIn('id="nsfwModePanel"',html)
        self.assertIn('id="nsfwModeImage"',html)
        self.assertIn('id="nsfwModeMotion"',html)
        self.assertIn('id="nsfwPromptMode"',html)
        self.assertIn("nsfwPromptMode",js)
        self.assertIn("exact_prompt",js)
        self.assertIn('id="nsfwPickCharacterImage"',html)
        self.assertIn('id="nsfwPickMotionVideo"',html)
        self.assertIn('createConversationForProfile',js)
        self.assertIn('settingMotionModel',html)
        self.assertIn('renameConversation',js)
        self.assertIn('deleteConversation',js)
        self.assertIn('deleteLibraryItem',js)
        self.assertIn('renameModel',js)
        self.assertIn('settingTechnicalQuality',html)
        self.assertIn('videoFile',html)
        self.assertIn('Video Motion VACE 1.3B.json',js)
        self.assertNotIn('body.reserved-theme',css)
        self.assertNotIn('--reserved-red',css)
