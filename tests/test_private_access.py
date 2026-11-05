import json
import os
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch
from local_app import private_access, server


class PrivateAccessTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        private_access._sessions.clear();private_access._failures.clear()
        self.env=patch.dict(os.environ,{'LOCALAI_PRIVATE_PIN':'1234'});self.env.start();self.addCleanup(self.env.stop)

    def test_session_revocation_expiry_and_rate_limit(self):
        token,expires=private_access.unlock('1234');cookie=private_access.COOKIE+'='+token
        self.assertTrue(private_access.session(cookie)['authenticated'])
        self.assertNotIn(token,private_access._sessions)
        with patch.object(private_access.time,'time',return_value=expires+1):self.assertIsNone(private_access.session(cookie))
        token,_=private_access.unlock('1234');cookie=private_access.COOKIE+'='+token
        private_access.revoke(cookie);self.assertIsNone(private_access.session(cookie))
        for _ in range(5):
            with self.assertRaises(ValueError):private_access.unlock('wrong')
        with self.assertRaisesRegex(ValueError,'Trop de tentatives'):private_access.unlock('1234')

    def test_registry_survives_restart_and_never_changes_media(self):
        media=self.root/'original.png';media.write_bytes(b'original')
        private_access.register_job(self.root,'private-job')
        private_access.register_outputs(self.root,'private-job',{'status':{'completed':True},'outputs':{'1':{'images':[{'filename':'original.png','subfolder':'private'}]}}})
        self.assertTrue(private_access.private_job(self.root,'private-job'))
        self.assertTrue(private_access.private_file(self.root,'original.png','private'))
        self.assertFalse(private_access.pending_jobs(self.root))
        private_access.index_legacy(self.root,[{'filename':'legacy.mp4','type':'output'}])
        self.assertTrue(private_access.private_file(self.root,'legacy.mp4'))
        self.assertEqual(media.read_bytes(),b'original')
        before=(self.root/'private-access/ownership.json').read_bytes()
        with self.assertRaises(ValueError):private_access.index_legacy(self.root,[{'filename':'ok.png'},{'filename':'../bad'}])
        self.assertEqual((self.root/'private-access/ownership.json').read_bytes(),before)

    def test_http_blocks_private_history_preview_files_and_generation_before_engine(self):
        private_access.register_job(self.root,'private-job')
        private_access.register_outputs(self.root,'private-job',{'status':{'completed':True},'outputs':{'1':{'images':[{'filename':'private.png'}]}}})
        service=server.StudioHTTPServer(('127.0.0.1',0),server.Handler)
        worker=threading.Thread(target=service.serve_forever,daemon=True);worker.start()
        self.addCleanup(service.server_close);self.addCleanup(service.shutdown)
        def request(path,body=None,cookie=None,origin=None):
            connection=HTTPConnection('127.0.0.1',service.server_port,timeout=5)
            headers={'X-LocalAI-Media':'1','Content-Type':'application/json'}
            if cookie:headers['Cookie']=cookie
            if origin:headers['Origin']=origin
            connection.request('POST' if body is not None else 'GET',path,json.dumps(body) if body is not None else None,headers)
            response=connection.getresponse();raw=response.read();result=(response.status,dict(response.getheaders()),raw);connection.close();return result
        with patch.object(server,'DATA',self.root),patch.object(server,'history',return_value={'private-job':{}}) as history,patch.object(server,'_media_request_start') as generation,patch.object(server,'urlopen') as download:
            for path in ['/api/history/private-job','/api/studio/media/job?id=private-job','/api/studio/media/preview?id=private-job','/api/view?filename=private.png']:
                self.assertEqual(request(path)[0],403,path)
            self.assertEqual(request('/api/studio/media/start',{'workflow':'existing','prompt':'unchanged','settings':{'reserved_profile':'nsfw'}})[0],403)
            history.assert_not_called();generation.assert_not_called();download.assert_not_called()
            self.assertEqual(request('/api/private/unlock',{'code':'1234'},origin='https://evil.example')[0],403)
            status,headers,raw=request('/api/private/unlock',{'code':'1234'})
            self.assertEqual(status,200);self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('SameSite=Strict',headers['Set-Cookie'])
            cookie=headers['Set-Cookie'].split(';')[0]
            self.assertEqual(request('/api/history/private-job',cookie=cookie)[0],200)
            self.assertEqual(request('/api/private/index',{'files':[{'filename':'old.png'}]},cookie)[0],200)
            self.assertEqual(request('/api/view?filename=old.png')[0],403)
            request('/api/private/lock',{},cookie)
            self.assertEqual(request('/api/history/private-job',cookie=cookie)[0],403)
