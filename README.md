# Fraud Detection Dashboard

Streamlit dashboard for FAA4023 final assignment: automated fraud detection on PaySim-style transactions.

## Run the dashboard

```bash
streamlit run app/Home.py
```

The app reads `artifacts/scored_transactions.csv` when available. If artifacts are missing, it generates a deterministic demo dataset so the interface can still be reviewed and screenshotted.

## Train with PaySim

Place the Kaggle PaySim CSV in `data/raw/`, then run:

```bash
python scripts/train_models.py --input data/raw/PS_20174392719_1491204439457_log.csv
```

Outputs are written to `artifacts/`:

- `model_xgb.pkl`
- `model_iforest.pkl`
- `feature_pipeline.pkl`
- `scored_transactions.csv`
- `model_metrics.json`

## Test

```bash
pytest -q
```
