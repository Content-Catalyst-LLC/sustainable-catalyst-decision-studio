from fastapi import HTTPException
import pytest
from app.scientific_evidence_review import readiness_from_figure

def test_machine_readiness_never_becomes_independent_review():
 figure={'spec_sha256':'a'*64,'spec':{'project_id':'synthetic','family':'evidence-gates','sources':[{'id':'synthetic'}],'limitations':['No observations'],'nodes':[{'id':'review','label':'Review','source_ids':['synthetic'],'blockers':[],'disposition':'positive'}]}}
 r=readiness_from_figure(figure,'synthetic','core-synthetic','artifact:sha256:'+'b'*64)
 assert r['gates'][0]['source_declared_disposition']=='positive'
 assert r['gates'][0]['independent_review_status']=='UNREVIEWED'
 assert r['net_removal_status']=='NOT_QUANTIFIED' and r['human_decision_recorded'] is False
 with pytest.raises(HTTPException):readiness_from_figure(figure,'other-project','core-synthetic','artifact:sha256:'+'b'*64)
