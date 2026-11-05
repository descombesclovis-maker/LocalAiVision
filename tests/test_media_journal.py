import json
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
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

    def test_legacy_active_job_survives_more_than_1000_newer_requests(self):
        media_journal.reserve(self.root,self.body,self.record)
        media_journal.accepted(self.root,self.record['ticket'],'old-active-id')
        # Emulate the existing pre-index schema, including older accepted IDs.
        with closing(sqlite3.connect(self.root/'media-journal.sqlite')) as db, db:
            db.execute('DROP TABLE renders')
            db.execute('DROP TABLE journal_meta')
            for i in range(1001):
                ticket=f'prep-new-{i}'
                db.execute('INSERT INTO requests VALUES(?,?,?,?,?)',
                           (ticket,ticket,'digest','old-boot',json.dumps({'ticket':ticket,'state':'queued'})))
        pending=media_journal.monitorable(self.root)
        self.assertEqual([row['prompt_id'] for row in pending],['old-active-id'])
        media_journal.render_finished(self.root,'old-active-id','done')
        self.assertEqual(media_journal.monitorable(self.root),[])
        self.assertEqual(media_journal.load(self.root,self.record['ticket'])['render_states']['old-active-id'],'done')

    def test_concurrent_acceptance_and_completion_do_not_lose_receipts(self):
        media_journal.reserve(self.root,self.body,self.record)
        ids=[f'parallel-render-{i}' for i in range(20)]
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda pid:media_journal.accepted(self.root,self.record['ticket'],pid),ids))
            list(pool.map(lambda pid:media_journal.render_finished(self.root,pid,'done'),ids))
        # A stale worker snapshot must not resurrect finished renders.
        media_journal.save(self.root,{**self.record,'render_states':{pid:'queued' for pid in ids}})
        row=media_journal.load(self.root,self.record['ticket'])
        self.assertEqual(set(row['prompt_ids']),set(ids))
        self.assertEqual(row['render_states'],dict.fromkeys(ids,'done'))
        self.assertEqual(set(row['render_finished_at']),set(ids))
        self.assertEqual(media_journal.monitorable(self.root),[])

    def test_terminal_receipt_is_idempotent_even_if_history_arrives_late(self):
        media_journal.reserve(self.root,self.body,self.record)
        media_journal.accepted(self.root,self.record['ticket'],'cancelled-id')
        media_journal.render_finished(self.root,'cancelled-id','cancelled')
        before=media_journal.load(self.root,self.record['ticket'])
        media_journal.render_finished(self.root,'cancelled-id','error')
        self.assertEqual(media_journal.load(self.root,self.record['ticket']),before)

    def test_websocket_terminal_state_is_saved_before_disappearing(self):
        media_journal.reserve(self.root,self.body,self.record)
        media_journal.accepted(self.root,self.record['ticket'],'interrupted-id')
        from local_app import comfy_progress
        with patch.object(server,'DATA',self.root),patch.object(server,'_media_requests',{}), \
             patch.object(comfy_progress,'_jobs',{}),patch.object(comfy_progress,'_preview',{}), \
             patch.object(server,'comfy_get',return_value={'queue_running':[],'queue_pending':[]}):
            comfy_progress.register('interrupted-id')
            comfy_progress.mark('interrupted-id','cancelled')
            self.assertEqual(server.studio_media_jobs()['jobs'],[])
        self.assertEqual(media_journal.monitorable(self.root),[])
        self.assertEqual(media_journal.load(self.root,self.record['ticket'])['render_states']['interrupted-id'],'cancelled')

    def test_partial_history_is_not_reported_as_success(self):
        from local_app import comfy_progress
        media_journal.reserve(self.root,self.body,self.record)
        media_journal.accepted(self.root,self.record['ticket'],'partial-id')
        partial={'partial-id':{'status':{'completed':False,'status_str':'running'}}}
        with patch.object(server,'DATA',self.root),patch.object(server,'_media_requests',{}), \
             patch.object(comfy_progress,'_jobs',{}),patch.object(comfy_progress,'_preview',{}), \
             patch.object(server,'comfy_get',return_value=partial),patch.object(server,'_free_comfy_if_idle'):
            comfy_progress.register('partial-id')
            server.history('partial-id')
            self.assertEqual(comfy_progress.status('partial-id')['state'],'queued')
            self.assertEqual(len(server.studio_media_jobs()['jobs']),1)
        self.assertEqual(len(media_journal.monitorable(self.root)),1)
        self.assertEqual(server._confirmed_render_state({'status':{'completed':False,'status_str':'error'}}),'error')
        self.assertEqual(server._confirmed_render_state({'status':{'completed':False,'messages':[
            ['execution_interrupted',{'prompt_id':'partial-id'}]]}}),'cancelled')
