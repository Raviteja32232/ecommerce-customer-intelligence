"""Export clean model tables (CSV) for Power BI + build report charts."""
import sqlite3, pandas as pd, numpy as np, pathlib
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, seaborn as sns
from sklearn.metrics import roc_curve, roc_auc_score
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT/"powerbi/data"; OUT.mkdir(exist_ok=True)
con = sqlite3.connect(ROOT/"data/ecommerce.db"); q = lambda s: pd.read_sql(s, con)

tables = {
 "dim_customer_360": """SELECT c.customer_id, c.state, c.signup_date, s.frequency, s.monetary, s.recency, s.tenure_days,
        s.R, s.F, s.M, s.rfm_score, s.rfm_segment, s.kmeans_segment, s.avg_review, s.avg_delay,
        v.p_alive, v.exp_orders_12m, v.clv_12m, v.clv_tier, ch.churn_probability, ch.risk_band
        FROM dim_customer c LEFT JOIN customer_segments s USING(customer_id)
        LEFT JOIN customer_clv v USING(customer_id) LEFT JOIN customer_churn ch USING(customer_id)""",
 "fact_orders": "SELECT * FROM fact_orders",
 "fact_order_items": """SELECT i.order_id,i.item_seq,i.product_id,i.price,i.freight,o.customer_id,o.order_date,o.order_status
        FROM order_items i JOIN fact_orders o USING(order_id)""",
 "dim_product": "SELECT * FROM dim_product",
 "dim_date": "SELECT * FROM dim_date",
 "v_monthly_revenue":"SELECT * FROM v_monthly_revenue", "v_cohort_retention":"SELECT * FROM v_cohort_retention",
 "v_delivery_vs_review":"SELECT * FROM v_delivery_vs_review", "v_category_performance":"SELECT * FROM v_category_performance",
 "v_pareto":"SELECT * FROM v_pareto",
}
for n,s in tables.items():
    d = q(s); d.to_csv(OUT/f"{n}.csv", index=False); print(f"{n:24s}{len(d):>8,} rows")

# ---------------- charts ----------------
sns.set_theme(style="whitegrid"); C = "#1f4e79"
fig,ax = plt.subplots(1,2,figsize=(13,4.5))
m = q("SELECT * FROM v_monthly_revenue"); ax[0].plot(m.year_month,m.revenue/1e6,color=C,lw=2); ax[0].set_title("Monthly revenue (₹ millions)")
ax[0].set_xticks(range(0,len(m),4)); ax[0].set_xticklabels(m.year_month[::4],rotation=45)
p = q("SELECT * FROM v_pareto"); ax[1].bar(p.decile,p.revenue_share_pct,color=C); ax[1].plot(p.decile,p.revenue_share_pct.cumsum(),color="#e07b00",marker="o")
ax[1].set_title("Revenue share by customer decile (bars) & cumulative (line)"); ax[1].set_xlabel("Customer decile (1 = top 10%)"); ax[1].set_ylabel("% of revenue")
plt.tight_layout(); plt.savefig(ROOT/"reports/01_revenue_and_pareto.png",dpi=150); plt.close()

seg = q("SELECT rfm_segment, COUNT(*) n, SUM(monetary) rev FROM customer_segments GROUP BY 1 ORDER BY rev DESC")
fig,ax = plt.subplots(1,2,figsize=(13,4.5)); sns.barplot(data=seg,y="rfm_segment",x="n",ax=ax[0],color=C); ax[0].set_title("Customers per RFM segment"); ax[0].set_ylabel("")
sns.barplot(data=seg,y="rfm_segment",x=100*seg.rev/seg.rev.sum(),ax=ax[1],color="#e07b00"); ax[1].set_title("% of lifetime revenue"); ax[1].set_ylabel(""); ax[1].set_xlabel("%")
plt.tight_layout(); plt.savefig(ROOT/"reports/02_rfm_segments.png",dpi=150); plt.close()

ch = q("SELECT * FROM v_cohort_retention"); ch["q"]=ch.cohort.str[:4]+"-Q"+((ch.cohort.str[5:7].astype(int)+2)//3).astype(str)
pv = ch[ch.month_n<=12].pivot_table(index="cohort",columns="month_n",values="retention_pct")
plt.figure(figsize=(11,8)); sns.heatmap(pv,cmap="Blues",annot=True,fmt=".0f",annot_kws={"size":6},cbar_kws={"label":"% active"}); plt.title("Cohort retention (% of cohort ordering in month N)")
plt.tight_layout(); plt.savefig(ROOT/"reports/03_cohort_heatmap.png",dpi=150); plt.close()

d = q("SELECT * FROM v_delivery_vs_review"); plt.figure(figsize=(7,4.5)); sns.barplot(data=d,x="delay_bucket",y="avg_review",color=C)
plt.title("Late delivery destroys customer satisfaction"); plt.xlabel(""); plt.ylabel("Avg review score"); plt.xticks(rotation=15); plt.ylim(0,5)
for i,v in enumerate(d.avg_review): plt.text(i,v+.05,f"{v:.2f}",ha="center")
plt.tight_layout(); plt.savefig(ROOT/"reports/04_delivery_vs_review.png",dpi=150); plt.close()

y,pr = np.load(ROOT/"outputs/roc_data.npy"); fpr,tpr,_ = roc_curve(y,pr)
plt.figure(figsize=(5.5,5)); plt.plot(fpr,tpr,color=C,lw=2,label=f"AUC = {roc_auc_score(y,pr):.3f}"); plt.plot([0,1],[0,1],"--",color="grey")
plt.title("Churn model ROC curve"); plt.xlabel("False positive rate"); plt.ylabel("True positive rate"); plt.legend(); plt.tight_layout(); plt.savefig(ROOT/"reports/05_churn_roc.png",dpi=150); plt.close()

# headline numbers
k = q("""SELECT ROUND(SUM(revenue)) rev, COUNT(*) orders, COUNT(DISTINCT customer_id) cust, ROUND(AVG(revenue)) aov FROM fact_orders WHERE order_status<>'cancelled'""").iloc[0]
print("\nHEADLINE:", k.to_dict())
print(q("SELECT risk_band, COUNT(*) n FROM customer_churn GROUP BY 1").to_string(index=False))
print(q("""SELECT ch.risk_band, COUNT(*) customers, ROUND(SUM(v.clv_12m)) clv_at_stake FROM customer_churn ch JOIN customer_clv v USING(customer_id)
          GROUP BY 1 ORDER BY clv_at_stake DESC""").to_string(index=False))
