# Plan: ML Training Pipeline + Model Registry

## Goal
Wire the existing XGBoost + Optuna training stubs to real production data and persist trained models.

## Scope
- `backend/bomguard/ml/models/train.py`
- `backend/bomguard/ml/models/registry.py`
- `backend/bomguard/ml/evaluate.py`
- `backend/bomguard/ml/features/engineering.py`

## Tasks
1. [ ] **Data wiring**: Read labels from `substance_regulation_status` table (restricted / not_restricted) per regulation.
2. [ ] **Feature alignment**: Join `substance_properties` (cached descriptors + Morgan PCA 50) with labels.
3. [ ] **Temporal split**: Implement `evaluate.py` holdout logic (temporal if ≥6 months history, else stratified random).
4. [ ] **Training loop**: One XGBoost classifier per ML-enabled regulation (`eu_reach_svhc`, `us_state_pfas`).
5. [ ] **Optuna**: 50-trial HPO with early stopping.
6. [ ] **Calibration**: `CalibratedClassifierCV` (isotonic) on holdout set.
7. [ ] **MLflow logging**: Log params, metrics, artifacts; tag `production` if ROC-AUC > 0.75 else `rejected`.
8. [ ] **Registry persistence**: Save model artifacts (pickle / joblib) to disk or MLflow; `registry.py` loads by regulation ID.
9. [ ] **Target metrics validation**: ROC-AUC > 0.75, AP > 0.25, Precision@Top100 > 0.15, Brier < 0.10.
10. [ ] **Tests**: Add `tests/test_ml/test_training.py` with a minimal synthetic dataset.

## Dependencies
- Existing feature pipeline (`substance_properties` populated)
- MLflow server running (port 5000)

## Outcome
Calling `train.py` for a regulation produces a calibrated, persisted model and logs to MLflow.
