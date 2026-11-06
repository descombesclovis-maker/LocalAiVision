"""Retirement regressions: removal cannot expose or delete historical media."""
import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch
from local_app import retired_media, server


class RetiredMediaTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.index=self.root/'private-access'/'ownership.json';self.index.parent.mkdir()
        self.original=json.dumps({'schema':1,'jobs':{'private-job':{}},'files':{'output//private.png':{}}})
        self.index.write_text(self.original)

    def test_retired_wins_over_public_classification_without_touching_original(self):
        media=self.root/'original.png';media.write_bytes(b'original-personal-data')
        retired_media.classify(self.root,[{'filename':'public.png'},{'filename':'private.png'}],[],['public-job','private-job'])
        self.assertTrue(retired_media.allowed_file(self.root,'public.png'))
        self.assertFalse(retired_media.allowed_file(self.root,'private.png'))
        self.assertFalse(retired_media.allowed_file(self.root,'unknown.png'))
        self.assertTrue(retired_media.allowed_job(self.root,'public-job'))
        self.assertFalse(retired_media.allowed_job(self.root,'private-job'))
        self.assertEqual(self.index.read_text(),self.original)
        self.assertEqual(media.read_bytes(),b'original-personal-data')
        retired_media.classify(self.root,[],[{'filename':'public.png'}])
        retired_media.classify(self.root,[{'filename':'public.png'}],[])
        self.assertFalse(retired_media.allowed_file(self.root,'public.png'))

    def test_invalid_inventory_never_partially_grants_access(self):
        with self.assertRaises(ValueError):retired_media.classify(self.root,[{'filename':'good.png'},{'filename':'../bad.png'}],[])
        self.assertFalse(retired_media.allowed_file(self.root,'good.png'))
        self.index.write_text('{')
        with self.assertRaises(ValueError):retired_media.allowed_file(self.root,'good.png')

    def test_public_receipts_register_only_their_own_outputs(self):
        folder=self.root/'public-provenance';folder.mkdir();(folder/'public-job.json').write_text('{}')
        info={'outputs':{'1':{'images':[{'filename':'public.png'}],'videos':[{'filename':'private.png'}]}}}
        retired_media.register_outputs(self.root,'unknown-job',info)
        self.assertFalse(retired_media.allowed_file(self.root,'public.png'))
        retired_media.register_outputs(self.root,'public-job',info)
        self.assertTrue(retired_media.allowed_file(self.root,'public.png'))
        self.assertFalse(retired_media.allowed_file(self.root,'private.png'))

    def test_removed_routes_cannot_unlock_and_block_before_contacting_engine(self):
        service=server.StudioHTTPServer(('127.0.0.1',0),server.Handler)
        threading.Thread(target=service.serve_forever,daemon=True).start()
        self.addCleanup(service.server_close);self.addCleanup(service.shutdown)
        def request(path,body=None):
            connection=HTTPConnection('127.0.0.1',service.server_port,timeout=5)
            connection.request('POST' if body is not None else 'GET',path,json.dumps(body) if body is not None else None,{'Content-Type':'application/json','X-LocalAI-Media':'1','Cookie':'lva_private=old-token'})
            response=connection.getresponse();response.read();status=response.status;connection.close();return status
        with patch.object(server,'DATA',self.root),patch.object(server,'history') as history,patch.object(server,'_media_request_start') as generation,patch.object(server,'urlopen') as download:
            for path in ('/api/private/session','/nsfw','/private','/assets/studio-adult-workspace.css'):
                self.assertEqual(request(path),410,path)
            self.assertEqual(request('/api/private/unlock',{'code':'1234'}),410)
            for path in ('/api/history/private-job','/api/view?filename=private.png','/api/view?filename=unknown.png'):
                self.assertEqual(request(path),403,path)
            self.assertEqual(request('/api/studio/media/start',{'settings':{'reserved_profile':'nsfw'}}),410)
            history.assert_not_called();generation.assert_not_called();download.assert_not_called()
