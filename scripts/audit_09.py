import pandas as pd, numpy as np, re
pd.set_option('display.width',260); pd.set_option('display.max_colwidth',200); pd.set_option('display.max_rows',100)
t=pd.read_csv('data/raw/tickets.csv',dtype=str,keep_default_na=False)
pr=pd.read_csv('data/raw/products.csv',dtype=str,keep_default_na=False)
t['amt']=pd.to_numeric(t.refund_amount_inr.replace('',np.nan),errors='coerce')
t['amt_norm']=np.where(t.source_system=='legacy_fd',t.amt/100,t.amt)
t['pref']=t.source_system.map({'helpdesk':0,'legacy_fd':1})
c=t.sort_values('pref').drop_duplicates('ticket_id',keep='first').copy()
c['q']=pd.to_datetime(c.created_at).dt.to_period('Q')
cr=c[c.amt_norm.notna()].copy()
notes=cr.agent_notes.str.lower()

pat_repl=re.compile(r'\b(rplc|replacement|replacment|new unit|new set|replaced|repl unit|sending a new)\b')
pat_both=re.compile(r'(refund \+ replacement|rfnd \+ rplc|refund and replacement|both)')
cr['note_repl']=notes.str.contains(pat_repl)
cr['note_both']=notes.str.contains(pat_both)
print("refund rows:",len(cr))
print("flag replacement_issued=Y:",(cr.replacement_issued=='Y').sum())
print("notes mention replacement:",cr.note_repl.sum())
print("notes mention BOTH explicitly:",cr.note_both.sum())
print("\ncrosstab flag vs note_both:\n",pd.crosstab(cr.replacement_issued,cr.note_both))
print("\ncrosstab flag vs note_repl:\n",pd.crosstab(cr.replacement_issued,cr.note_repl))
hidden=cr[(cr.replacement_issued=='N')&cr.note_both]
print("\nHIDDEN conflicts (flag=N, note says both):",len(hidden)," amount:",hidden.amt_norm.sum())
print(hidden[['ticket_id','refund_reason_code','amt_norm','assigned_team']].head(10).to_string())
print("\nsample hidden notes:")
for n in hidden.agent_notes.head(6): print("  -",n[:220])

print("\n=== conflict cost model (policy: unit_cost + Rs340) ===")
pr['uc']=pd.to_numeric(pr.unit_cost_inr)
conf=cr[(cr.replacement_issued=='Y')|cr.note_both].merge(pr[['sku','uc']],left_on='product_sku',right_on='sku',how='left')
conf['repl_cost']=conf.uc+340
print("total conflict tickets:",len(conf))
print("refund value:",conf.amt_norm.sum()," replacement cost:",conf.repl_cost.sum()," combined:",conf.amt_norm.sum()+conf.repl_cost.sum())
print("per quarter (18mo/6):", round((conf.amt_norm.sum()+conf.repl_cost.sum())/6))
print("\nby quarter:\n",conf.groupby('q').agg(n=('ticket_id','size'),refund=('amt_norm','sum'),repl=('repl_cost','sum')).to_string())

print("\n=== DUP-PAYMENT ===")
dp=cr[cr.refund_reason_code=='DUP-PAYMENT']
print("n:",len(dp),"amt:",dp.amt_norm.sum(),"per qtr:",round(dp.amt_norm.sum()/6))

print("\n=== GW-OTHER keyword fingerprint (deterministic proxy for miscoding) ===")
gw=cr[cr.refund_reason_code=='GW-OTHER'].copy()
gwn=gw.agent_notes.str.lower()+' || '+gw.customer_message.str.lower()
tests={
 'payment/dup': r'(debited|double charge|charged twice|duplicate|payment gateway|pg dashboard|no ord|utr|paid once|statement disagrees)',
 'transit/lost': r'(lost in transit|not delivered|awb|courier|undelivered|tracking not updating)',
 'transit damage/doa': r'(transit damage|damage conf|crack|arrived damaged|doa|dead on arrival)',
 'cancellation': r'(cancel)',
 'return/qc': r'(return received|qc|pickup|returned the)',
 'warranty': r'(warranty|wty|rma|repair)',
 'price/coupon': r'(coupon|price drop|price adj|discount not applied)',
}
for k,p in tests.items():
    m=gwn.str.contains(p,regex=True)
    print(f"  {k:20s} n={m.sum():4d}  amt={gw[m].amt_norm.sum():12.0f}")
print("GW total n=",len(gw),"amt=",gw.amt_norm.sum())
