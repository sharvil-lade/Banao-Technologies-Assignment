import pandas as pd, numpy as np
pd.set_option('display.width',250); pd.set_option('display.max_columns',50); pd.set_option('display.max_colwidth',40)
t=pd.read_csv('data/raw/tickets.csv',dtype=str,keep_default_na=False)
d=t[t.ticket_id.duplicated(keep=False)].sort_values(['ticket_id','source_system'])
print("rows involved in dup ticket_id:",len(d),"distinct ids:",d.ticket_id.nunique())
g=d.groupby('ticket_id').size().value_counts(); print("\ngroup sizes:\n",g)
# source combos
combo=d.groupby('ticket_id').source_system.apply(lambda s:'|'.join(sorted(s))).value_counts()
print("\nsource combos per dup id:\n",combo)
# which columns differ within a dup pair?
cols=[c for c in t.columns]
diff={}
for c in cols:
    n=d.groupby('ticket_id')[c].nunique()
    diff[c]=int((n>1).sum())
print("\n# dup-ids where column value differs:")
for c,v in diff.items(): print(f"  {c:22s} {v}")
print("\n=== EXAMPLE DUP PAIRS ===")
ids=d.ticket_id.unique()[:3]
for i in ids:
    print(d[d.ticket_id==i][['ticket_id','created_at','resolved_at','status','agent_id','refund_amount_inr','refund_reason_code','replacement_issued','transfers','csat_score','source_system','order_id']].to_string())
    print()
# are all dup ids inside legacy window?
d2=d.copy(); d2['cdate']=pd.to_datetime(d2.created_at)
print("dup created_at min/max:",d2.cdate.min(),d2.cdate.max())
t2=t.copy(); t2['cdate']=pd.to_datetime(t2.created_at)
print("\nsource_system x created month range:")
print(t2.groupby('source_system').cdate.agg(['min','max','count']))
# helpdesk rows before go-live
gl=pd.Timestamp('2025-09-14')
print("\nhelpdesk rows created before 2025-09-14:",((t2.source_system=='helpdesk')&(t2.cdate<gl)).sum())
print("legacy rows created on/after 2025-09-14:",((t2.source_system=='legacy_fd')&(t2.cdate>=gl)).sum())
