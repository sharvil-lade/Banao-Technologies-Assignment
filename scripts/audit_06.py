import pandas as pd, numpy as np
pd.set_option('display.width',250); pd.set_option('display.max_columns',60); pd.set_option('display.max_rows',200)
t=pd.read_csv('data/raw/tickets.csv',dtype=str,keep_default_na=False)
a=pd.read_csv('data/raw/agents.csv',dtype=str,keep_default_na=False)
o=pd.read_csv('data/raw/orders.csv',dtype=str,keep_default_na=False)
cu=pd.read_csv('data/raw/customers.csv',dtype=str,keep_default_na=False)
pr=pd.read_csv('data/raw/products.csv',dtype=str,keep_default_na=False)
print("=== AGENTS ==="); print(a.head(8).to_string()); print("rows",len(a),"distinct agent_id",a.agent_id.nunique())
print("\nrows per agent:\n",a.groupby('agent_id').size().value_counts())
print("\nagents with >1 row:")
multi=a[a.agent_id.isin(a.agent_id.value_counts()[lambda s:s>1].index)].sort_values(['agent_id','from_date'])
print(multi.to_string())
print("\nto_date blank count:",(a.to_date=='').sum())
print("teams:",sorted(a.team.unique())); print("tiers:",a.tier.value_counts().to_dict()); print("sites:",a.site.value_counts().to_dict())
print("\nticket agent_ids not in roster:", sorted(set(t.agent_id)-set(a.agent_id)))
print("roster agents with no ticket:", sorted(set(a.agent_id)-set(t.agent_id)))

print("\n=== PRODUCTS ==="); print(pr.to_string())
print("\nticket skus not in products:",sorted(set(t.product_sku)-set(pr.sku)))
print("\n=== ORDERS ==="); print(o.head(3).to_string()); print("distinct order_id",o.order_id.nunique(),"rows",len(o))
to=set(t.order_id)-{''}
print("ticket order_ids missing from orders.csv:",len(to-set(o.order_id)), "of", len(to))
print("tickets with blank order_id:",(t.order_id=='').sum())
print("\n=== CUSTOMERS ==="); print(cu.head(3).to_string())
print("ticket customer_ids missing:",len(set(t.customer_id)-set(cu.customer_id)))
print("care_plus:",cu.care_plus.value_counts().to_dict())

# fallback join viability: customer_id + product_sku -> order
m=t[t.order_id==''].merge(o,left_on=['customer_id','product_sku'],right_on=['customer_id','sku'],how='left')
cnt=m.groupby('ticket_id').order_id_y.nunique()
print("\nfallback join (cust+sku) for blank-order tickets: 0 matches:",(cnt==0).sum()," 1 match:",(cnt==1).sum()," >1:",(cnt>1).sum())

# does order_id on ticket match the customer on the order?
j=t[t.order_id!=''].merge(o,on='order_id',how='left',suffixes=('_t','_o'))
print("\nticket.order rows w/ mismatched customer:",(j.customer_id_t!=j.customer_id_o).sum(),"of",len(j))
print("ticket.order rows w/ mismatched sku:",(j.product_sku!=j.sku).sum())
