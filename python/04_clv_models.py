"""BG/NBD (purchase frequency + P(alive)) and Gamma-Gamma (monetary value) implemented with scipy.
Equivalent to lifetimes.BetaGeoFitter / GammaGammaFitter. Time unit = weeks."""
import sqlite3, pandas as pd, numpy as np, pathlib
from scipy.optimize import minimize
from scipy.special import gammaln, hyp2f1
ROOT = pathlib.Path(__file__).resolve().parents[1]
con = sqlite3.connect(ROOT/"data/ecommerce.db")

def summary(end, orders):
    o = orders[orders.order_date<=end]
    g = o.groupby("customer_id").agg(first=("order_date","min"),last=("order_date","max"),n=("order_id","count"),m=("revenue","mean"))
    g["x"] = g.n-1                                   # repeat purchases
    g["t_x"] = (g["last"]-g["first"]).dt.days/7      # recency (age at last purchase)
    g["T"] = (end-g["first"]).dt.days/7              # customer age
    return g

# ---- BG/NBD ----
def bgnbd_ll(p, x, t_x, T):
    r,a_,al,b_ = np.exp(p)   # r, alpha, a, b
    r,al,a,b = r,a_,al,b_
    A1 = gammaln(r+x)-gammaln(r)+r*np.log(al)
    A2 = gammaln(a+b)+gammaln(b+x)-gammaln(b)-gammaln(a+b+x)
    A3 = -(r+x)*np.log(al+T)
    A4 = np.where(x>0, np.log(a)-np.log(np.maximum(b+x-1,1e-9))-(r+x)*np.log(al+t_x), -np.inf)
    return -np.sum(A1+A2+np.logaddexp(A3,A4))

def fit_bgnbd(g):
    res = minimize(bgnbd_ll, np.log([1,10,1,3]), args=(g.x.values,g.t_x.values,g["T"].values), method="L-BFGS-B")
    r,alpha,a,b = np.exp(res.x); return dict(r=r,alpha=alpha,a=a,b=b)

def p_alive(m,x,t_x,T):
    r,al,a,b = m["r"],m["alpha"],m["a"],m["b"]
    ratio = np.where(x>0, a/np.maximum(b+x-1,1e-9)*((al+T)/(al+t_x))**(r+x), 0)
    return 1/(1+ratio)

def exp_purchases(m,x,t_x,T,t):
    r,al,a,b = m["r"],m["alpha"],m["a"],m["b"]
    a_eff = max(a,1.0001)
    num = (a_eff+b+x-1)/(a_eff-1)*(1-((al+T)/(al+T+t))**(r+x)*hyp2f1(r+x,b+x,a_eff+b+x-1,t/(al+T+t)))
    ratio = np.where(x>0, a_eff/np.maximum(b+x-1,1e-9)*((al+T)/(al+t_x))**(r+x), 0)
    return num/(1+ratio)

# ---- Gamma-Gamma ----
def gg_ll(p, x, m):
    pp,q,v = np.exp(p)
    return -np.sum(gammaln(x*pp+q)-gammaln(x*pp)-gammaln(q)+q*np.log(v)+(x*pp-1)*np.log(m)+(x*pp)*np.log(x)-(x*pp+q)*np.log(x*m+v))
def fit_gg(g):
    rep = g[g.x>0]
    res = minimize(gg_ll, np.log([2,3,500]), args=(rep.x.values,rep.m.values), method="L-BFGS-B")
    pp,q,v = np.exp(res.x); return dict(p=pp,q=q,v=v)
def exp_avg_value(gg,x,m):  # shrinks observed avg towards population mean
    return np.where(x>0, gg["p"]*(gg["v"]+x*m)/(gg["p"]*x+gg["q"]-1), gg["p"]*gg["v"]/(gg["q"]-1))

orders = pd.read_sql("SELECT order_id,customer_id,order_date,revenue FROM fact_orders WHERE order_status<>'cancelled'", con, parse_dates=["order_date"])

# ---- Validation: calibrate on <= 2025-06-30, predict Jul-Dec 2025 ----
cal_end, hold_end = pd.Timestamp("2025-06-30"), pd.Timestamp("2025-12-31")
cal = summary(cal_end, orders); mdl_v = fit_bgnbd(cal)
hold = orders[(orders.order_date>cal_end)&(orders.order_date<=hold_end)].groupby("customer_id").size()
cal["actual"] = hold.reindex(cal.index).fillna(0)
weeks = (hold_end-cal_end).days/7
cal["pred"] = exp_purchases(mdl_v,cal.x.values,cal.t_x.values,cal["T"].values,weeks)
print("BG/NBD params (calibration):", {k:round(v,3) for k,v in mdl_v.items()})
print(f"Holdout validation: actual orders={cal.actual.sum():.0f}  predicted={cal.pred.sum():.0f}  "
      f"error={100*(cal.pred.sum()-cal.actual.sum())/cal.actual.sum():+.1f}%  corr={np.corrcoef(cal.actual,cal.pred)[0,1]:.3f}")
cal["decile"] = pd.qcut(cal.pred.rank(method="first"),10,labels=False)
print(cal.groupby("decile")[["pred","actual"]].mean().round(3).T.to_string())
cal.groupby("decile")[["pred","actual"]].mean().to_csv(ROOT/"outputs/clv_validation_deciles.csv")

# ---- Final model on all data, 12-month CLV ----
g = summary(hold_end, orders)
mdl = fit_bgnbd(g); gg = fit_gg(g)
print("\nFinal BG/NBD:", {k:round(v,3) for k,v in mdl.items()}, "| Gamma-Gamma:", {k:round(v,2) for k,v in gg.items()})
print("corr(frequency, monetary) among repeaters (Gamma-Gamma assumes ~0):", round(g[g.x>0][["x","m"]].corr().iloc[0,1],3))
g["p_alive"] = p_alive(mdl,g.x.values,g.t_x.values,g["T"].values)
g["exp_orders_12m"] = exp_purchases(mdl,g.x.values,g.t_x.values,g["T"].values,52)
g["exp_avg_order_value"] = exp_avg_value(gg,g.x.values,g.m.values)
g["clv_12m"] = g.exp_orders_12m*g.exp_avg_order_value
out = g[["x","t_x","T","m","p_alive","exp_orders_12m","exp_avg_order_value","clv_12m"]].round(4).reset_index()
out.columns = ["customer_id","repeat_purchases","recency_weeks","age_weeks","avg_order_value","p_alive","exp_orders_12m","exp_avg_order_value","clv_12m"]
out["clv_tier"] = pd.qcut(out.clv_12m.rank(method="first"),[0,.5,.8,.95,1],labels=["Low","Medium","High","Top 5%"])
out.to_sql("customer_clv", con, if_exists="replace", index=False); con.commit()
print(f"\nTotal predicted 12-month revenue: {out.clv_12m.sum():,.0f}")
top20 = 100*out.clv_12m.nlargest(int(len(out)*.2)).sum()/out.clv_12m.sum()
print(f"Top 20% of customers by CLV = {top20:.1f}% of predicted 12-month revenue")
print(out.groupby("clv_tier",observed=True).agg(customers=("customer_id","count"),clv=("clv_12m","sum"),avg_p_alive=("p_alive","mean")).round(2).to_string())
