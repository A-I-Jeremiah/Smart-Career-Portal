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
graph TB
    subgraph "Frontend Layer"
        React[React / Vite Web App<br/>Main Production Frontend]
        Streamlit[Streamlit Dashboard<br/>Mock / Testing App]
    end

    subgraph "Backend Layer"
        FastAPI[FastAPI REST API Server<br/>Core Business Logic]
        SQLite[SQLite Database<br/>Users, Results, Tests, Recommendations, Chat]
        ML[XGBoost ML Models<br/>Career Prediction]
        Gemini[Google Gemini API<br/>Narrative & AI Chat]
    end

    subgraph "External Services"
        Render[Render.com<br/>Hosting FastAPI]
        StreamlitCloud[Streamlit Cloud<br/>Hosting Mock App]
    end

    React -->|JWT Auth + REST API Calls| FastAPI
    Streamlit -->|REST API Calls / Local ML| FastAPI
    Streamlit -.->|Testing Only| FastAPI

    FastAPI -->|Persistence| SQLite
    FastAPI -->|ML Inference| ML
    FastAPI -->|Narrative Generation & Chat| Gemini

    style React fill:#e3f2fd,stroke:#1565c0,stroke-width:3px
    style Streamlit fill:#f1f8e9,stroke:#689f38,stroke-width:2px,stroke-dasharray: 5 5
    style FastAPI fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    style SQLite fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
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
erDiagram
    USER {
        int id PK
        string full_name
        date dob
        string class_level
        string department
        string email UK
        string password
    }

    ACADEMIC_RESULT {
        int id PK
        int user_id FK
        string result_type
        string subject
        float score
        date exam_date
        datetime uploaded_at
    }

    TEST_RESPONSE {
        int id PK
        int user_id FK
        string test_type
        string question_id
        string answer
        float score
        datetime submitted_at
    }

    RECOMMENDATION {
        int id PK
        int user_id FK
        string career_path
        float confidence
        json universities
        json linkedin_mentors
        text narrative
        json top3
        datetime generated_at
    }

    CHAT_HISTORY {
        int id PK
        int user_id FK
        string role
        text message
        datetime created_at
    }

    USER ||--o{ ACADEMIC_RESULT : "has"
    USER ||--o{ TEST_RESPONSE : "submits"
    USER ||--o{ RECOMMENDATION : "receives"
    USER ||--o{ CHAT_HISTORY : "participates in"
```
## Data Flow Diagram - Recommendation Generation & Conversation Chat Flow

```mermaid
flowchart TD
    subgraph User Interaction
        Student[Student User]
    end

    subgraph Frontend
        React[React Web App]
        Streamlit[Streamlit Mock App]
    end

    subgraph Backend
        FastAPI[FastAPI REST API]
        Auth[Authentication Service]
        DB[(SQLite Database)]
        ML[XGBoost ML Model]
        Gemini[Google Gemini API]
    end

    %% Recommendation Generation Flow
    Student -->|1. Submit Grades + Tests| React
    React -->|2. POST /predict/ml| FastAPI
    FastAPI -->|3. Validate JWT| Auth
    FastAPI -->|4. Load Academic + Test Data| DB
    FastAPI -->|5. Run Career Prediction| ML
    ML -->|6. Return Top Careers| FastAPI
    FastAPI -->|7. Build Prompt| Gemini
    Gemini -->|8. Generate Narrative| FastAPI
    FastAPI -->|9. Save Recommendation| DB
    FastAPI -->|10. Return Full Report| React
    React -->|11. Display Report| Student

    %% Conversation Chat Flow
    Student -->|A. Send Question| React
    React -->|B. POST /chat| FastAPI
    FastAPI -->|C. Load Context| DB
    FastAPI -->|D. Build Context Prompt| Gemini
    Gemini -->|E. Generate Reply| FastAPI
    FastAPI -->|F. Save Chat History| DB
    FastAPI -->|G. Return Reply| React
    React -->|H. Display Response| Student

    style React fill:#e3f2fd,stroke:#1565c0
    style FastAPI fill:#f3e5f5,stroke:#7b1fa2
    style ML fill:#e8f5e9,stroke:#388e3c
    style Gemini fill:#fff3e0,stroke:#f57c00
    style DB fill:#fce4ec,stroke:#c2185b
```

## Workflow Diagrams - Student Recommendation Workflow & Backend Request lIfecycle

```mermaid
flowchart TD
    subgraph "Student Recommendation Workflow"
        A[Start] --> B[Register / Login]
        B --> C[Enter Current Subject Grades]
        C --> D[Complete All 4 Diagnostic Tests]
        D --> E[Click Generate Recommendation]
        E --> F[View Personalized Career Report]
        F --> G[Explore Universities & Mentors]
        G --> H[Chat with AI Counsellor]
        H --> I[End Session]
    end

    subgraph "Backend Request Lifecycle"
        direction TB
        Request[Incoming Request] --> Auth[JWT Authentication]
        Auth -->|Valid| Router[Router Handler]
        Router -->|Grades / Tests| DB[SQLite Database]
        Router -->|Prediction| ML[XGBoost ML Model]
        Router -->|Narrative| Gemini[Google Gemini API]
        ML --> FastAPI[FastAPI Response Builder]
        Gemini --> FastAPI
        DB --> FastAPI
        FastAPI --> Response[Return JSON Response]
    end

    style A fill:#e3f2fd,stroke:#1565c0
    style E fill:#f3e5f5,stroke:#7b1fa2
    style ML fill:#e8f5e9,stroke:#388e3c
    style Gemini fill:#fff3e0,stroke:#f57c00
```

## Model Performance Metrics and Evaluation

The career path recommendation engine was evaluated using multiple machine learning classification models in `new_model.ipynb`. The models were evaluated on key classification metrics including **Accuracy**, **Precision**, **Recall**, and **F1-Score**, as well as Stratified 5-Fold Cross-Validation.

### Summary of Model Performance

| Model | Train Accuracy | Test Accuracy | Precision (Macro Avg) | Recall (Macro Avg) | F1-Score (Macro Avg) | Stratified 5-Fold CV |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Random Forest (Baseline)** | 99.07% | 86.59% | 0.9 (90%) | 0.87 (87%) | 0.88 (88%) | 85.71% ± 1.90% |
| **XGBoost Classifier (Primary)** | 100.00% | 84.15% | 0.89 (89%) | 0.86 (86%) | 0.86 (86%) | — |
| **Tuned XGBoost Classifier** | 98.46% | 85.37% | 0.9 (90%) | 0.85 (85%) | 0.87 (87%) | 88.17% ± 3.30% |

### Key Metric Details
- **Accuracy**: Achieved **86.59%** test for accuracy Random Forest and **85.37%** test accuracy for XGBoost (Tuned) architectures.
- **Precision**: XGBoost (Tuned) achieved **0.85** in macro average across all target career classes.
- **Recall**: XGBoost (Tuned) achieved **0.85** in macro average across all target career classes.
- **F1-Score**: Macro average of **0.86** (86%) for all career classifications.
- **Cross-Validation**: 5-Fold Stratified Cross-Validation confirmed robust generalization with **85.71% ± 1.90%** for Random Forest and **88.17% ± 3.30%** for Tuned XGBoost.

## Backend Test Suite Results

A comprehensive pytest suite (`backend/models/test_backend.py`) covering all major backend components was written and executed on the local environment:

### Command Run
```bash
python -m pytest backend/models/test_backend.py -v --tb=short
```

### Test Run Output
```
platform win32 -- Python 3.11.14, pytest-8.4.2, pluggy-1.5.0
plugins: anyio-4.14.1

collected 21 items

backend/models/test_backend.py::test_root_health_check                    PASSED  [  4%]
backend/models/test_backend.py::test_health_check_endpoint                PASSED  [  9%]
backend/models/test_backend.py::test_ml_model_prediction_science          PASSED  [ 14%]
backend/models/test_backend.py::test_ml_model_prediction_arts             PASSED  [ 19%]
backend/models/test_backend.py::test_ml_model_prediction_commercial       PASSED  [ 23%]
backend/models/test_backend.py::test_ml_model_f_grade_blocking            PASSED  [ 28%]
backend/models/test_backend.py::test_department_filter_alignment          PASSED  [ 33%]
backend/models/test_backend.py::test_auth_register_success                PASSED  [ 38%]
backend/models/test_backend.py::test_auth_register_duplicate_email        PASSED  [ 42%]
backend/models/test_backend.py::test_auth_register_missing_department_sss PASSED  [ 47%]
backend/models/test_backend.py::test_auth_login_success                   PASSED  [ 52%]
backend/models/test_backend.py::test_auth_login_invalid_password          PASSED  [ 57%]
backend/models/test_backend.py::test_auth_change_password                 PASSED  [ 61%]
backend/models/test_backend.py::test_academic_results_crud                PASSED  [ 66%]
backend/models/test_backend.py::test_get_test_questions_all_categories    PASSED  [ 71%]
backend/models/test_backend.py::test_submit_test_responses                PASSED  [ 76%]
backend/models/test_backend.py::test_public_ml_predict                    PASSED  [ 80%]
backend/models/test_backend.py::test_full_predict_authenticated           PASSED  [ 85%]
backend/models/test_backend.py::test_get_saved_recommendation_and_chat   PASSED  [ 90%]
backend/models/test_backend.py::test_ml_model_latency_performance         PASSED  [ 95%]
backend/models/test_backend.py::test_api_endpoint_throughput_performance  PASSED  [100%]

================== 21 passed, 3 warnings in 70.34s (0:01:10) ==================
```

### Results Summary

| Metric | Value |
| :--- | :---: |
| **Total Tests** | 21 |
| **Passed** | 21 |
| **Failed** | 0 |
| **Pass Rate** | 100% |
| **Duration** | 70.34s |
| **Python Version** | 3.11.14 |
| **pytest Version** | 8.4.2 |

### Test Coverage

| # | Test Name | Area | Description |
| :---: | :--- | :--- | :--- |
| 1 | `test_root_health_check` | System Health | Verifies root endpoint returns `status: ok` and correct API version |
| 2 | `test_health_check_endpoint` | System Health | Validates `/health` returns `healthy` status |
| 3 | `test_ml_model_prediction_science` | ML Model | XGBoost returns valid career, confidence, and top-3 for Science dept |
| 4 | `test_ml_model_prediction_arts` | ML Model | XGBoost returns valid career predictions for Arts dept |
| 5 | `test_ml_model_prediction_commercial` | ML Model | XGBoost returns valid career predictions for Commercial dept |
| 6 | `test_ml_model_f_grade_blocking` | ML Model | Model correctly blocks recommendations when student has F in Maths |
| 7 | `test_department_filter_alignment` | Department Filter | `normalize_department()` correctly maps aliases and invalid inputs |
| 8 | `test_auth_register_success` | Authentication | New user registration returns HTTP 201 |
| 9 | `test_auth_register_duplicate_email` | Authentication | Duplicate email registration returns HTTP 409 |
| 10 | `test_auth_register_missing_department_sss` | Authentication | SSS student missing department returns HTTP 422 |
| 11 | `test_auth_login_success` | Authentication | Valid credentials return JWT token and user profile |
| 12 | `test_auth_login_invalid_password` | Authentication | Wrong password returns HTTP 401 Unauthorized |
| 13 | `test_auth_change_password` | Authentication | Password change succeeds and new credentials work |
| 14 | `test_academic_results_crud` | Academic Results | Full create, read, delete lifecycle for academic results |
| 15 | `test_get_test_questions_all_categories` | Diagnostic Tests | All 4 test categories return exactly 10 valid questions each |
| 16 | `test_submit_test_responses` | Diagnostic Tests | Test submission, score generation, status check, and retake work |
| 17 | `test_public_ml_predict` | Prediction API | Public `/predict/ml` endpoint returns correct prediction structure |
| 18 | `test_full_predict_authenticated` | Prediction API | Authenticated `/predict/` returns career, confidence, top-3, unis, mentors, narrative |
| 19 | `test_get_saved_recommendation_and_chat` | History & Chat | Recommendation persists after prediction; chat history starts empty |
| 20 | `test_ml_model_latency_performance` | Performance | ML inference averages within acceptable latency bounds (10 runs) |
| 21 | `test_api_endpoint_throughput_performance` | Performance | API endpoint averages within acceptable latency bounds (10 runs) |

---


## Deployment Notes
> **Deployment Note:** The production **frontend application** (React/Vite) is deployed and hosted on **Vercel**, while the **backend REST API service** (FastAPI) is deployed and hosted on **Render**.

- `render.yaml` defines Render services:
  - `career-fastapi`: backend Python service deployed on Render.
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
## Deployment Architecture

```mermaid
graph LR
    subgraph Render
        FastAPI[FastAPI Service]
    end
    subgraph Vercel
        Frontend[Vite/React Frontend]
    end
    Docker[Docker Image] --> FastAPI
    Frontend --> FastAPI
```

### Backend (Render)

- Deployed on Render using `render.yaml` which defines three services:
  - `career-fastapi`: Python FastAPI app container.
  - `career-streamlit`: Streamlit app container.
  - `career-react`: static frontend build on Vite.

### Frontend (Vercel)

- The React/Vite app is built and deployed to Vercel.
- Vercel handles CI/CD on push to `main`, runs `npm install && npm run build` and serves the static files.

### Docker Imaging

- `Dockerfile` builds an image for the Streamlit app.
- Multi‑stage build could be used for FastAPI as well (optional).

## Methodology & Implementation

- **Backend**: FastAPI with JWT authentication, SQLite database, XGBoost ML models, and Google Gemini API integration for narrative generation.
- **Frontend**: React with Vite, Axios for API calls, JWT stored in `localStorage`.
- **Streamlit**: Alternative UI that can load models locally or call the FastAPI backend.
- **Data**: SQLite schema stores users, academic results, test responses, recommendations, and chat history.
- **Machine Learning**: XGBoost model trained on historical student data, using a label encoder for categorical features.
- **AI**: Google Gemini used for narrative generation and conversational counselling.
- **Testing**: Unit tests for routers, model inference, and API endpoints (if present).

## Future Work

- Migrate SQLite to PostgreSQL for better scalability and concurrency handling.
- Add CI pipelines with GitHub Actions for linting, testing, and Docker image publishing.
- Expand AI capabilities with function calling for structured recommendations and richer chat interactions.

## Links To Frontend And Backend Deploments
- [Streamlit](https://smart-career-app.streamlit.app/)
- [Backend-FastAPI](https://smart-career-app-4702.onrender.com)
- [Frontend-UI](https://smart-career-portal.vercel.app/)
