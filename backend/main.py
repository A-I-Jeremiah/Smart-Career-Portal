# main.py  — FastAPI entrypoint (run from project root)
# Usage: uvicorn main:app --reload
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import auth_router, predict_router, results_router, tests_router, history_router
from backend.database import init_db

app = FastAPI(
    title="Smart Career Portal API",
    description="AI-powered career recommendation system for Nigerian secondary students",
    version="2.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
origins = [
    "http://localhost:5173",
    "https://smart-career-portal.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router.router)
app.include_router(predict_router.router)
app.include_router(results_router.router)
app.include_router(tests_router.router)
app.include_router(history_router.router)

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Smart Career Portal API v2.0 is running 🎓"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9000)