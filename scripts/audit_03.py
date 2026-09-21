import pandas as pd, numpy as np
pd.set_option('display.width',250); pd.set_option('display.max_columns',60)
t=pd.read_csv('data/raw/tickets.csv',dtype=str,keep_default_na=False)
t['amt']=pd.to_numeric(t.refund_amount_inr.replace('',np.nan),errors='coerce')
print("non-numeric refund values:", t[t.refund_amount_inr.ne('') & t.amt.isna()].refund_amount_inr.unique()[:20])
d=t[t.ticket_id.duplicated(keep=False)]
p=d.pivot_table(index='ticket_id',columns='source_system',values='amt',aggfunc='first')
p=p.dropna(how='all')
print("\ndup ids with any amount:",len(p))
both=p.dropna()
print("dup ids with amount on BOTH:",len(both))
both=both.assign(ratio=both.legacy_fd/both.helpdesk)
print(both.ratio.describe())
print("\nratio value counts:\n",both.ratio.round(6).value_counts())
print("\nsample:\n",both.head(10))
print("\ndup ids amount on only one side:\n",p[p.isna().any(axis=1)].head(20))

print("\n=== amount distribution by source (all rows) ===")
for s in ['helpdesk','legacy_fd']:
    a=t[(t.source_system==s)&t.amt.notna()].amt
    print(s,"n=",len(a))
    print(a.describe([.01,.05,.25,.5,.75,.95,.99]).to_string())
    print("  distinct sample:",sorted(a.unique())[:15],"...",sorted(a.unique())[-10:])
    print("  %% divisible by 100:", round((a%100==0).mean()*100,2))
