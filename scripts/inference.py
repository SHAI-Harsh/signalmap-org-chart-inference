"""Conservative reporting-line candidates from *observed* roster fields only.

No ground-truth input is accepted by any function in this module.
"""
import re

# Ordered so the more specific terms win over broad terms.
GROUPS = [
 ('Security','Security Engineering',r'\bsecurity eng'), ('Security','Security Compliance',r'\bsecurity compliance'), ('Security','Information Security',r'\b(?:information|info) security'),
 ('Data','Data Engineering',r'\bdata eng'), ('Data','Analytics Engineering',r'\banalytics eng'), ('Data','Data Science',r'\bdata scien'),
 ('Engineering','Backend Engineering',r'\bbackend'), ('Engineering','Platform Engineering',r'\bplatform'), ('Engineering','Frontend Engineering',r'\bfront.?end'),
 ('Product','Product Management',r'\bproduct (?:management|manager)'), ('Product','Product Design',r'\bproduct design'), ('Product','Product Operations',r'\bproduct (?:operations|ops)'),
 ('Sales','Enterprise Sales',r'\b(?:enterprise sales|account executive)'), ('Sales','Business Development',r'\bbusiness development'), ('Sales','Sales Operations',r'\bsales (?:operations|ops)'),
 ('Marketing','Growth Marketing',r'\bgrowth market'), ('Marketing','Content Marketing',r'\bcontent market'), ('Marketing','Brand Marketing',r'\bbrand market'),
 ('Customer Success','Customer Success',r'\bcustomer success'), ('Customer Success','Customer Support',r'\bcustomer support'), ('Customer Success','Customer Onboarding',r'\bcustomer onboarding'),
 ('Finance','Financial Planning',r'\bfinancial planning'), ('Finance','Accounting',r'\baccounting|\baccountant'), ('Finance','Billing',r'\bbilling'),
 ('People','Recruiting',r'\brecruit'), ('People','People Operations',r'\bpeople (?:operations|ops)'), ('People','Human Resources',r'\bhuman resources|\bhr\b'),
 ('Operations','Business Operations',r'\bbusiness (?:operations|ops)'), ('Operations','Supply Chain',r'\bsupply chain'), ('Operations','Procurement',r'\bprocurement'),
 ('Legal','Legal Compliance',r'\blegal compliance'), ('Legal','Legal',r'\blegal'), ('Legal','Contracts',r'\bcontracts'),
]
HEAD_DOMAINS=[('Security',r'security|cyber'),('Data',r'\bdata\b|\banalytics\b'),('Engineering',r'eng(?:ineering)?\b'),('Product',r'\bproduct\b'),('Sales',r'\bsales\b'),('Marketing',r'\bmarketing\b'),('Customer Success',r'customer success'),('Finance',r'finance'),('People',r'people|\bhr\b'),('Operations',r'operations|\bops\b'),('Legal',r'legal|general counsel')]
EXEC_PATTERNS=[('CEO',r'\bceo\b|chief executive officer'),('CTO',r'\bcto\b|chief technology officer'),('CRO',r'\bcro\b|chief revenue officer'),('CFO',r'\bcfo\b|chief financial officer'),('COO',r'\bcoo\b|chief operating officer')]
EXEC_PARENT={'Engineering':('CTO',.97),'Data':('CTO',.60),'Security':('CTO',.61),'Product':('CTO',.70),'Sales':('CRO',.96),'Marketing':('CRO',.96),'Customer Success':('CRO',.96),'Finance':('CFO',.96),'People':('COO',.80),'Operations':('COO',.96),'Legal':('CEO',.96)}

def parse(person):
    t=(person.get('title') or '').strip().lower()
    result={'role':None,'rank':None,'function':None,'group':None,'executive':None}
    if not t: return result
    for name,pat in EXEC_PATTERNS:
        if re.search(pat,t):
            return {**result,'role':'executive','rank':6 if name=='CEO' else 5,'function':'Executive','executive':name}
    head=bool(re.search(r'\b(head|vp|vice president|director|dir)\b|general counsel',t))
    # Product Manager and Customer Success Manager are usually individual contributors.
    # A bare Team Lead is also too ambiguous to treat as a people manager.
    ambiguous=bool(re.search(r'\bteam lead\b',t)) or bool(re.search(r'^(?:(?:senior|sr\.?|staff|associate)\s+)?(?:product|customer success) manager$',t))
    managerial=not ambiguous and bool(re.search(r'\bmgr\b|\bmanager\b',t))
    group_info=next(((f,g) for f,g,pat in GROUPS if re.search(pat,t)),None)
    function=group_info[0] if group_info else next((f for f,pat in HEAD_DOMAINS if re.search(pat,t)),None)
    group=group_info[1] if group_info else None
    # A customer-success / people-operations head is not a team-level manager.
    if head: return {**result,'role':'head','rank':4,'function':function}
    if ambiguous and 'team lead' in t: return {**result,'role':'ambiguous','function':function,'group':group}
    if managerial and function and group: return {**result,'role':'manager','rank':3,'function':function,'group':group}
    if function and group: return {**result,'role':'individual contributor','rank':1,'function':function,'group':group}
    return {**result,'function':function}

def candidates_for_company(people):
    parsed={p['id']:parse(p) for p in people}
    by_exec={}
    for p in people:
        q=parsed[p['id']]
        if q['executive']: by_exec.setdefault((p['company_id'],q['executive']),[]).append(p)
    out={}
    for child in people:
        c=parsed[child['id']]
        base={'function':c['function'] or 'Unknown','role':c['role'] or 'Unknown','group':c['group']}
        if c['executive']=='CEO':
            out[child['id']]={**base,'candidate_id':None,'reason':'Top executive; no manager inferred.','kind':'root'}; continue
        if c['rank'] is None or not c['function']:
            out[child['id']]={**base,'candidate_id':None,'reason':'The title is missing, generic, or too ambiguous to place.','kind':'insufficient'}; continue
        candidates=[]
        if c['role']=='executive':
            for m in by_exec.get((child['company_id'],'CEO'),[]): candidates.append((.99,m,'Executive-to-CEO relationship'))
        elif c['role']=='head':
            target,score=EXEC_PARENT.get(c['function'],(None,0))
            for m in by_exec.get((child['company_id'],target),[]): candidates.append((score,m,f"{c['function']} leader to {target} role"))
        else:
            needed_rank=4 if c['role']=='manager' else 3
            for m in people:
                q=parsed[m['id']]
                if m['company_id']!=child['company_id'] or m['id']==child['id'] or q['rank']!=needed_rank or q['function']!=c['function']: continue
                if c['role']=='individual contributor' and (not c['group'] or c['group']!=q['group']): continue
                if c['role']=='manager':
                    score=.94
                    why=f"{c['function']} team manager to function leader"
                else:
                    score=.73
                    why=f"Same {c['group']} specialty; more senior manager title"
                    if child.get('location') and m.get('location'):
                        if child['location']==m['location']: score+=.12; why+='; matching location'
                        else: score-=.06; why+='; different locations'
                candidates.append((round(score,3),m,why))
        candidates.sort(key=lambda x:(-x[0],x[1]['id']))
        if not candidates:
            out[child['id']]={**base,'candidate_id':None,'reason':'No suitable senior manager was found in the observed roster.','kind':'no_candidate'}; continue
        if len(candidates)>1 and candidates[0][0]-candidates[1][0]<.03:
            out[child['id']]={**base,'candidate_id':None,'reason':'Several managers are equally plausible; the model abstained.','kind':'ambiguous'}; continue
        score,m,why=candidates[0]
        # Competing managers make even the best-matching location less certain.
        if len(candidates)>1: score=round(score-.04,3); why+='; another manager is plausible'
        out[child['id']]={**base,'candidate_id':m['id'],'raw_score':score,'reason':why,'kind':'candidate'}
    return out

def naive_baseline(people):
    """Deliberately weak baseline: same inferred function, nearest senior level, tie by id."""
    parsed={p['id']:parse(p) for p in people}; out={}
    for p in people:
        child=parsed[p['id']]; cr=child['rank']
        if cr is None or child['executive']=='CEO': continue
        opts=[]
        for m in people:
            q=parsed[m['id']]
            if m['company_id']!=p['company_id'] or q['rank'] is None or q['rank']<=cr: continue
            if q['function']==child['function'] or (q['executive']=='CEO' and cr==5): opts.append((q['rank'],m['id']))
        if opts: out[p['id']]=min(opts)[1]
    return out
