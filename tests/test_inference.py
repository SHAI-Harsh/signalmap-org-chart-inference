import json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from inference import parse,candidates_for_company
from build_data import fit_calibration,confidence

def person(pid,title,company='a',location='Austin'):
    return {'id':pid,'company_id':company,'name':pid,'title':title,'department':'','location':location}

class InferenceTests(unittest.TestCase):
    def test_distinguishes_product_manager_from_manager_of_product_team(self):
        self.assertEqual(parse(person('1','Senior Product Manager'))['role'],'individual contributor')
        self.assertEqual(parse(person('2','Manager, Product Management'))['role'],'manager')
        self.assertEqual(parse(person('3','Data Engineering Team Lead'))['role'],'ambiguous')
    def test_missing_and_generic_titles_abstain(self):
        for title in ('','Manager','Specialist'):
            out=candidates_for_company([person('x',title),person('m','Data Engineering Manager')])['x']
            self.assertIsNone(out['candidate_id']);self.assertEqual(out['kind'],'insufficient')
    def test_unique_more_senior_same_specialty(self):
        rows=[person('e','Sr. Data Engineer'),person('m','Mgr, Data Engineering'),person('wrong','Security Engineering Manager')]
        out=candidates_for_company(rows)['e']
        self.assertEqual(out['candidate_id'],'m');self.assertIn('matching location',out['reason'])
    def test_equal_plausible_managers_are_not_broken_by_id(self):
        rows=[person('e','Data Engineer'),person('a','Data Engineering Manager'),person('b','Manager, Data Engineering')]
        out=candidates_for_company(rows)['e']
        self.assertIsNone(out['candidate_id']);self.assertEqual(out['kind'],'ambiguous')
    def test_missing_direct_manager_does_not_jump_to_head(self):
        rows=[person('e','Data Engineer'),person('h','Head of Data')]
        self.assertIsNone(candidates_for_company(rows)['e']['candidate_id'])
    def test_never_crosses_company_boundaries_even_with_mixed_input(self):
        rows=[person('e','Data Engineer','a'),person('m','Data Engineering Manager','b'),person('cto','CTO','a'),person('ceo','CEO','b')]
        out=candidates_for_company(rows)
        self.assertIsNone(out['e']['candidate_id']);self.assertIsNone(out['cto']['candidate_id'])
    def test_calibration_is_monotone_and_not_certain(self):
        blocks=fit_calibration([(.5,True),(.5,False),(.7,True),(.9,False)])
        values=[b['probability'] for b in blocks]
        self.assertEqual(values,sorted(values))
        self.assertTrue(all(0<v<1 for v in values))
        self.assertLessEqual(confidence(.5,blocks),confidence(.9,blocks))

class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.companies=json.loads((ROOT/'data/companies.json').read_text())
    def test_size_and_company_disjoint_splits(self):
        self.assertEqual(len(self.companies),500)
        self.assertTrue(all(c['employee_count']>=100 for c in self.companies))
        self.assertEqual(len({c['id'] for c in self.companies}),500)
        self.assertEqual({s:sum(c['split']==s for c in self.companies) for s in ('development','calibration','test')}, {'development':300,'calibration':100,'test':100})
    def test_every_published_forest_is_acyclic_and_in_company(self):
        count=0
        for co in self.companies:
            data=json.loads((ROOT/'dist/data/companies'/f"{co['id']}.json").read_text())
            rows=data['people'];byid={p['id']:p for p in rows};count+=len(rows)
            self.assertEqual(len(rows),co['employee_count'])
            self.assertEqual(len(byid),len(rows))
            for p in rows:
                self.assertEqual(p['company_id'],co['id'])
                self.assertNotIn('_manager',p)
                if p['manager_id']:
                    self.assertIn(p['manager_id'],byid)
                    self.assertGreaterEqual(p['confidence'],.85)
                    self.assertLess(p['confidence'],1)
                    self.assertLess(parse(p)['rank'],parse(byid[p['manager_id']])['rank'])
                seen=set();cur=p
                while cur.get('manager_id'):
                    self.assertNotIn(cur['id'],seen);seen.add(cur['id']);cur=byid[cur['manager_id']]
        self.assertEqual(count,106250)
    def test_evaluation_denominators_and_static_assets(self):
        r=json.loads((ROOT/'data/evaluation.json').read_text());m=r['test']
        self.assertEqual(r['dataset']['test_companies'],100)
        self.assertLessEqual(m['correct'],m['emitted']);self.assertLessEqual(m['emitted'],m['eligible'])
        self.assertAlmostEqual(m['precision'],m['correct']/m['emitted'],places=4)
        self.assertFalse((ROOT/'dist/data/truth.jsonl').exists())
if __name__=='__main__':unittest.main()
