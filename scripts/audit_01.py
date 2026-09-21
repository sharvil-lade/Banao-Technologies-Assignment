import pandas as pd, numpy as np, json
pd.set_option('display.width',200); pd.set_option('display.max_columns',50)
R='data/raw/'
t=pd.read_csv(R+'tickets.csv',dtype=str,keep_default_na=False)
print("TICKETS shape:",t.shape)
print("\ncolumns:",list(t.columns))
print("\n--- blank rate per column ---")
for c in t.columns:
    b=(t[c].str.strip()=='').sum()
    print(f"{c:22s} blank={b:6d} ({b/len(t)*100:5.1f}%)  distinct={t[c].nunique()}")
print("\n--- source_system ---"); print(t.source_system.value_counts(dropna=False))
print("\n--- status ---"); print(t.status.value_counts(dropna=False))
print("\n--- channel ---"); print(t.channel.value_counts(dropna=False))
print("\n--- assigned_team ---"); print(t.assigned_team.value_counts(dropna=False))
print("\n--- priority ---"); print(t.priority.value_counts(dropna=False))
print("\n--- category ---"); print(t.category.value_counts(dropna=False))
print("\n--- refund_reason_code ---"); print(t.refund_reason_code.value_counts(dropna=False))
print("\n--- replacement_issued ---"); print(t.replacement_issued.value_counts(dropna=False))
print("\n--- ticket_id sample ---"); print(t.ticket_id.head(5).tolist(), t.ticket_id.tail(5).tolist())
print("dup ticket_id count:", t.ticket_id.duplicated().sum())
print("\n--- created_at samples by source ---")
for s in t.source_system.unique():
    sub=t[t.source_system==s]
    print(s, sub.created_at.head(3).tolist(), "| resolved sample:", sub.resolved_at.head(3).tolist())
