#!/usr/bin/env python3
"""Fit confidence on calibration companies and evaluate on held-out companies."""
import json, random, math
from collections import defaultdict
from pathlib import Path
from inference import candidates_for_company, naive_baseline
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; DIST=ROOT/'dist'/'data'; THRESHOLD=.85

def read_jsonl(path):
    with path.open(encoding='utf-8') as f:
        for line in f: yield json.loads(line)
def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')
def wilson(k,n):
    if not n:return [0,0]
    z=1.95996398454; p=k/n; den=1+z*z/n; center=(p+z*z/(2*n))/den
    delta=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [round(center-delta,4),round(center+delta,4)]
def fit_calibration(samples):
    # Pooled-adjacent-violators calibration on score groups. Beta(1,1)
    # smoothing prevents literal 0/100% confidence in finite data.
    levels=defaultdict(lambda:[0,0])
    for s,correct in samples: levels[s][0]+=int(correct);levels[s][1]+=1
    blocks=[]
    for score,(yes,n) in sorted(levels.items()):
        blocks.append({'lo':score,'hi':score,'yes':yes,'n':n})
        while len(blocks)>1 and (blocks[-2]['yes']+1)/(blocks[-2]['n']+2) > (blocks[-1]['yes']+1)/(blocks[-1]['n']+2):
            b=blocks.pop(); a=blocks.pop()
            blocks.append({'lo':a['lo'],'hi':b['hi'],'yes':a['yes']+b['yes'],'n':a['n']+b['n']})
    return [{**b,'probability':round((b['yes']+1)/(b['n']+2),4)} for b in blocks]
def confidence(score,blocks):
    # Nearest lower fitted breakpoint; extrapolate to extreme blocks conservatively.
    for b in blocks:
        if score <= b['hi']: return b['probability']
    return blocks[-1]['probability']
def metric(correct, emitted, eligible):
    return {'correct':correct,'emitted':emitted,'eligible':eligible,'precision':round(correct/emitted,4) if emitted else None,
            'coverage':round(emitted/eligible,4) if eligible else 0,'recall':round(correct/eligible,4) if eligible else 0,'precision_ci_95_wilson':wilson(correct,emitted)}
def main():
    companies=json.loads((DATA/'companies.json').read_text()); by_company=defaultdict(list)
    for p in read_jsonl(DATA/'people.jsonl'): by_company[p['company_id']].append(p)
    truth={r['person_id']:r['manager_id'] for r in read_jsonl(DATA/'truth.jsonl')}
    predictions={}; samples=[]
    for co in companies:
        preds=candidates_for_company(by_company[co['id']]);predictions[co['id']]=preds
        if co['split']=='calibration':
            samples.extend((x['raw_score'],x['candidate_id']==truth[pid]) for pid,x in preds.items() if x['candidate_id'] is not None and truth[pid] is not None)
    blocks=fit_calibration(samples)
    dump(DATA/'calibration.json',{'method':'Monotone pooled-adjacent-violators; beta(1,1) smoothing','fit_companies':100,'fit_candidates':len(samples),'blocks':blocks})
    eligible=emitted=correct=base_emitted=base_correct=missing_managers=0
    thresholds=[.50,.60,.70,.80,.85,.90,.95,.99]
    curve={str(t):{'correct':0,'emitted':0} for t in thresholds}
    bins=defaultdict(lambda:{'n':0,'correct':0,'sum_confidence':0})
    company_index=[]
    test_companies=[]
    error_missing_manager=0
    for co in companies:
        people=by_company[co['id']]; ids={p['id'] for p in people}; preds=predictions[co['id']]
        if co['split']=='test':
            local={'eligible':0,'emitted':0,'correct':0}
            base=naive_baseline(people)
            for p in people:
                pid=p['id']; true=truth[pid]
                if true is None: continue
                eligible+=1;local['eligible']+=1
                if true not in ids: missing_managers+=1
                if pid in base:
                    base_emitted+=1; base_correct+=(base[pid]==true)
                pred=preds[pid]
                if pred['candidate_id'] is not None:
                    prob=confidence(pred['raw_score'],blocks); is_correct=pred['candidate_id']==true
                    for t in thresholds:
                        if prob>=t: curve[str(t)]['emitted']+=1; curve[str(t)]['correct']+=is_correct
                    if prob>=THRESHOLD:
                        emitted+=1;correct+=is_correct
                        local['emitted']+=1;local['correct']+=is_correct
                        if not is_correct and true not in ids: error_missing_manager+=1
                        key=f'{int(prob*10)/10:.1f}–{min(1,(int(prob*10)+1)/10):.1f}'
                        bins[key]['n']+=1;bins[key]['correct']+=is_correct;bins[key]['sum_confidence']+=prob
            test_companies.append(local)
        app_people=[]
        for p in people:
            x=preds[p['id']]; cand=x['candidate_id']; prob=confidence(x['raw_score'],blocks) if cand else None
            accepted=bool(cand and prob>=THRESHOLD)
            if cand and not accepted:
                reason=f'Candidate evidence was below the {int(THRESHOLD*100)}% confidence threshold.'
                state='low_confidence'
            else: reason=x['reason'];state=x['kind']
            app_people.append({**p,'function':x['function'],'role':x['role'],'group':x['group'],
                               'manager_id':cand if accepted else None,'confidence':round(prob,4) if accepted else None,
                               'reason':reason,'state':state})
        clean={k:v for k,v in co.items() if k!='split'}
        dump(DIST/'companies'/f"{co['id']}.json",{'company':clean,'people':app_people})
        company_index.append(clean)
    comparison={k:metric(v['correct'],v['emitted'],eligible) for k,v in curve.items()}
    reliability=[{'range':k,'n':v['n'],'correct':v['correct'],'observed_precision':round(v['correct']/v['n'],4),'mean_confidence':round(v['sum_confidence']/v['n'],4)} for k,v in sorted(bins.items())]
    rng=random.Random(613)
    bootstrap=[]
    for _ in range(2000):
        sample=[rng.choice(test_companies) for _ in test_companies]
        denominator=sum(x['emitted'] for x in sample)
        bootstrap.append(sum(x['correct'] for x in sample)/denominator if denominator else 0)
    bootstrap.sort()
    test_metric=metric(correct,emitted,eligible)
    test_metric['precision_ci_95_company_bootstrap']=[round(bootstrap[49],4),round(bootstrap[1949],4)]
    report={'dataset':{'companies':len(companies),'employees':sum(c['employee_count'] for c in companies),'min_employees':min(c['employee_count'] for c in companies),'max_employees':max(c['employee_count'] for c in companies),
                       'calibration_companies':sum(c['split']=='calibration' for c in companies),'test_companies':sum(c['split']=='test' for c in companies)},
            'threshold':THRESHOLD,'test':test_metric,'baseline':metric(base_correct,base_emitted,eligible),'test_missing_managers':missing_managers,'wrong_edges_missing_true_manager':error_missing_manager,
            'threshold_curve':comparison,'reliability':reliability,'limitations':'Synthetic labels test recovery of this generator, not real-world reporting accuracy. Wilson intervals treat edges as independent and may be too narrow when employees share managers.'}
    dump(DATA/'evaluation.json',report);dump(DIST/'evaluation.json',report);dump(DIST/'index.json',company_index)
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
