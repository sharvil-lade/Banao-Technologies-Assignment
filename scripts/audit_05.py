import pandas as pd, numpy as np
pd.set_option('display.width',250); pd.set_option('display.max_columns',60); pd.set_option('display.max_rows',120)
t=pd.read_csv('data/raw/tickets.csv',dtype=str,keep_default_na=False)
for c in ['created_at','first_response_at','resolved_at']:
    t[c+'_ts']=pd.to_datetime(t[c].replace('',np.nan),errors='coerce')
print("unparseable timestamps:",{c:int(t[c+'_ts'].isna().sum()-(t[c]=='').sum()) for c in ['created_at','first_response_at','resolved_at']})
t['fr_min']=(t.first_response_at_ts-t.created_at_ts).dt.total_seconds()/60
t['res_hr']=(t.resolved_at_ts-t.created_at_ts).dt.total_seconds()/3600
print("\n=== first_response - created (minutes) by source ===")
print(t.groupby('source_system').fr_min.describe([.01,.05,.5,.95,.99]).to_string())
print("negative fr:",(t.fr_min<0).sum())
print("\n=== resolved - created (hours) by source ===")
print(t.groupby('source_system').res_hr.describe([.01,.05,.5,.95,.99]).to_string())
print("negative res by source:\n",t[t.res_hr<0].groupby('source_system').size())
print("res_hr < 0 examples:\n",t[t.res_hr<0][['ticket_id','created_at','first_response_at','resolved_at','source_system']].head(8).to_string())
print("\n=== resolved - first_response (hours) by source ===")
t['h2']=(t.resolved_at_ts-t.first_response_at_ts).dt.total_seconds()/3600
print(t.groupby('source_system').h2.describe([.01,.05,.5]).to_string())
print("negative:\n",t[t.h2<0].groupby('source_system').size())

print("\n=== hour-of-day histogram of resolved_at by source (looking for UTC shift) ===")
t['rh']=t.resolved_at_ts.dt.hour
piv=t.pivot_table(index='rh',columns='source_system',values='ticket_id',aggfunc='count').fillna(0).astype(int)
print(piv.to_string())
print("\n=== hour-of-day of created_at by source ===")
t['ch']=t.created_at_ts.dt.hour
print(t.pivot_table(index='ch',columns='source_system',values='ticket_id',aggfunc='count').fillna(0).astype(int).to_string())
