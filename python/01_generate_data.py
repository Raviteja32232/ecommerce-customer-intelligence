"""Generate a realistic synthetic e-commerce dataset (Olist-like schema).
Replace with real Kaggle CSVs by dropping them in /data with the same column names."""
import numpy as np, pandas as pd
rng = np.random.default_rng(42)

N_CUST = 8000
START, END = pd.Timestamp("2023-01-01"), pd.Timestamp("2025-12-31")
days = (END - START).days

states = ["Telangana","Maharashtra","Karnataka","Delhi","Tamil Nadu","Gujarat","West Bengal","Uttar Pradesh"]
state_p = [.14,.20,.16,.12,.12,.08,.08,.10]
cats = {"Electronics":(3500,.18),"Fashion":(1200,.22),"Home & Kitchen":(1800,.16),"Beauty":(700,.12),
        "Books":(400,.08),"Sports":(1500,.07),"Toys":(900,.06),"Grocery":(500,.11)}

customers = pd.DataFrame({
    "customer_id": [f"C{i:05d}" for i in range(N_CUST)],
    "state": rng.choice(states, N_CUST, p=state_p),
    "signup_date": START + pd.to_timedelta(rng.integers(0, days-30, N_CUST), unit="D"),
})

prods = []
for c,(base,_) in cats.items():
    for j in range(25):
        prods.append((f"P{len(prods):04d}", c, round(base*rng.lognormal(0,.45),0)))
products = pd.DataFrame(prods, columns=["product_id","category","price"])
cat_w = np.array([v[1] for v in cats.values()]); cat_w/=cat_w.sum()
prod_p = np.repeat(cat_w,25)/25

customers["freq_rate"] = rng.gamma(1.2, 0.012, N_CUST)
customers["lifetime_days"] = rng.exponential(260, N_CUST)
customers["spend_mult"] = rng.lognormal(0, .35, N_CUST)

orders, items, pays, revs = [], [], [], []
oid = 0
for r in customers.itertuples():
    t = r.signup_date
    end_active = min(END, r.signup_date + pd.Timedelta(days=float(r.lifetime_days)))
    first = True
    while True:
        if not first:
            t = t + pd.Timedelta(days=float(rng.exponential(1/max(r.freq_rate,1e-4))))
        first = False
        if t > end_active: break
        oid += 1
        o = f"O{oid:07d}"
        n_items = rng.choice([1,2,3,4],p=[.6,.25,.1,.05])
        total = 0
        for k in range(n_items):
            p = products.iloc[rng.choice(len(products), p=prod_p)]
            price = round(p.price*r.spend_mult*rng.uniform(.9,1.1),2)
            items.append((o,k+1,p.product_id,price,round(rng.uniform(20,150),2)))
            total += price
        promised = int(rng.integers(5,12))
        delay = int(rng.choice([-3,-1,0,2,5,9],p=[.2,.3,.25,.12,.08,.05]))
        status = rng.choice(["delivered","cancelled","returned"],p=[.93,.04,.03])
        orders.append((o,r.customer_id,t,t+pd.Timedelta(days=promised+delay),t+pd.Timedelta(days=promised),status))
        pays.append((o,rng.choice(["UPI","credit_card","debit_card","COD","wallet"],p=[.38,.25,.12,.18,.07]),round(total,2)))
        base_score = 4.5 - 0.35*max(delay,0) - (1.5 if status!="delivered" else 0)
        revs.append((o,int(np.clip(round(rng.normal(base_score,.7)),1,5))))

orders = pd.DataFrame(orders,columns=["order_id","customer_id","order_date","delivered_date","estimated_delivery_date","order_status"])
items = pd.DataFrame(items,columns=["order_id","item_seq","product_id","price","freight"])
payments = pd.DataFrame(pays,columns=["order_id","payment_type","payment_value"])
reviews = pd.DataFrame(revs,columns=["order_id","review_score"])
customers = customers[["customer_id","state","signup_date"]]

for n,d in dict(customers=customers,orders=orders,order_items=items,products=products,payments=payments,reviews=reviews).items():
    d.to_csv(f"data/{n}.csv",index=False); print(f"{n:12s}{len(d):>8,}")
