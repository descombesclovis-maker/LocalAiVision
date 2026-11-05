import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from local_app import media_journal, server


class MediaJournalTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.body={'workflow':'existing.json','prompt':'not stored in plaintext','request_key':'same-request-key'}
        self.record={'ticket':'prep-12345678','state':'preparing','private':False,'kind':'image'}

    def test_duplicate_reservation_does_not_relaunch_and_changed_body_is_rejected(self):
        row,created=media_journal.reserve(self.root,self.body,self.record);self.assertTrue(created)
        duplicate,created=media_journal.reserve(self.root,self.body,{**self.record,'ticket':'prep-other'})
        self.assertFalse(created);self.assertEqual(duplicate['ticket'],row['ticket'])
        with self.assertRaises(ValueError):media_journal.reserve(self.root,{**self.body,'prompt':'different'},self.record)
        self.assertNotIn(self.body['prompt'].encode(),(self.root/'media-journal.sqlite').read_bytes())

    def test_restart_reports_interruption_without_inference_restart(self):
        media_journal.reserve(self.root,self.body,self.record)
        with patch.object(media_journal,'BOOT','restarted'):
            row=media_journal.load(self.root,self.record['ticket'])
            self.assertEqual(row['state'],'error');self.assertTrue(row['interrupted'])
        media_journal.accepted(self.root,self.record['ticket'],'actual-comfy-id')
        with patch.object(media_journal,'BOOT','restarted'):
            row=media_journal.load(self.root,self.record['ticket'])
            self.assertEqual(row['state'],'queued');self.assertEqual(row['prompt_ids'],['actual-comfy-id'])

    def test_server_reserves_before_starting_one_worker(self):
        with patch.object(server,'DATA',self.root),patch.object(server,'_media_requests',{}),patch.object(server.threading,'Thread') as worker:
            first=server._media_request_start(self.body)
            second=server._media_request_start(self.body)
            self.assertEqual(first['ticket'],second['ticket'])
            self.assertTrue(second['already_submitted']);self.assertEqual(worker.call_count,1)
            self.assertIsNotNone(media_journal.load(self.root,first['ticket']))

    def test_accepted_render_is_monitorable_after_restart_and_completion_is_idempotent(self):
        media_journal.reserve(self.root,self.body,self.record)
        media_journal.accepted(self.root,self.record['ticket'],'actual-comfy-id')
        self.assertEqual(media_journal.monitorable(self.root)[0]['prompt_id'],'actual-comfy-id')
        # A concurrent cancellation status save must retain accepted IDs.
        media_journal.save(self.root,{**self.record,'cancel_requested':True})
        self.assertEqual(media_journal.load(self.root,self.record['ticket'])['prompt_ids'],['actual-comfy-id'])
        media_journal.render_finished(self.root,'actual-comfy-id','done')
        media_journal.render_finished(self.root,'actual-comfy-id','done')
        self.assertEqual(media_journal.monitorable(self.root),[])
