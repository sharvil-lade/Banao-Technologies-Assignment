import pandas as pd, numpy as np
pd.set_option('display.width',250); pd.set_option('display.max_columns',60); pd.set_option('display.max_rows',100)
t=pd.read_csv('data/raw/tickets.csv',dtype=str,keep_default_na=False)
t['amt']=pd.to_numeric(t.refund_amount_inr.replace('',np.nan),errors='coerce')
t['cdate']=pd.to_datetime(t.created_at); t['q']=t.cdate.dt.to_period('Q')

print("=== A. NAIVE (what Finance likely did): sum all rows as-is ===")
print(t.groupby('q').amt.agg(['sum','count']).to_string())
print("total naive:", t.amt.sum(), " => per-quarter avg:", round(t.amt.sum()/6))

print("\n=== B. helpdesk-only rows as-is (what helpdesk report likely shows) ===")
h=t[t.source_system=='helpdesk']
print(h.groupby('q').amt.agg(['sum','count']).to_string())
print("total:",h.amt.sum(),"avg/qtr:",round(h.amt.sum()/6))

print("\n=== C. dedup(keep helpdesk) + legacy/100 ===")
t['amt_norm']=np.where(t.source_system=='legacy_fd', t.amt/100, t.amt)
pref={'helpdesk':0,'legacy_fd':1}
t['pref']=t.source_system.map(pref)
c=t.sort_values('pref').drop_duplicates('ticket_id',keep='first')
print(c.groupby('q').amt_norm.agg(['sum','count']).to_string())
print("total:",c.amt_norm.sum(),"avg/qtr:",round(c.amt_norm.sum()/6))

print("\n=== refund+replacement conflicts (canonical) ===")
conf=c[(c.amt_norm.notna())&(c.replacement_issued=='Y')]
print("count:",len(conf)," amount:",conf.amt_norm.sum())
print(conf.groupby('assigned_team').agg(n=('ticket_id','size'),amt=('amt_norm','sum')).to_string())
print(conf.refund_reason_code.value_counts().to_string())

print("\n=== refunds with blank reason code (canonical) ===")
print(((c.amt_norm.notna())&(c.refund_reason_code=='')).sum())
print("\n=== reason code with NO amount ===")
print(((c.amt_norm.isna())&(c.refund_reason_code!='')).sum())

print("\n=== canonical refunds by reason ===")
cr=c[c.amt_norm.notna()]
print(cr.groupby('refund_reason_code').agg(n=('ticket_id','size'),amt=('amt_norm','sum'),med=('amt_norm','median')).sort_values('amt',ascending=False).to_string())

print("\n=== status of refund tickets ===")
print(cr.status.value_counts().to_string())

print("\n=== GW-OTHER over policy cap 500 ===")
gw=cr[cr.refund_reason_code=='GW-OTHER']
print("n=",len(gw),"amt=",gw.amt_norm.sum()," over500 n=",(gw.amt_norm>500).sum()," over500 amt=",gw[gw.amt_norm>500].amt_norm.sum())
print(gw.amt_norm.describe().to_string())

print("\n=== amount == 350 (SLA credit?) ===")
print((cr.amt_norm==350).sum())
