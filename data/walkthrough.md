# Walkthrough: Smart Career Portal React Migration & Backend Enhancements

We have successfully migrated the frontend of the **Smart Career Portal** from Streamlit to a modern, responsive, and aesthetically outstanding **React + Vite** single-page application. We also resolved a critical grading accuracy bug in the FastAPI backend tests router and updated the Docker container configurations.

---

## 🛠️ Changes Implemented

### 1. React Frontend Migration (`frontend/` directory)
* **Vite + React Setup**: Scaffolded a lightweight, blazing-fast React client in `frontend/`.
* **Design System & Theme (`index.css`)**: Established a premium styling framework using Slate and Indigo theme tokens, glassmorphism cards, micro-animations, clean inputs/selects, custom progress meters, and dynamic CSS flexbox/grid alignments.
* **Authentication Global Context (`AuthContext.jsx`)**: Added global state handling for JWT session tokens and student profile data.
* **Axios API Layer (`api.js`)**: Configured an Axios client pointing to `http://localhost:9000` with automatic authorization header injection.
* **Interactive Views**:
  * **Auth Page (`Auth.jsx`)**: Beautiful sliding tab layout supporting login and register with dynamic department displays for SSS students.
  * **Dashboard (`Dashboard.jsx`)**: Displays real-time completed counts, average academic score, journey map guidance blocks, and completion alert banners.
  * **Subject Grades (`Grades.jsx`)**: Manual grading form, active grade ledger table with delete capabilities, and an Excel/CSV drag-and-drop parser using SheetJS (`xlsx`).
  * **Take Tests (`Tests.jsx`)**: Shows all diagnostic assessments, score tracking, progress indicators, previous/next navigation, and response submission.
  * **Recommendations (`Recommendations.jsx`)**: Renders primary matched career paths, match confidence charts, recommended universities/locations, suggested LinkedIn mentors, and a conversational AI Guidance chatbot.

### 2. Backend Grading Fixes (`backend/routers/tests_router.py`)
* **Fixed Option Shuffling Bug**: Removed option shuffling (`rng.shuffle(options)`) from the questions fetcher endpoint. Keeping options in their static order preserves the correct index mappings for:
  * **Cognitive Tests**: Graded correctly against `COGNITIVE_ANSWERS`.
  * **Aptitude Tests**: Graded correctly using static `APTITUDE_WEIGHTS`.
  * **Psychometric & Sentiment Surveys**: Preserves the clean structural flow of Likert scale choices (e.g. *Strongly Agree* to *Strongly Disagree*).

### 3. Service Containerization & Deployments
* **Docker Compose Setup (`docker-compose.yml`)**: Integrated the new React frontend container (`career-react`), mapping container port `80` (served by Nginx) to host port `3000`.
* **Render One-Click Deployment (`render.yaml`)**: Added configuration for the React static site so the entire application can be hosted together.

---

## 🧪 Verification & How to Run

### Run Locally (Development Mode)

1. **Start the FastAPI Backend**:
   ```powershell
   # From the project root folder
   .venv\Scripts\activate
   uvicorn backend.main:app --reload --port 9000
   ```

2. **Start the React Frontend**:
   ```powershell
   # From the project root folder
   cd frontend
   npm run dev
   ```
   * Open your browser and navigate to `http://localhost:5173`.

---

## 🐳 Docker Deployment (Production Mode)

To run the entire ecosystem (FastAPI + Streamlit + React Client) inside Docker:

```bash
docker-compose up --build -d
```

* **FastAPI Backend URL**: `http://localhost:9000`
* **React Frontend URL**: `http://localhost:3000`
* **Streamlit Legacy URL**: `http://localhost:8501`
