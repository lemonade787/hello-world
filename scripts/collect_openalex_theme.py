#!/usr/bin/env python3
from __future__ import annotations
import csv, json, os, random, sys, time
from pathlib import Path
import requests

API='https://api.openalex.org/works'
START='2000-01-01'; CUTOFF='2026-09-01'; MAX_PAGES=5
THEME_QUERIES={
 'K1':['machine learning spectrum sensing','deep learning spectrum sensing','radio frequency anomaly detection','spectrum situational awareness artificial intelligence','RF signal detection neural network'],
 'K2':['radar signal deinterleaving deep learning','specific emitter identification deep learning','radio frequency fingerprinting machine learning','radar emitter identification artificial intelligence','pulse sorting neural network radar'],
 'K3':['radar jamming recognition deep learning','jamming detection machine learning wireless','radar deception jamming recognition neural network','open set radio signal recognition','unknown jammer recognition deep learning'],
 'K4':['radar jamming decision reinforcement learning','electronic countermeasure reinforcement learning','adaptive jamming deep reinforcement learning','cognitive electronic warfare artificial intelligence','countermeasure waveform generation machine learning'],
 'K5':['anti-jamming communication reinforcement learning','GNSS jamming detection machine learning','GNSS spoofing detection deep learning','jammer resilient communication machine learning','frequency hopping anti-jamming deep reinforcement learning'],
 'K6':['cognitive radar reinforcement learning','adaptive radar waveform reinforcement learning','radar resource management artificial intelligence','radar beamforming reinforcement learning','frequency agile radar machine learning'],
 'K7':['multi-agent reinforcement learning electronic warfare','UAV swarm anti-jamming reinforcement learning','distributed spectrum sensing federated learning','cooperative jamming reinforcement learning','distributed radio frequency sensing machine learning'],
 'K8':['radio frequency foundation model','wireless foundation model IQ signal','self-supervised radio frequency signal learning','large language model radio frequency signal','multimodal electromagnetic perception model'],
 'K9':['electronic warfare digital twin artificial intelligence','radio frequency digital twin machine learning','hardware in the loop electronic warfare artificial intelligence','software defined radio machine learning jamming','real-time radio frequency emulation artificial intelligence'],
 'K10':['adversarial machine learning radio frequency','out of distribution radio signal recognition','uncertainty estimation radar deep learning','robust electronic warfare artificial intelligence','conformal prediction radio frequency signal'],
}

def get(s,params):
    wait=1.5
    for _ in range(8):
        r=s.get(API,params=params,timeout=90)
        if r.status_code==200:return r.json()
        if r.status_code in {429,500,502,503,504}:
            ra=r.headers.get('Retry-After')
            time.sleep(float(ra) if ra and ra.isdigit() else wait+random.random())
            wait=min(wait*1.8,30);continue
        raise RuntimeError(f'HTTP {r.status_code}: {r.text[:300]}')
    raise RuntimeError('retries exhausted')

def main():
    if len(sys.argv)<3: raise SystemExit('usage: collect_openalex_theme.py THEME OUTDIR')
    theme=sys.argv[1]; out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
    if theme not in THEME_QUERIES: raise SystemExit(f'unknown theme {theme}')
    email=os.getenv('OPENALEX_EMAIL','research@example.com')
    s=requests.Session();s.headers.update({'User-Agent':f'EW-AI-country-theme-matrix/1.0 (mailto:{email})','Accept':'application/json'})
    records={};audit=[]
    for q in THEME_QUERIES[theme]:
        cursor='*';retrieved=0;reported=None;pages=0;err='';truncated=False
        print('QUERY',theme,q,flush=True)
        try:
            for page in range(1,MAX_PAGES+1):
                payload=get(s,{'search':q,'filter':f'from_publication_date:{START},to_publication_date:{CUTOFF}','per-page':200,'cursor':cursor,'select':'id,doi,title,publication_year,publication_date,type,cited_by_count,authorships,abstract_inverted_index,primary_topic'})
                pages=page
                if reported is None:reported=payload.get('meta',{}).get('count')
                batch=payload.get('results') or []
                if not batch:break
                retrieved+=len(batch)
                for w in batch:
                    wid=w.get('id')
                    if not wid:continue
                    rec=records.setdefault(wid,w);rec.setdefault('_query_hits',[])
                    hit={'theme_id':theme,'query':q}
                    if hit not in rec['_query_hits']:rec['_query_hits'].append(hit)
                cursor=payload.get('meta',{}).get('next_cursor')
                if not cursor:break
                time.sleep(.04)
            if cursor and reported is not None and retrieved<reported:truncated=True
        except Exception as e:
            err=f'{type(e).__name__}: {e}'
            print('ERROR',err,file=sys.stderr,flush=True)
        audit.append({'theme_id':theme,'query':q,'reported_count':reported,'retrieved':retrieved,'pages':pages,'cap':MAX_PAGES*200,'truncated':truncated,'error':err})
    with (out/f'{theme}_openalex_raw.jsonl').open('w',encoding='utf-8') as f:
        for wid in sorted(records):f.write(json.dumps(records[wid],ensure_ascii=False)+'\n')
    with (out/f'{theme}_query_audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
    summary={'theme_id':theme,'window':{'start':START,'cutoff':CUTOFF},'query_count':len(audit),'max_per_query':MAX_PAGES*200,'unique_works':len(records),'failed_queries':sum(bool(x['error']) for x in audit),'truncated_queries':sum(bool(x['truncated']) for x in audit)}
    (out/f'{theme}_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 0 if records else 2
if __name__=='__main__':raise SystemExit(main())
