#!/usr/bin/env python3
"""Deterministic, independently generated companies with private reporting truth."""
import json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data'
SEED = 73129
N_COMPANIES = 500
FIRST = 'Aarav Ada Aisha Alex Amara Amelia Ananya Andre Anika Arjun Ava Ben Cameron Carlos Carmen Chen Chloe Daniel David Deepa Diego Elena Ethan Fatima Grace Hannah Haruto Henry Ibrahim Imani Isabella Ivan Jade James Jay Jia Jordan Julia Kai Karan Kavya Kim Leila Liam Lina Lucas Maya Mei Michael Miguel Mina Mohammed Naomi Neha Noah Nora Oliver Omar Priya Rafael Riya Rosa Ryan Sam Sara Sarah Sophia Tanvi Theo Wei William Yara Zara Zoe'.split()
LAST = 'Adams Ali Alvarez Anderson Baker Banerjee Brown Campbell Carter Chen Clark Cohen Cooper Davis Diaz Evans Fischer Garcia Gupta Hall Hernandez Hill Howard Hughes Ibrahim Jackson Jain Johnson Jones Kapoor Khan Kim Kumar Lee Lewis Li Liu Martin Martinez Mehta Miller Mitchell Moore Morgan Murphy Nguyen Patel Perez Phillips Robinson Rodriguez Ross Shah Sharma Singh Smith Taylor Thomas Thompson Torres Turner Walker Wang White Williams Wilson Wu Young Zhang'.split()
PREFIXES = ['Northstar','Evergreen','Summit','Brightline','Meridian','Bluebird','Copper','Juniper','Atlas','Cedar','Lattice','Beacon','Willow','Orion','Silver','Harbor','Acorn','Nimbus','Redwood','Clearwater','Stonebridge','Mosaic','Pioneer','Cobalt','Aster']
SUFFIXES = ['Labs','Health','Systems','Financial','Works','Collective','Cloud','Logistics','Analytics','Networks','Commerce','Energy','Foods','Technologies','Partners','Industries','Software','Ventures','Dynamics','Solutions']
INDUSTRIES = ['Software & SaaS','Healthcare','Financial services','Retail & e-commerce','Manufacturing','Logistics','Clean energy','Media','Professional services','Consumer products']
SUFFIX_INDUSTRY = {'Health':'Healthcare','Financial':'Financial services','Cloud':'Software & SaaS','Logistics':'Logistics','Commerce':'Retail & e-commerce','Energy':'Clean energy','Foods':'Consumer products','Software':'Software & SaaS'}
LOCATIONS = ['New York, NY','Austin, TX','San Francisco, CA','Chicago, IL','Seattle, WA','Boston, MA','Bengaluru, India','London, UK','Remote']

# Visible titles vary, while teams and reporting structure remain private.
DEPTS = {
 'Engineering': {'heads':['VP Engineering','VP of Engineering','Head of Engineering','Director of Engineering'], 'groups':[('Backend Engineering','Backend Engineer'),('Platform Engineering','Platform Engineer'),('Frontend Engineering','Frontend Engineer')]},
 'Data': {'heads':['Head of Data','VP, Data','Director of Data','VP Data & Analytics'], 'groups':[('Data Engineering','Data Engineer'),('Analytics Engineering','Analytics Engineer'),('Data Science','Data Scientist')]},
 'Security': {'heads':['Head of Security','VP, Information Security','Director of Security','Head of Cybersecurity'], 'groups':[('Security Engineering','Security Engineer'),('Information Security','Information Security Analyst'),('Security Compliance','Security Compliance Analyst')]},
 'Product': {'heads':['VP Product','Head of Product','Director, Product','VP of Product'], 'groups':[('Product Management','Product Manager'),('Product Design','Product Designer'),('Product Operations','Product Operations Specialist')]},
 'Sales': {'heads':['VP Sales','Head of Sales','Director of Sales','VP, Sales'], 'groups':[('Enterprise Sales','Account Executive'),('Business Development','Business Development Representative'),('Sales Operations','Sales Operations Analyst')]},
 'Marketing': {'heads':['VP Marketing','Head of Marketing','Director of Marketing','VP, Marketing'], 'groups':[('Growth Marketing','Growth Marketing Specialist'),('Content Marketing','Content Marketer'),('Brand Marketing','Brand Marketing Specialist')]},
 'Customer Success': {'heads':['VP Customer Success','Head of Customer Success','Director of Customer Success'], 'groups':[('Customer Success','Customer Success Manager'),('Customer Support','Customer Support Specialist'),('Customer Onboarding','Customer Onboarding Specialist')]},
 'Finance': {'heads':['VP Finance','Head of Finance','Director of Finance'], 'groups':[('Financial Planning','Financial Planning Analyst'),('Accounting','Accountant'),('Billing','Billing Specialist')]},
 'People': {'heads':['VP People','Head of People','Director of People Operations','Head of HR'], 'groups':[('Recruiting','Recruiter'),('People Operations','People Operations Specialist'),('Human Resources','HR Generalist')]},
 'Operations': {'heads':['VP Operations','Head of Operations','Director of Operations'], 'groups':[('Business Operations','Business Operations Analyst'),('Supply Chain','Supply Chain Analyst'),('Procurement','Procurement Specialist')]},
 'Legal': {'heads':['General Counsel','Head of Legal','Director of Legal'], 'groups':[('Legal','Legal Counsel'),('Legal Compliance','Legal Compliance Analyst'),('Contracts','Contracts Specialist')]},
}
EXEC_TITLES = {'CEO':['CEO','Chief Executive Officer','Founder & CEO'], 'CTO':['CTO','Chief Technology Officer'], 'CRO':['CRO','Chief Revenue Officer'], 'CFO':['CFO','Chief Financial Officer'], 'COO':['COO','Chief Operating Officer']}

def dump_json(path, value):
    path.write_text(json.dumps(value, separators=(',', ':'), ensure_ascii=False) + '\n', encoding='utf-8')

def main():
    OUT.mkdir(exist_ok=True)
    all_companies, people, truth = [], [], []
    split_order = list(range(N_COMPANIES)); random.Random(SEED + 1).shuffle(split_order)
    split = {idx: ('development' if j < 300 else 'calibration' if j < 400 else 'test') for j, idx in enumerate(split_order)}
    for i in range(N_COMPANIES):
        rng = random.Random(SEED * 1009 + i * 7919)
        cid = f'cmp{i+1:04d}'
        name = f'{PREFIXES[i % len(PREFIXES)]} {SUFFIXES[(i // len(PREFIXES)) % len(SUFFIXES)]}'
        home = rng.choice(LOCATIONS[:-1])
        alt = rng.choice([x for x in LOCATIONS if x != home])
        target = rng.choices([145,165,190,220,260,310,380], weights=[12,20,22,18,13,10,5])[0] + rng.randint(-8,8)
        # Actual structure includes some people later removed from the observed roster.
        org=[]
        def add(title, dept, manager, level, group=None, loc=None):
            pid=f'{cid}-p{len(org)+1:04d}'
            person={'id':pid,'company_id':cid,'name':f'{rng.choice(FIRST)} {rng.choice(LAST)}','title':title,'department':dept,'location':loc or (home if rng.random()<0.78 else alt), '_manager':manager,'_level':level,'_group':group}
            org.append(person); return pid
        ceo=add(rng.choice(EXEC_TITLES['CEO']),'Executive',None,'executive',loc=home)
        cto=add(rng.choice(EXEC_TITLES['CTO']),'Technology',ceo,'executive',loc=home)
        cro=add(rng.choice(EXEC_TITLES['CRO']),'Commercial',ceo,'executive',loc=home)
        cfo=add(rng.choice(EXEC_TITLES['CFO']),'Finance',ceo,'executive',loc=home)
        coo=add(rng.choice(EXEC_TITLES['COO']),'Operations',ceo,'executive',loc=home)
        leaders={}
        for dept, info in DEPTS.items():
            parent = {'Engineering':cto,'Data':rng.choices([cto,coo,ceo],[0.60,0.25,0.15])[0], 'Security':rng.choices([cto,coo,ceo],[0.60,0.25,0.15])[0],
                      'Product':rng.choices([cto,ceo],[0.70,0.30])[0], 'Sales':cro,'Marketing':cro,'Customer Success':cro,
                      'Finance':cfo,'People':rng.choices([coo,ceo],[0.8,0.2])[0], 'Operations':coo,'Legal':ceo}[dept]
            leaders[dept]=add(rng.choice(info['heads']),dept,parent,'head',loc=home)
        teams=[]
        for dept, info in DEPTS.items():
            for group, ic_title in info['groups']:
                # Some teams have multiple indistinguishable managers; this is intentional.
                count=1 + (rng.random()<0.27)
                for j in range(count):
                    loc=home if (j==0 or rng.random()<0.45) else alt
                    title=rng.choice([f'{group} Manager', f'Manager, {group}', f'Mgr, {group}', f'{group} Team Lead'])
                    mid=add(title,dept,leaders[dept],'manager',group,loc)
                    teams.append((dept,group,ic_title,mid,loc))
        while len(org) < target:
            dept,group,title,mid,loc = rng.choice(teams)
            senior = rng.choices(['','Senior ','Sr. ','Staff ','Associate '],[0.43,0.21,0.14,0.07,0.15])[0]
            employee_loc=loc if rng.random()<0.78 else rng.choice([home,alt,'Remote'])
            add(senior+title,dept,mid,'ic',group,employee_loc)
        # Hide some managers, preserving orphaned reports. Do not hide CEOs or ICs.
        hidden={p['id'] for p in org if p['_level'] in ('manager','head','executive') and p['id']!=ceo and rng.random()<0.085}
        visible=[p for p in org if p['id'] not in hidden]
        # There is always a healthy margin above the required 100 observed employees.
        assert len(visible) >= 100
        for p in visible:
            title=p['title']; dept=p['department']; loc=p['location']
            noise=rng.random()
            if noise < .025: title = ''
            elif noise < .055: title = rng.choice(['Specialist','Associate','Manager','Team Member','Consultant'])
            elif noise < .11: title = title.replace('Engineering','Eng').replace('Information','Info').replace('Operations','Ops').replace('Director','Dir')
            if rng.random()<.16: dept=''
            elif rng.random()<.04: dept='Technology' if dept in ('Data','Engineering','Security') else 'Corporate'
            if rng.random()<.19: loc=''
            people.append({'id':p['id'],'company_id':cid,'name':p['name'],'title':title,'department':dept,'location':loc})
            truth.append({'person_id':p['id'],'manager_id':p['_manager']})
        random_industry=rng.choice(INDUSTRIES)
        suffix=SUFFIXES[(i // len(PREFIXES)) % len(SUFFIXES)]
        all_companies.append({'id':cid,'name':name,'industry':SUFFIX_INDUSTRY.get(suffix,random_industry),'location':home,'employee_count':len(visible),'split':split[i]})
    dump_json(OUT/'companies.json', all_companies)
    for path, rows in [(OUT/'people.jsonl',people),(OUT/'truth.jsonl',truth)]:
        with path.open('w', encoding='utf-8') as f:
            for row in rows: f.write(json.dumps(row,separators=(',',':'),ensure_ascii=False)+'\n')
    dump_json(OUT/'manifest.json',{'seed':SEED,'companies':len(all_companies),'observed_people':len(people),'splits':{k:sum(c['split']==k for c in all_companies) for k in ('development','calibration','test')},'truth_note':'truth.jsonl is only used for calibration and evaluation, never candidate generation'})
    print(json.dumps({'companies':len(all_companies),'observed_people':len(people),'min_company_size':min(c['employee_count'] for c in all_companies),'max_company_size':max(c['employee_count'] for c in all_companies)}))
if __name__=='__main__': main()
