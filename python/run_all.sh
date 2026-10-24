#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
python3 python/01_generate_data.py       # skip if you use the real Kaggle CSVs
python3 python/02_build_database.py
python3 python/03_rfm_segmentation.py
python3 python/04_clv_models.py
python3 python/05_churn_model.py
python3 python/06_export_for_powerbi.py
