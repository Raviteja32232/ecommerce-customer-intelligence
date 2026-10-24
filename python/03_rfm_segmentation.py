"""RFM scoring + K-Means segmentation -> table customer_segments"""
import sqlite3, pandas as pd, numpy as np, pathlib
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
ROOT = pathlib.Path(__file__).resolve().parents[1]
con = sqlite3.connect(ROOT/"data/ecommerce.db")
SNAPSHOT = pd.Timestamp("2025-12-31")

df = pd.read_sql("SELECT * FROM v_customer_base", con, parse_dates=["first_order","last_order","signup_date"])
df["recency"] = (SNAPSHOT - df.last_order).dt.days
df["tenure_days"] = (SNAPSHOT - df.first_order).dt.days

# --- RFM quintile scores (5 = best) ---
df["R"] = pd.qcut(df.recency.rank(method="first"), 5, labels=[5,4,3,2,1]).astype(int)
df["F"] = pd.qcut(df.frequency.rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
df["M"] = pd.qcut(df.monetary.rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
df["rfm_score"] = df.R*100 + df.F*10 + df.M

def label(r):
    if r.R>=4 and r.F>=4: return "Champions"
    if r.R>=3 and r.F>=3: return "Loyal"
    if r.R>=4 and r.F<=2: return "New / Promising"
    if r.R==3:            return "Needs Attention"
    if r.R<=2 and r.F>=4: return "Cant Lose Them"
    if r.R<=2 and r.F>=2: return "At Risk"
    return "Hibernating / Lost"
df["rfm_segment"] = df.apply(label, axis=1)

# --- K-Means on log-scaled RFM ---
X = StandardScaler().fit_transform(np.log1p(df[["recency","frequency","monetary"]]))
scores = {k: silhouette_score(X, KMeans(k,n_init=10,random_state=42).fit_predict(X), sample_size=4000, random_state=42) for k in range(2,8)}
print("Silhouette by k:", {k: round(v,3) for k,v in scores.items()})
K = 4
df["cluster"] = KMeans(K,n_init=20,random_state=42).fit_predict(X)
prof = df.groupby("cluster").agg(recency=("recency","mean"),frequency=("frequency","mean"),monetary=("monetary","mean"),n=("customer_id","count"))
# name clusters by value rank
order = (prof.monetary.rank()+prof.frequency.rank()-prof.recency.rank()).sort_values(ascending=False).index.tolist()
names = dict(zip(order, ["VIP Loyalists","Steady Buyers","Lapsing Customers","Lost / One-time"]))
df["kmeans_segment"] = df.cluster.map(names)

print("\nRFM segments:"); 
seg = df.groupby("rfm_segment").agg(customers=("customer_id","count"),revenue=("monetary","sum"),avg_recency=("recency","mean"),avg_freq=("frequency","mean"),avg_monetary=("monetary","mean")).round(1)
seg["rev_share_%"]=(100*seg.revenue/seg.revenue.sum()).round(1); print(seg.sort_values("revenue",ascending=False).to_string())
print("\nK-Means segments:"); print(df.groupby("kmeans_segment").agg(customers=("customer_id","count"),recency=("recency","mean"),frequency=("frequency","mean"),monetary=("monetary","mean")).round(1).to_string())

df.drop(columns=["cluster"]).to_sql("customer_segments", con, if_exists="replace", index=False)
con.commit()
