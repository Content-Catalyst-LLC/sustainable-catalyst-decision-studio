from app.energy_runtime_consumer import framework, consume, TARGET_KEY, CONSUMER_CONTRACT

def packet():
    sections=['identity', 'decision', 'economics', 'sustainability_indicators', 'global_context', 'uncertainty', 'provenance', 'review']
    payload={k: ({"study_id":"study:test","question":"Compare pathways"} if k=="identity" else ([{"source_ref":"source:test"}] if k=="provenance" else {} if k not in ("sustainability_indicators","uncertainty") else [])) for k in sections}
    return {"schema":"sc-energy-runtime-handoff/1.0","version":"1.2.0","packet":{"handoff_id":"es-test","source":{"product":"Library","subsystem":"Energy Systems Intelligence","version":"1.2.0"},"target":{"key":TARGET_KEY,"product":'Decision Studio',"consumer_contract":CONSUMER_CONTRACT},"contract_refs":["integrated-energy-study-contract"],"payload":payload}}

def test_framework_contract():
    x=framework(); assert x["ok"] is True; assert x["target_key"]=='decision-studio'; assert x["consumer_version"]=='2.3.0'; assert x["capabilities"]["automatic_execution"] is False; assert x["capabilities"]["persistence"] is False

def test_consume_builds_ephemeral_receipt():
    x=consume(packet()); assert x["accepted"] is True; assert x["execution"]["performed"] is False; assert x["persistence"]["performed"] is False; assert len(x["receipt_fingerprint"])==64
