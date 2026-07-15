# Smart Career Portal — FastAPI + React Production Migration Plan

## Background
The project predicts career paths for Nigerian SS1/SS2/SS3 students using:
1. **XGBoost model** (via sklearn Pipeline): predicts career using subject grades + department info
2. **Gemini LLM**: takes XGBoost result + test scores (cognitive, aptitude, psychometric, sentiment) to produce a final enhanced prediction

The new model (`new_model.ipynb`) uses a **sklearn Pipeline** (`ColumnTransformer` + `XGBClassifier`) saved to `models/xgb_best_model.pkl` + `models/label_encoder.pkl`.

The existing `machine-learning/predict.py` has bugs — wrong model path, and doesn't account for the Pipeline structure (the model already includes preprocessing).

---

## User Review Required

> [!IMPORTANT]
> The new model uses a full `sklearn.pipeline.Pipeline` that includes `ColumnTransformer` (StandardScaler + OrdinalEncoder) + XGBClassifier.
> This means **the saved model already handles all preprocessing internally**. The `predict.py` currently applies manual grade mapping and type conversions before calling `model.predict()`, which should still work since the grades are already mapped to numbers before passing to the pipeline.

> [!WARNING]
> The `machine-learning/predict.py` has a wrong path:
> - Line 8: `MODEL_PATH = BASE_DIR.parent.parent / "models"` — resolves to project root `/models/` ✅ (correct since notebook saves there)
> - Line 9: `LABEL_ENCODER_PATH = BASE_DIR.parent.parent / "model_artifacts" / "label_encoder.pkl"` — **WRONG**: should be `models/label_encoder.pkl`, not `model_artifacts/label_encoder.pkl`

> [!IMPORTANT]
> The `history` column is in the notebook's drop list (`df.drop(columns=['French', 'History', 'Age_Group'])`), so it's not in the model features. But `predict.py` currently lists `history` in the subject grade columns — this will either be ignored or cause errors.

---

## Open Questions

> [!IMPORTANT]
> **Gemini Integration for Final Prediction**: Currently the Streamlit `app.py` uses Gemini to augment predictions. For the FastAPI+React version, should the `/predict` endpoint:
> - Option A: Return XGBoost result only, with a separate `/enhance` endpoint for Gemini?
> - Option B: Always call both XGBoost + Gemini in one `/predict` call?
> - **Recommended**: Option A — keeps ML and LLM concerns separate and makes the API faster for basic predictions.

> [!IMPORTANT]
> **Authentication**: The old `app.py` has SQLite-backed user auth with bcrypt. Should the FastAPI backend:
> - Keep the SQLite DB (`career_portal.db`) and port the auth logic?
> - Use a simpler token-based auth (JWT)?
> I'll implement JWT-based auth backed by the existing SQLite DB.

> [!NOTE]
> **Class-level subject filtering**: The project aims to show only the subjects relevant to a student's department (Science/Arts/Commercial). The current `predict.py` doesn't enforce this — it accepts all subjects. The FastAPI API will accept all and use defaults for irrelevant ones, but the React frontend will show only department-specific subjects.

---

## Proposed Changes

### Backend — FastAPI

---

#### [NEW] `backend/` directory

**Structure:**
```
backend/
├── main.py              ← FastAPI app entrypoint (CORS, router registration)
├── config.py            ← Settings (API key, model paths, DB path)
├── database.py          ← SQLite setup (users, predictions table)
├── auth.py              ← JWT auth utilities (login, register, token verify)
├── models/
│   ├── schemas.py       ← Pydantic request/response models
│   └── ml_model.py      ← XGBoost model loader + predict_career()
├── routers/
│   ├── auth_router.py   ← POST /auth/register, POST /auth/login
│   ├── predict_router.py ← POST /predict (XGBoost), POST /enhance (Gemini)
│   └── history_router.py ← GET /history (user prediction history)
└── requirements.txt     ← FastAPI, uvicorn, joblib, xgboost, etc.
```

#### [MODIFY] `machine-learning/predict.py`
- Fix wrong label encoder path (`model_artifacts` → `models`)
- Remove `history` from grade columns (it was dropped during training)
- Fix grade mapping: the pipeline already contains OrdinalEncoder for categorical cols — the manual grade→int mapping needs to stay since that's how the model was trained (grades mapped to numeric before the pipeline's StandardScaler/OrdinalEncoder)

---

### Frontend — React

---

#### [NEW] `frontend/` directory

**Stack:** Vite + React + TypeScript

**Key pages/components:**
- `Login` / `Register` pages
- `Dashboard` — student selects class level + department, enters grades/test scores
- `PredictionResult` — shows XGBoost prediction + Gemini-enhanced narrative
- `History` — past predictions for logged-in user

**Department-based subject filtering:**
- **Science**: Math, English, Civic Ed, Physics, Chemistry, Biology, Further Math, Agric Science, Geography, Technical Drawing, Computer Studies
- **Arts**: Math, English, Civic Ed, Yoruba/Igbo/Hausa, Literature in English, CRS/IRS, Creative Arts, Government, History (not in model, will be skipped)
- **Commercial**: Math, English, Civic Ed, Economics, Financial Accounting, Commerce, Government, Marketing, Data Processing

---

## Verification Plan

### Automated Tests
```bash
# Start FastAPI server
cd backend && uvicorn main:app --reload

# Test prediction endpoint
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"department":"Science","mathematics":"A","english":"B",...}'
```

### Manual Verification
1. Register a new user via React UI
2. Log in and submit a prediction form (Science department)
3. Verify XGBoost result appears, then Gemini narrative loads
4. Check prediction appears in History tab
