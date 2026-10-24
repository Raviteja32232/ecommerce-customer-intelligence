import sqlite3, pandas as pd, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
con = sqlite3.connect(ROOT/"data/ecommerce.db")
con.executescript((ROOT/"sql/01_schema.sql").read_text())
for t in ["customers","products","orders","order_items","payments","reviews"]:
    pd.read_csv(ROOT/f"data/{t}.csv").to_sql(t, con, if_exists="append", index=False)
con.executescript((ROOT/"sql/02_star_schema.sql").read_text())
con.executescript((ROOT/"sql/03_analytical_views.sql").read_text())
con.commit()
for v in ["v_repeat_rate","v_category_performance","v_delivery_vs_review","v_pareto"]:
    print(f"\n== {v} =="); print(pd.read_sql(f"SELECT * FROM {v}", con).to_string(index=False))
print("\n== v_monthly_revenue (last 6) =="); print(pd.read_sql("SELECT * FROM v_monthly_revenue", con).tail(6).to_string(index=False))
con.close()
