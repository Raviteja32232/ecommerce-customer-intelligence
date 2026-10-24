"""Churn prediction for ACTIVE customers (bought in the 180 days before the snapshot).
Churn = no purchase in the 180 days after the snapshot date.
Train on snapshot 2025-06-30 (label from Jul-Dec 2025). No leakage: features use only data <= snapshot."""
import sqlite3, pandas as pd, numpy as np, pathlib, json
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, confusion_matrix, average_precision_score
from sklearn.inspection import permutation_importance
ROOT = pathlib.Path(__file__).resolve().parents[1]
con = sqlite3.connect(ROOT/"data/ecommerce.db")
HORIZON = 180
o = pd.read_sql("""SELECT order_id,customer_id,order_date,revenue,review_score,delay_days,order_status
                   FROM fact_orders WHERE order_status<>'cancelled'""", con, parse_dates=["order_date"])
cust = pd.read_sql("SELECT customer_id,state FROM dim_customer", con)

def features(snap):
    h = o[o.order_date<=snap].sort_values("order_date")
    g = h.groupby("customer_id")
    f = pd.DataFrame({
        "frequency": g.size(),
        "monetary": g.revenue.sum(),
        "avg_order_value": g.revenue.mean(),
        "recency": (snap-g.order_date.max()).dt.days,
        "tenure": (snap-g.order_date.min()).dt.days,
        "avg_review": g.review_score.mean(),
        "last_review": g.review_score.last(),
        "avg_delay": g.delay_days.mean(),
        "late_orders": g.delay_days.apply(lambda s:(s>0).sum()),
        "returns": g.order_status.apply(lambda s:(s=="returned").sum()),
    })
    f["orders_last_90d"] = h[h.order_date>snap-pd.Timedelta(days=90)].groupby("customer_id").size().reindex(f.index).fillna(0)
    f["avg_gap_days"] = (f.tenure/(f.frequency-1).replace(0,np.nan)).fillna(f.tenure+1)
    f["recency_vs_gap"] = f.recency/f.avg_gap_days
    return f

SNAP = pd.Timestamp("2025-06-30")
ACTIVE_WINDOW = 180
X = features(SNAP); X = X[X.recency<=ACTIVE_WINDOW]       # only customers who are currently "active"
future = o[(o.order_date>SNAP)&(o.order_date<=SNAP+pd.Timedelta(days=HORIZON))].customer_id.unique()
y = (~X.index.isin(future)).astype(int)          # 1 = churned
print(f"Active customers at snapshot: {len(X):,} | churn rate: {y.mean():.1%}")
Xtr,Xte,ytr,yte = train_test_split(X,y,test_size=.25,stratify=y,random_state=42)

models = {
 "Logistic Regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced")),
 "Gradient Boosting":   HistGradientBoostingClassifier(max_depth=4,learning_rate=.05,max_iter=300,l2_regularization=1.0,random_state=42),
}
rows=[]
for n,m in models.items():
    m.fit(Xtr,ytr); p=m.predict_proba(Xte)[:,1]; pred=(p>=.5).astype(int)
    rows.append(dict(model=n,roc_auc=roc_auc_score(yte,p),pr_auc=average_precision_score(yte,p),
                     precision=precision_score(yte,pred),recall=recall_score(yte,pred),f1=f1_score(yte,pred)))
res = pd.DataFrame(rows).round(3); print(res.to_string(index=False)); res.to_csv(ROOT/"outputs/churn_model_metrics.csv",index=False)

best = models["Logistic Regression"]; p = best.predict_proba(Xte)[:,1]   # best AUC + interpretable
print("Confusion matrix [[TN FP][FN TP]]:", confusion_matrix(yte,(p>=.5).astype(int)).tolist())
pi = permutation_importance(best,Xte,yte,scoring="roc_auc",n_repeats=5,random_state=42)
imp = pd.Series(pi.importances_mean,index=X.columns).sort_values(ascending=False).round(4)
print("\nPermutation importance (drop in AUC):"); print(imp.head(6).to_string()); imp.to_csv(ROOT/"outputs/churn_feature_importance.csv")
np.save(ROOT/"outputs/roc_data.npy", np.vstack([yte,p]))
# lift: top decile of predicted risk
d = pd.DataFrame({"y":yte,"p":p}); d["dec"]=pd.qcut(d.p.rank(method="first"),10,labels=False)
print("\nChurn rate in highest-risk decile: %.1f%% vs base %.1f%%" % (100*d[d.dec==9].y.mean(), 100*d.y.mean()))

# ---- Score today's customers (features as of 2025-12-31) ----
today_all = features(pd.Timestamp("2025-12-31"))
today = today_all[today_all.recency<=ACTIVE_WINDOW]
best.fit(X,y)    # refit on all snapshot data
sc = pd.DataFrame({"customer_id":today.index,"churn_probability":best.predict_proba(today)[:,1].round(4)})
sc["risk_band"] = pd.cut(sc.churn_probability,[-.01,.4,.7,1.0],labels=["Low","Medium","High"]).astype(str)
lost = pd.DataFrame({"customer_id":today_all.index.difference(today.index),"churn_probability":1.0,"risk_band":"Already Lost"})
sc = pd.concat([sc,lost],ignore_index=True)
sc.to_sql("customer_churn", con, if_exists="replace", index=False); con.commit()
print("\nRisk bands (all customers, today):"); print(sc.risk_band.value_counts().to_string())
