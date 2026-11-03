"""Financial services never leave the process in these tests."""
import hashlib
import hmac
import json
import os
import tempfile
import time
from contextlib import closing
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from local_app import server, web_builder, web_crm as crm, web_sales_orders as orders
from local_app import web_sales_registrar as registrar, web_sales_delivery as delivery

SELLER={"name":"Atelier exemple","siret":"53784237900027","address":"Adresse de recette",
        "legal_form":"EI","vat_mode":"franchise","payment_details":"Virement",
        "late_penalty_rate":"Taux contractuel de recette"}
CLIENT={"name":"Client démo","address":"Adresse de recette","email":"client@example.org","type":"business"}


class SalesTests(TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.crm=self.root/"crm"
        self.store=web_builder.LocalAiWebStore(self.root/"projects",None)
        for obj,key,value in [(server,"_web_store",lambda:self.store),(server,"LOCALAIWEB_DATA",self.root)]:
            context=patch.object(obj,key,value);context.start();self.addCleanup(context.stop)
        self.business={"name":"Atelier Démo","category":"fleuriste","source":"Données de recette","id":"fixture-55","phone":"01 23 45 67 89","city":"Lyon"}
        self.pid=self.store.create_business_project(self.business)["project"]["id"]
        crm.attach_business_project(self.crm,self.store,self.pid,self.business)
        context=patch.dict(os.environ,{"LOCALAI_SALES_MODE":"test","DROPBOX_SIGN_API_KEY":"dummy",
            "STRIPE_SECRET_KEY":"sk_test_dummy","STRIPE_WEBHOOK_SECRET":"test-secret",
            "LOCALAI_CHECKOUT_RETURN_URL":"https://example.org/retour"})
        context.start();self.addCleanup(context.stop)

    def build(self):
        self.store.write_files(self.pid,{"index.html":"<!doctype html><html lang='fr'><main><h1>Atelier</h1><p>Une vraie page locale de démonstration pour les tests du dossier de vente.</p></main></html>"})
        server._web_persist_generation(self.pid,{"state":"done"})

    def quote(self):
        self.build()
        return crm.create_quote(self.crm,self.store,{"project_id":self.pid,"confirmed":True,
            "seller":SELLER,"customer":CLIENT,"items":["landing"],"discount_pct":20,
            "scope":"Deux révisions","recurring":"Hébergement non inclus."})["quote_number"]

    def test_completion_and_restart_and_opposition(self):
        self.assertFalse(server._sales_dossier(self.pid)["ready"])
        self.build()
        def change(action,**body):
            return server._sales_dossier(self.pid,{"action":action,**body})
        self.assertEqual(change("prepare")["pages"],["index.html"])
        with self.assertRaises(ValueError):change("call",outcome="répondu")
        self.assertTrue(change("verify_phone",confirmed=True)["call_allowed"])
        self.assertEqual(change("call",outcome="rappel",due="2099-01-01")["events"][-1]["due"],"2099-01-01")
        self.assertFalse(change("oppose")["call_allowed"])
        self.assertTrue(server._sales_dossier(self.pid)["opposed"])
        self.assertFalse(crm.snapshot(self.crm,self.store)["followups_upcoming"])
        with self.assertRaises(ValueError):change("call",outcome="répondu")
        with self.assertRaises(ValueError):change("verify_phone",confirmed=True)

    def test_quote_and_provider_identity(self):
        number=self.quote()
        self.assertTrue(crm.quote_file(self.crm,number).read_bytes().startswith(b"%PDF"))
        self.assertEqual(orders._quote(self.crm,self.pid,number)["total_eur"],"720.00")
        ref="a"*40
        with patch.object(orders,"_request",return_value={"signature_request":{"signature_request_id":ref}}) as send:
            self.assertEqual(orders.signature_request(self.crm,self.pid,number),ref)
            orders.signature_request(self.crm,self.pid,number)
            self.assertEqual(send.call_count,1)
        record={"signature_request_id":ref,"is_complete":True,"has_error":False,"is_declined":False,
            "metadata":{"sales_mode":"test","quote_number":number,"quote_sha256":hashlib.sha256(crm.quote_file(self.crm,number).read_bytes()).hexdigest()},
            "signatures":[{"status_code":"signed","signer_email_address":"other@example.org","signed_at":int(time.time())}]}
        with patch.object(orders,"_request",return_value={"signature_request":record}):
            with self.assertRaises(ValueError):orders.verify_acceptance(self.crm,self.pid,number)
            record["signatures"][0]["signer_email_address"]=CLIENT["email"]
            self.assertEqual(orders.verify_acceptance(self.crm,self.pid,number)[0]["payment"],"unpaid")
        with patch.object(orders,"_request",return_value={"id":"cs_test_55","client_reference_id":number,"metadata":{"quote":number},"url":"https://checkout.stripe.com/example",
              "amount_total":72000,"currency":"eur","livemode":False}) as checkout:
            self.assertEqual(orders.checkout(self.crm,self.pid,number)[0]["payment"],"pending")
            orders.checkout(self.crm,self.pid,number)
            self.assertEqual(checkout.call_count,1)

    def event(self, kind, ident, body):
        raw=json.dumps({"type":kind,"id":ident,"livemode":False,"data":{"object":body}}).encode()
        ts=str(int(time.time()))
        sig=hmac.new(b"test-secret",ts.encode()+b"."+raw,hashlib.sha256).hexdigest()
        return raw,"t="+ts+",v1="+sig

    def test_webhook_duplicate_amount_and_reordered_refund(self):
        number=self.quote()
        with closing(orders._db(self.crm)) as db,db:
            db.execute("INSERT INTO orders(quote,project,amount,signature,mode,accepted,session,payment) VALUES(?,?,72000,'sig','test',0,'cs_test_55','pending')",(number,self.pid))
        obj={"id":"cs_test_55","metadata":{"quote":number},"currency":"eur","amount_total":72000,
             "client_reference_id":number,"payment_status":"paid","payment_intent":"pi_test"}
        raw,sig=self.event("checkout.session.completed","evt_1",obj)
        with self.assertRaises(ValueError):orders.webhook(self.crm,raw,sig+"0")
        with self.assertRaises(ValueError):orders.webhook(self.crm,*self.event("checkout.session.completed","evt_bad",dict(obj,amount_total=2)))
        orders.webhook(self.crm,raw,sig);orders.webhook(self.crm,raw,sig)
        self.assertEqual(orders.status(self.crm,self.pid)[0]["payment"],"paid")
        refund=dict(obj,id="ch_55",amount=72000,amount_refunded=72000)
        orders.webhook(self.crm,*self.event("charge.refunded","evt_2",refund))
        orders.webhook(self.crm,*self.event("checkout.session.completed","evt_late",obj))
        self.assertEqual(orders.status(self.crm,self.pid)[0]["payment"],"refunded")
        with closing(orders._db(self.crm)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events").fetchone()[0],3)

    def test_domain_refuses_unpaid_or_changed_price_and_never_repeats_uncertain_order(self):
        number=self.quote()
        directory=self.root/"mandates";directory.mkdir()
        link=self.store.project_dir(self.pid)/"site"/".vercel";link.mkdir()
        (link/"project.json").write_text(json.dumps({"orgId":"team_55","projectId":"prj_55"}))
        m={"domain":"example.org","price_usd":12,"all_in_usd":12,"renewal_usd":15,"years":1,
           "expires_at":time.time()+3600,"billing_verified":True,"billing_evidence":"test","customer_name":CLIENT["name"],
           "project":self.pid,"quote":number,"autoRenew":False,"holder_consented":True,
           "teamId":"team_55","projectId":"prj_55","contactInformation":{k:"test" for k in
           ("firstName","lastName","phone","address1","city","state","zip","country")}}
        m["contactInformation"]["email"]=CLIENT["email"]
        (directory/(self.pid+".json")).write_text(json.dumps(m))
        with patch.dict(os.environ,{"LOCALAI_SALES_MODE":"live","LOCALAI_REGISTRAR_MANDATES":str(directory),"LOCALAI_REGISTRAR_TOKEN":"dummy"}), patch.object(registrar,"registrar_search") as lookup, patch.object(registrar,"_provider",side_effect=TimeoutError) as provider:
            with self.assertRaises(ValueError):registrar.prepare(self.crm,self.store,self.pid,number)
            with closing(orders._db(self.crm)) as db,db:
                db.execute("INSERT INTO orders(quote,project,amount,signature,mode,accepted,payment) VALUES(?,?,72000,'sig','live',0,'paid')",(number,self.pid))
            lookup.return_value={"available":False}
            with self.assertRaises(ValueError):registrar.prepare(self.crm,self.store,self.pid,number)
            lookup.return_value={"available":True,"price":14,"renewal":15,"years":1}
            with self.assertRaises(ValueError):registrar.prepare(self.crm,self.store,self.pid,number)
            lookup.return_value["price"]=12
            offer,_=registrar.prepare(self.crm,self.store,self.pid,number)
            with self.assertRaises(ValueError):registrar.buy(self.crm,self.store,self.pid,number,"old")
            with self.assertRaises(TimeoutError):registrar.buy(self.crm,self.store,self.pid,number,offer["approval"])
            with self.assertRaises(ValueError):registrar.buy(self.crm,self.store,self.pid,number,offer["approval"])
            self.assertEqual(provider.call_count,1)
            self.assertEqual(registrar.details(self.crm,self.pid)["state"],"uncertain")

    def test_delivery_refuses_local_address(self):
        with patch("socket.getaddrinfo",return_value=[(2,1,6,"",("127.0.0.1",443))]):
            with self.assertRaises(ValueError):delivery._https("example.org")

    def test_signature_pending_declined_and_expiry_persist_without_acceptance(self):
        number=self.quote()
        ref="b"*40
        with patch.object(orders,"_request",return_value={"signature_request":{"signature_request_id":ref}}):
            orders.signature_request(self.crm,self.pid,number)
        record={"signature_request_id":ref,"is_complete":False,"is_declined":False,"has_error":False,
            "metadata":{"sales_mode":"test","quote_number":number,
                        "quote_sha256":hashlib.sha256(crm.quote_file(self.crm,number).read_bytes()).hexdigest()},
            "signatures":[{"status_code":"awaiting_signature","signer_email_address":CLIENT["email"]}]}
        with patch.object(orders,"_request",return_value={"signature_request":record}):
            self.assertEqual(orders.verify_acceptance(self.crm,self.pid,number),[])
            orders.verify_acceptance(self.crm,self.pid,number)
            record["is_declined"]=True
            self.assertEqual(orders.verify_acceptance(self.crm,self.pid,number),[])
        saved=orders.signatures(self.crm,self.pid)[0]
        self.assertEqual(saved["state"],"declined")
        self.assertEqual([h["state"] for h in saved["history"]],["sent","pending","declined"])
        self.assertEqual(server._sales_dossier(self.pid)["signatures"],[saved])
        # Provider timeout must leave the last verified state, not invent success.
        with patch.object(orders,"_request",side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):orders.verify_acceptance(self.crm,self.pid,number)
        self.assertEqual(orders.signatures(self.crm,self.pid)[0]["state"],"declined")
        record["is_declined"]=False
        quote=dict(orders._quote(self.crm,self.pid,number),valid_until="2000-01-01")
        with patch.object(orders,"_quote",return_value=quote),patch.object(orders,"_request",return_value={"signature_request":record}):
            self.assertEqual(orders.verify_acceptance(self.crm,self.pid,number),[])
        self.assertEqual(orders.signatures(self.crm,self.pid)[0]["state"],"quote_expired")
        with self.assertRaises(ValueError):orders.checkout(self.crm,self.pid,number)

    def test_signature_wrong_document_never_changes_history_or_accepts(self):
        number=self.quote()
        ref="c"*40
        with patch.object(orders,"_request",return_value={"signature_request":{"signature_request_id":ref}}):
            orders.signature_request(self.crm,self.pid,number)
        record={"signature_request_id":ref,"is_complete":True,
            "metadata":{"sales_mode":"test","quote_number":number,"quote_sha256":"wrong"},
            "signatures":[{"status_code":"signed","signer_email_address":CLIENT["email"],"signed_at":int(time.time())}]}
        with patch.object(orders,"_request",return_value={"signature_request":record}):
            with self.assertRaises(ValueError):orders.verify_acceptance(self.crm,self.pid,number)
        self.assertEqual(orders.status(self.crm,self.pid),[])
        self.assertEqual(orders.signatures(self.crm,self.pid)[0]["state"],"sent")

    def test_failure_cannot_grant_paid_and_refund_bounds_are_atomic(self):
        number=self.quote()
        with closing(orders._db(self.crm)) as db,db:
            db.execute("INSERT INTO orders(quote,project,amount,signature,mode,accepted,session,payment) VALUES(?,?,72000,'sig','test',0,'cs_test_55','pending')",(number,self.pid))
        obj={"id":"cs_test_55","metadata":{"quote":number},"currency":"eur","amount_total":72000,
             "client_reference_id":number,"payment_status":"paid","payment_intent":"pi_test"}
        orders.webhook(self.crm,*self.event("checkout.session.async_payment_failed","evt_failed",obj))
        self.assertEqual(orders.status(self.crm,self.pid)[0]["payment"],"failed")
        orders.webhook(self.crm,*self.event("checkout.session.completed","evt_paid",obj))
        refund=dict(obj,id="ch_55",amount=72000,amount_refunded=1000)
        orders.webhook(self.crm,*self.event("charge.refunded","evt_partial",refund))
        for bad in (-1,72001,True,1.5,"1000"):
            with self.assertRaises(ValueError):
                orders.webhook(self.crm,*self.event("charge.refunded","evt_bad_refund",dict(refund,amount_refunded=bad)))
        # Smaller out-of-order refund cannot reduce the known cumulative refund.
        orders.webhook(self.crm,*self.event("charge.refunded","evt_older",dict(refund,amount_refunded=500)))
        with self.assertRaises(ValueError):
            orders.webhook(self.crm,*self.event("checkout.session.completed","evt_wrong_intent",dict(obj,payment_intent="pi_other")))
        self.assertEqual(orders.status(self.crm,self.pid)[0]["refunded"],1000)
        self.assertEqual(orders.status(self.crm,self.pid)[0]["payment"],"partially_refunded")
        with closing(orders._db(self.crm)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events").fetchone()[0],4)

    def test_api_refuses_other_ports_schemes_and_preview_hosts(self):
        from http.client import HTTPConnection
        import threading
        from http.server import ThreadingHTTPServer
        http=ThreadingHTTPServer(("127.0.0.1",0),server.Handler)
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        try:
            host="127.0.0.1:"+str(http.server_port)
            for origin in ("http://127.0.0.1:1","https://"+host,"null","http://preview-"+self.pid+".localhost:"+str(http.server_port)):
                conn=HTTPConnection("127.0.0.1",http.server_port)
                try:
                    conn.request("GET","/api/web/crm/overview",headers={"Host":host,"Origin":origin})
                    response=conn.getresponse();self.assertEqual(response.status,403);response.read()
                finally:conn.close()
        finally:http.shutdown();http.server_close();thread.join()

    def test_handover_requires_payment_of_published_quote_and_refund_stays_visible(self):
        from local_app import web_sales_pipeline
        published=self.quote()
        other=self.quote()
        revision=server._sales_dossier(self.pid)["revision"]
        server._sales_dossier(self.pid,{"action":"prepare"})
        web_sales_pipeline.record_release(self.crm,self.pid,revision,published,"https://example.org")
        with closing(orders._db(self.crm)) as db,db:
            db.execute("INSERT INTO orders(quote,project,amount,signature,mode,accepted,payment) VALUES(?,?,72000,'published','live',0,'refunded')",(published,self.pid))
            db.execute("INSERT INTO orders(quote,project,amount,signature,mode,accepted,payment) VALUES(?,?,72000,'other','live',1,'paid')",(other,self.pid))
        with patch.dict(os.environ,{"LOCALAI_SALES_MODE":"live"}),patch.object(self.store,"preflight",return_value={"ok":True}),patch("local_app.integrations_cli.validate_site",return_value={"ok":True}),patch.object(delivery,"verify") as verify:
            self.assertEqual(server._sales_dossier(self.pid)["stage"],"refunded")
            with self.assertRaisesRegex(ValueError,"devis de cette publication"):
                server._sales_dossier(self.pid,{"action":"handover","confirmed":True})
            verify.assert_not_called()

    def test_default_domain_mandate_survives_configuration_reload(self):
        number=self.quote()
        link=self.store.project_dir(self.pid)/"site"/".vercel";link.mkdir()
        (link/"project.json").write_text(json.dumps({"orgId":"team_55","projectId":"prj_55"}))
        with closing(orders._db(self.crm)) as db,db:
            db.execute("INSERT INTO orders(quote,project,amount,signature,mode,accepted,payment) VALUES(?,?,72000,'sig','live',0,'paid')",(number,self.pid))
        contact={k:"test" for k in ("firstName","lastName","phone","address1","city","state","zip","country")}
        contact["email"]=CLIENT["email"]
        body={"domain":"example.org","all_in_usd":12,"holder_consented":True,"billing_verified":True,
              "billing_evidence":"Fixture, no purchase", "contactInformation":contact}
        with patch.dict(os.environ,{"LOCALAI_SALES_MODE":"live","LOCALAI_REGISTRAR_MANDATES":""}),patch.dict(orders._private_config,{},clear=True),patch.object(registrar,"registrar_search",return_value={"domain":"example.org","available":True,"price":12,"renewal":15,"years":1}),patch.object(registrar,"_provider") as buy:
            offer=registrar.save_mandate(self.crm,self.store,self.pid,number,body)
            self.assertTrue((self.crm/"mandates"/(self.pid+".json")).is_file())
            self.assertNotIn("LOCALAI_REGISTRAR_MANDATES",orders._private_config)
            # Only the persisted private file is needed after process restart.
            recovered,_=registrar.prepare(self.crm,self.store,self.pid,number)
            self.assertEqual(offer["approval"],recovered["approval"])
            buy.assert_not_called()

    def test_two_florists_have_distinct_evidence_and_never_inherit_each_others_facts(self):
        self.build()
        self.store.write_files(self.pid,{"index.html":"<!doctype html><html><title>Atelier</title><main><h1>Fleurs de saison</h1><p>Une maquette locale</p><a href='bouquets.html'>Voir les bouquets</a></main></html>",
            "bouquets.html":"<!doctype html><h1>Bouquets de saison</h1>"})
        change={"action":"confirm_fact","category":"priorité","value":"Montrer les compositions de mariage",
                "source":"Client au téléphone","day":time.strftime("%Y-%m-%d"),"confirmed":True}
        a=server._sales_dossier(self.pid,change)
        other=dict(self.business,name="Fleuriste B",category="fleuriste",city="Lille",id="demo-b",phone="")
        second=self.store.create_business_project(other)["project"]["id"]
        self.store.write_files(second,{"index.html":"<!doctype html><html><body><h1>Abonnements floraux</h1><p>Composition florale hebdomadaire en démonstration privée.</p></body></html>"})
        server._web_persist_generation(second,{"state":"done"})
        b=server._sales_dossier(second)
        first=str(a["call_sheet"]);later=str(b["call_sheet"])
        self.assertIn("Voir les bouquets",first)
        self.assertIn("bouquets.html",first)
        self.assertIn("Client au téléphone",first)
        self.assertNotIn("compositions de mariage",later)
        self.assertIn("Abonnements floraux",later)
        self.assertIn("Lille",later);self.assertNotIn("Lyon",later)
        self.assertIn("Site non renseigné",later)
        stale=server._sales_dossier(self.pid,dict(change,day="2020-01-01"))
        self.assertIn("Revalider ce point",str(stale["call_sheet"]))
        self.assertNotIn("Vous aviez indiqué le 2020",str(stale["call_sheet"]))
        removed=server._sales_dossier(self.pid,{"action":"withdraw_fact","category":"priorité"})
        self.assertNotIn("compositions de mariage",str(removed["call_sheet"]))
        self.assertEqual(server._sales_dossier(self.pid,{"action":"oppose"})["call_sheet"],[])

    def test_register_ambiguity_never_becomes_a_verified_fact(self):
        self.build()
        with patch("local_app.web_business_registry.professional_profile",return_value={"matched":False,"message":"Homonymes"}):
            d=server._sales_dossier(self.pid,{"action":"refresh_registry"})
        self.assertFalse(d["registry"]["matched"])
        self.assertIn("Identité juridique non rapprochée",str(d["call_sheet"]))
        with self.assertRaises(ValueError):server._sales_dossier(self.pid,{"action":"registry_result","registry":{"matched":True}})

    def test_review_bound_to_version_and_unsigned_copy_cannot_be_injected(self):
        self.build()
        d=server._sales_dossier(self.pid)
        checks=[True]*8
        self.assertEqual(server._sales_dossier(self.pid,{"action":"review","checks":checks,"revision":d["revision"]})["checks"],checks)
        self.store.write_files(self.pid,{"styles.css":"body{color:blue}"})
        self.assertEqual(server._sales_dossier(self.pid)["checks"],[])
        with self.assertRaises(ValueError):
            server._sales_dossier(self.pid,{"action":"review","checks":checks,"revision":d["revision"]})
        with self.assertRaises(ValueError):
            server._sales_dossier(self.pid,{"action":"save_pitch","pitch":"Unverified"})

    def test_db_migrations_require_same_sql_and_same_linked_ref(self):
        folder=self.store.project_dir(self.pid)/"site"/"supabase"
        (folder/"migrations").mkdir(parents=True);(folder/".temp").mkdir()
        ref="a"*20
        (folder/".temp"/"project-ref").write_text(ref)
        (folder/"config.toml").write_text('project_id = "test"')
        migration=folder/"migrations"/"20260101_test.sql";migration.write_text("-- fixture")
        with patch("local_app.integrations_cli._supabase_cmd",return_value=["supabase"]),patch("local_app.integrations_cli._run") as command:
            command.return_value.returncode=0
            plan=delivery.database_change(self.store,self.pid,ref)
            self.assertIn("--dry-run",command.call_args.args[0])
            migration.write_text("-- changed")
            with self.assertRaises(ValueError):delivery.database_change(self.store,self.pid,ref,plan["digest"])
            with self.assertRaises(ValueError):delivery.database_change(self.store,self.pid,"b"*20)
            self.assertEqual(command.call_count,1)


    def test_public_heading_changes_first_spoken_sentence_with_traceable_source(self):
        from local_app import web_sales_source
        from email.message import Message
        self.build()
        meta=self.store.meta(self.pid)
        meta["business"]["website"]="https://atelier-demo.example/"
        self.store.write_meta(self.pid,meta)
        headers=Message();headers["Content-Type"]="text/html"
        page="<input hidden><header hidden><h2>Hidden topic</h2></header><h1>Atelier Démo</h1><h2>Fleurs pour les entreprises</h2><script>never quoted</script><h2>Abonnements floraux</h2>"
        with patch.object(web_sales_source,"_read",side_effect=[(404,headers,b""),(200,headers,page.encode())]):
            d=server._sales_dossier(self.pid,{"action":"scan_website","confirmed":True})
        self.assertNotIn("Hidden topic",d["public_page"]["headings"])
        with self.assertRaises(ValueError):
            server._sales_dossier(self.pid,{"action":"select_angle","heading":"Offre inventée","confirmed":True})
        def first(heading):
            d=server._sales_dossier(self.pid,{"action":"select_angle","heading":heading,"confirmed":True})
            self.assertIn(d["public_page"]["url"],str(d["call_sheet"][0]))
            return " ".join(d["call_sheet"][1][1])
        self.assertIn("montrer des exemples",first("Fleurs pour les entreprises"))
        self.assertIn("les tarifs ou comment ça fonctionne",first("Abonnements floraux"))
        manual=server._sales_dossier(self.pid,{"action":"clear_angle"})
        self.assertIn("Est-ce toujours votre site",manual["call_sheet"][1][1][0])
        with self.assertRaises(ValueError):server._sales_dossier(self.pid,{"action":"website_observed","observation":{}})

    def test_official_page_requires_public_origin_and_robots_permission(self):
        from local_app import web_sales_source
        with patch("socket.getaddrinfo",return_value=[(2,1,6,"",("127.0.0.1",443))]):
            with self.assertRaises(ValueError):web_sales_source.scan("https://atelier.example")
        with patch.object(web_sales_source,"_read",return_value=(200,{},b"User-agent: *\nDisallow: /")) as read:
            with self.assertRaises(ValueError):web_sales_source.scan("https://atelier.example")
            self.assertEqual(read.call_count,1)
        with patch.object(web_sales_source,"_read",side_effect=[(404,{},b""),(302,{"Location":"https://other.example/"},b"")]) as read:
            with self.assertRaises(ValueError):web_sales_source.scan("https://atelier.example")
            self.assertEqual(read.call_count,2)
