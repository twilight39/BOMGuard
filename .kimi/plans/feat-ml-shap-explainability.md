# Plan: SHAP Explainability

## Goal
Enable per-p SHAP explanations for every ML prediction.

## Scope
- `backend/bomguard/ml/explainability.py`
- `backend/bomguard/api/substances.py` (`/api/substances/{cas}/shap`)

## Tasks
1. [ ] **TreeExplainer init**: Load trained model from registry; wrap with `shap.TreeExplainer`.
2. [ ] **Feature name mapping**: Ensure SHAP values map to readable feature names (descriptor names + PCA components).
3. [ ] **Per-substance explanation**: Given CAS + regulation, fetch cached features, run prediction, return top-20 positive/negative contributions.
4. [ ] **API response schema**: `ShapExplanationResponse` with `feature`, `value`, `contribution` arrays.
5. [ ] **Error handling**: Return 404 if model not trained; 400 if CAS has no cached features.
6. [ ] **Tests**: `tests/test_ml/test_shap.py` verifying output shape and sign consistency.

## Dependencies
- `feat/ml-training-registry` (trained models in registry)

## Outcome
`GET /api/substances/{cas}/shap?reg=eu_reach_svhc` returns interpretable feature contributions.
