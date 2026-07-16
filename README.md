# Smart Career Portal

## Project Summary
Smart Career Portal is a Nigerian student career guidance platform built as a multi-frontend system:
- `backend/`: FastAPI REST API with JWT authentication, machine learning inference, recommendation persistence and chat history.
- `app.py`: A Streamlit dashboard that can run independently or integrate with the backend API. It includes local user authentication, grade and test capture, local ML inference, Gemini narrative generation and chatbot interaction.
- `frontend/`: A React/Vite web portal that consumes the backend API for auth, academic records, test management, recommendation generation, and conversational follow-up.

The system is powered by:
- SQLite as the primary persistence layer (`career_portal.db`).
- XGBoost-based career recommendation ML artifacts in `backend/models/`.
- Google Gemini via `google-genai` for narrative generation and AI counselling.

## System Architecture
The platform is built as a service-oriented architecture with separate user-facing UI layers and a shared backend.

```mermaid
graph LR
    React[React/Vite Web App]
    Streamlit[Streamlit Dashboard]
    FastAPI[FastAPI API Server]
    SQLite[SQLite Database]
    XGBoostModel[ML Artifacts (xgb_best_model.pkl, label_encoder.pkl)]
    Gemini[Google Gemini API]
    MLLocal[Local Streamlit ML Models]

    React -->|REST API calls| FastAPI
    Streamlit -->|Optional /predict/ml| FastAPI
    FastAPI -->|reads/writes| SQLite
    FastAPI -->|loads| XGBoostModel
    FastAPI -->|calls| Gemini
    Streamlit -->|local DB| SQLite
    Streamlit -->|local ML inference| MLLocal
    Streamlit -->|Gemini API| Gemini
```
## Core Components

### Backend (`backend/`)
- `backend/main.py`: FastAPI app entrypoint, registers routers, and initializes SQLite.
- `backend/auth.py`: JWT issuance, password hashing, token validation, and current-user dependency.
- `backend/database.py`: SQLite schema and persistence for users, test responses, academic results, recommendations, and chat.
- `backend/routers/`: API endpoint definitions.
  - `auth_router.py`: registration, login, and password change.
  - `predict_router.py`: combined ML + Gemini recommendation endpoint and a public ML-only endpoint.
  - `results_router.py`: academic result CRUD.
  - `tests_router.py`: dynamic assessment questions, scoring, and saved results.
  - `history_router.py`: recommendation retrieval, chat history, and Gemini-powered follow-up chat.
- `backend/models/ml_model.py`: XGBoost-based prediction logic with ensemble, fallback heuristics, and lazy model loading.
- `backend/config.py`: environment and artifact paths.

### Streamlit App (`app.py`)
- Provides an alternative UI with local login, student dashboard, grade entry, test completion, recommendation generation, and chat.
- Can run predictions locally against models in `ml/models` or call the backend API if `FASTAPI_BASE_URL` is configured.
- Reads question bank from `backend/questions_engine/assessment_questions.json` and stores app state in `Streamlit` session state.

### React Frontend (`frontend/`)
- Uses JWT-authenticated REST calls to FastAPI.
- Stores auth token and user profile in browser `localStorage`.
- Key pages: `Dashboard`, `Grades`, `Tests`, `Recommendations`, `Profile`, `Auth`.
- Uses shared utility mapping in `frontend/src/utils/subjectMapper.js` to translate grade rows into backend prediction payloads.

## Use Case Diagram

```mermaid
graph TB
  Student([Student])
  System([System])

  Student --> Register[Register Account]
  Student --> Login[Login]
  Student --> UploadGrades[Upload Academic Grades]
  Student --> CompleteTests[Complete Diagnostic Tests]
  Student --> GenerateRecommendation[Generate Career Recommendation]
  Student --> ViewReport[View Recommendation Report]
  Student --> Chat[Chat with AI Career Counsellor]
  Student --> ManageProfile[Manage Profile]

  System --> Validate[Validate Credentials]
  System --> Persist[Persist Academic Records]
  System --> Score[Score Tests]
  System --> Infer[Run ML Inference]
  System --> Narrative[Generate Narrative]
  System --> Save[Save Recommendation]
  System --> Respond[Return Chat Response]
```
## Entity-Relationship Diagram

```mermaid
graph TB
    Users[Users]
    AcademicResults[Academic Results]
    TestResponses[Test Responses]
    Recommendations[Recommendations]
    ChatHistory[Chat History]

    Users -->|owns| AcademicResults
    Users -->|submits| TestResponses
    Users -->|receives| Recommendations
    Users -->|records| ChatHistory
```
## Data Flow Diagrams

### Recommendation Generation Flow

```mermaid
flowchart TD
    User[Student] -->|submits grades/tests| Frontend[React or Streamlit UI]
    Frontend -->|POST /predict/| FastAPI
    FastAPI -->|validate JWT| Auth[Auth Middleware]
    FastAPI -->|load payload| ML[run_xgboost prediction]
    ML -->|predict career & top-3| FastAPI
    FastAPI -->|build Gemini prompt| Gemini[Google Gemini]
    Gemini -->|narrative text| FastAPI
    FastAPI -->|save recommendation| SQLite[SQLite DB]
    FastAPI -->|return recommendation| Frontend
    Frontend -->|render| User
```

### Conversation Chat Flow

```mermaid
flowchart LR
    User -->|sends message| ChatUI[Frontend Chat Component]
    ChatUI -->|POST /history/chat| FastAPI
    FastAPI -->|load latest recommendation| SQLite
    FastAPI -->|load recent chat history| SQLite
    FastAPI -->|construct system prompt| Gemini
    Gemini -->|assistant reply| FastAPI
    FastAPI -->|store user & reply| SQLite
    FastAPI -->|return assistant message| ChatUI
    ChatUI -->|display| User
```

## Workflow Diagrams

### Student Recommendation Workflow

```mermaid
flowchart LR
    A[Start] --> B[Register / Login]
    B --> C[Enter Current Grades]
    C --> D[Complete All 4 Diagnostic Tests]
    D --> E[Generate Career Recommendation]
    E --> F[View Career Report, Universities & Mentors]
    F --> G[Ask Follow-up Career Questions via Chat]
    G --> H[End]
```

### Backend Request Lifecycle

```mermaid
flowchart TD
    Request[/predict/, /history/recommendation, /tests/, /results/] --> Auth[JWT & User Lookup]
    Auth -->|valid| Router[Router Handler]
    Router -->|predict| MLInference[ML model or fallback]
    Router -->|history|getRecommendation[DB lookup]
    Router -->|chat| Gemini[External AI service]
    Router --> DB[SQLite persistence]
    DB --> Router
    Router --> Response[HTTP Response]
    Response --> Request
```

## Deployment Notes
- `render.yaml` defines three Render services:
  - `career-fastapi`: backend Python service.
  - `career-streamlit`: Streamlit app service.
  - `career-react`: static frontend build on Vite.
- `Dockerfile` targets the Streamlit app.
- `requirements.txt` includes both backend and Streamlit dependencies.

## Important Observations
- The backend uses a shared database schema with the Streamlit app, but the two user-facing apps can operate independently.
- Backend ML inference is based on `backend/models/xgb_best_model.pkl` and `backend/models/label_encoder.pkl`.
- Recommendation persistence stores complex objects as JSON strings in SQLite columns.
- The `history` routes are designed to combine saved recommendations and Gemini responses into a conversational follow-up experience.
- The frontend uses Axios interceptors to automatically attach JWTs and handle unauthorized state transitions.

## Code Locations
- API: `backend/main.py`
- Authentication: `backend/routers/auth_router.py`
- Prediction: `backend/routers/predict_router.py`
- Chat + history: `backend/routers/history_router.py`
- Test engine: `backend/routers/tests_router.py`
- Academic results: `backend/routers/results_router.py`
- ML model logic: `backend/models/ml_model.py`
- Streamlit UI: `app.py`
- React UI: `frontend/src/App.jsx`
- Frontend API client: `frontend/src/utils/api.js`
- Prediction payload builder: `frontend/src/utils/subjectMapper.js`
