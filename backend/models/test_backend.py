# backend/models/test_backend.py
"""
Comprehensive pytest suite for Smart Career Portal backend.
Tests ML models, department filtering, authentication, database persistence,
diagnostic test engine, recommendation APIs, chat history, and latency performance.

Run with:
    python -m pytest backend/models/test_backend.py -v --tb=short
"""

import time
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend import database as db
from backend.models.ml_model import run_xgboost
from backend.models.department_filter import (
    normalize_department,
    apply_department_alignment,
    filter_careers_for_department,
)

client = TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensure database schema is initialized before every test."""
    db.init_db()


@pytest.fixture
def test_user_credentials():
    """Returns a unique email and password pair for testing."""
    timestamp = int(time.time() * 1000)
    return {
        "full_name": "Test Student",
        "dob": "2006-05-15",
        "class_level": "SSS 3",
        "department": "Science",
        "email": f"student_{timestamp}@example.com",
        "password": "SecurePassword123!",
    }


@pytest.fixture
def authenticated_client(test_user_credentials):
    """Creates a registered, logged-in test user and returns (client, token, user_data)."""
    reg_resp = client.post("/auth/register", json=test_user_credentials)
    assert reg_resp.status_code == 201

    login_resp = client.post(
        "/auth/login",
        json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"],
        },
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    token = data["access_token"]
    user_info = data["user"]

    auth_headers = {"Authorization": f"Bearer {token}"}
    return client, auth_headers, user_info


# ── 1. System Health & Root API Tests ──────────────────────────────────────────

def test_root_health_check():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert "v2.0" in data.get("message", "")


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


# ── 2. ML Model & Department Filter Unit Tests ───────────────────────────────

def test_ml_model_prediction_science():
    payload = {
        "department": "Science",
        "mathematics": "A",
        "english": "B",
        "physics": "A",
        "chemistry": "B",
        "biology": "A",
        "further_mathematics": "B",
        "aptitude_score_10": 8,
        "cognitive_score_10": 9,
        "psychometric_avg_5": 4.2,
        "sentiment_avg_5": 4.5,
    }
    result = run_xgboost(payload)
    assert "predicted_career" in result
    assert "confidence_percent" in result
    assert isinstance(result["confidence_percent"], float)
    assert len(result["top_3"]) == 3
    assert result["predicted_career"] != "Unknown"


def test_ml_model_prediction_arts():
    payload = {
        "department": "Arts",
        "english": "A",
        "literature_in_english": "A",
        "government": "A",
        "economics": "B",
        "mathematics": "C",
        "aptitude_score_10": 7,
        "cognitive_score_10": 8,
    }
    result = run_xgboost(payload)
    assert "predicted_career" in result
    assert result["confidence_percent"] > 0
    assert len(result["top_3"]) == 3


def test_ml_model_prediction_commercial():
    payload = {
        "department": "Commercial",
        "mathematics": "B",
        "english": "B",
        "economics": "A",
        "financial_accounting": "A",
        "commerce": "A",
        "marketing": "B",
        "aptitude_score_10": 8,
    }
    result = run_xgboost(payload)
    assert "predicted_career" in result
    assert result["confidence_percent"] > 0
    assert len(result["top_3"]) == 3


def test_ml_model_f_grade_blocking():
    payload = {
        "department": "Science",
        "mathematics": "F",
        "english": "A",
        "physics": "A",
    }
    result = run_xgboost(payload)
    assert "None — improve Mathematics and English" in result["predicted_career"]
    assert result["confidence_percent"] == 0.0
    assert "warning" in result


def test_department_filter_alignment():
    assert normalize_department("science") == "Science"
    assert normalize_department("ARTS") == "Arts"
    assert normalize_department("commercial") == "Commercial"
    assert normalize_department(None) == "Unknown"

    allowed_sci = filter_careers_for_department(
        ["Medicine & Health Sciences", "Law & Social Sciences"], "Science"
    )
    assert "Medicine & Health Sciences" in allowed_sci

    # Test alignment calculation with raw probabilities
    class_labels = ["Medicine & Health Sciences", "Law & Social Sciences", "Business & Finance"]
    raw_probs = [0.4, 0.5, 0.1]
    aligned = apply_department_alignment(raw_probs, class_labels, "Science")
    assert len(aligned.adjusted_proba) == 3


# ── 3. Authentication Router Tests (/auth) ───────────────────────────────────

def test_auth_register_success(test_user_credentials):
    res = client.post("/auth/register", json=test_user_credentials)
    assert res.status_code == 201
    assert res.json()["message"] == "Account created successfully. Please log in."


def test_auth_register_duplicate_email(test_user_credentials):
    res1 = client.post("/auth/register", json=test_user_credentials)
    assert res1.status_code == 201

    res2 = client.post("/auth/register", json=test_user_credentials)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


def test_auth_register_missing_department_sss():
    payload = {
        "full_name": "No Dept Student",
        "dob": "2007-01-01",
        "class_level": "SSS 2",
        "email": "nodept@example.com",
        "password": "Password123!",
    }
    res = client.post("/auth/register", json=payload)
    assert res.status_code == 422
    assert "Department is required" in res.json()["detail"]


def test_auth_login_success(test_user_credentials):
    client.post("/auth/register", json=test_user_credentials)
    login_res = client.post(
        "/auth/login",
        json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"],
        },
    )
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["user"]["email"] == test_user_credentials["email"]


def test_auth_login_invalid_password(test_user_credentials):
    client.post("/auth/register", json=test_user_credentials)
    login_res = client.post(
        "/auth/login",
        json={
            "email": test_user_credentials["email"],
            "password": "WrongPassword123!",
        },
    )
    assert login_res.status_code == 401


def test_auth_change_password(authenticated_client, test_user_credentials):
    cli, headers, _ = authenticated_client
    change_res = cli.post(
        "/auth/user/change-password",
        headers=headers,
        json={
            "old_password": test_user_credentials["password"],
            "new_password": "NewSecurePassword456!",
        },
    )
    assert change_res.status_code == 200
    assert change_res.json()["message"] == "Password updated successfully."

    # Login with new password should succeed
    login_res = cli.post(
        "/auth/login",
        json={
            "email": test_user_credentials["email"],
            "password": "NewSecurePassword456!",
        },
    )
    assert login_res.status_code == 200


# ── 4. Academic Results Router Tests (/results) ──────────────────────────────

def test_academic_results_crud(authenticated_client):
    cli, headers, _ = authenticated_client

    # Add result
    res_in = {
        "result_type": "WAEC",
        "subject": "Mathematics",
        "score": 85.0,
        "exam_date": "2024-06-01",
    }
    post_res = cli.post("/results/", headers=headers, json=res_in)
    assert post_res.status_code == 201
    inserted = post_res.json()
    assert inserted["subject"] == "Mathematics"
    assert inserted["score"] == 85.0

    # Fetch results
    get_res = cli.get("/results/", headers=headers)
    assert get_res.status_code == 200
    results_list = get_res.json()
    assert len(results_list) >= 1
    assert results_list[0]["subject"] == "Mathematics"

    # Delete result
    result_id = inserted["id"]
    del_res = cli.delete(f"/results/{result_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify deleted
    get_res_after = cli.get("/results/", headers=headers)
    assert len(get_res_after.json()) == 0


# ── 5. Diagnostic Tests Router Tests (/tests) ────────────────────────────────

def test_get_test_questions_all_categories(authenticated_client):
    cli, headers, _ = authenticated_client
    for test_type in ("aptitude", "cognitive", "psychometric", "sentiment"):
        res = cli.get(f"/tests/{test_type}/questions", headers=headers)
        assert res.status_code == 200
        questions = res.json()
        assert len(questions) == 10
        for q in questions:
            assert "id" in q
            assert "text" in q
            assert "options" in q
            assert len(q["options"]) > 0


def test_submit_test_responses(authenticated_client):
    cli, headers, _ = authenticated_client
    # Get questions first
    q_res = cli.get("/tests/aptitude/questions", headers=headers)
    questions = q_res.json()

    answers = {q["id"]: q["options"][0] for q in questions}
    submit_payload = {"test_type": "aptitude", "answers": answers}

    sub_res = cli.post("/tests/submit", headers=headers, json=submit_payload)
    assert sub_res.status_code == 200
    data = sub_res.json()
    assert data["test_type"] == "aptitude"
    assert "score" in data

    # Check status
    status_res = cli.get("/tests/", headers=headers)
    assert status_res.status_code == 200
    completed = status_res.json()["completed"]
    assert "aptitude" in completed

    # Retake test
    retake_res = cli.delete("/tests/aptitude", headers=headers)
    assert retake_res.status_code == 204


# ── 6. Prediction Router Tests (/predict) ─────────────────────────────────────

def test_public_ml_predict():
    payload = {
        "department": "Science",
        "mathematics": "A",
        "english": "A",
        "physics": "B",
        "chemistry": "A",
        "biology": "B",
        "aptitude_score_10": 9,
        "cognitive_score_10": 8,
    }
    res = client.post("/predict/ml", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "predicted_career" in data
    assert "confidence_percent" in data
    assert len(data["top_3"]) == 3


def test_full_predict_authenticated(authenticated_client):
    cli, headers, _ = authenticated_client
    payload = {
        "department": "Science",
        "mathematics": "A",
        "english": "A",
        "physics": "A",
        "chemistry": "B",
        "biology": "B",
        "aptitude_score_10": 9,
        "cognitive_score_10": 8,
        "psychometric_avg_5": 4.5,
        "sentiment_avg_5": 4.0,
    }
    res = cli.post("/predict/", headers=headers, json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "predicted_career" in data
    assert "confidence_percent" in data
    assert "top_3" in data
    assert "universities" in data
    assert "mentors" in data
    assert "narrative" in data


# ── 7. History & Chat Router Tests (/history) ─────────────────────────────────

def test_get_saved_recommendation_and_chat(authenticated_client):
    cli, headers, _ = authenticated_client

    # Before prediction, recommendation should 404
    rec_before = cli.get("/history/recommendation", headers=headers)
    assert rec_before.status_code == 404

    # Run prediction to save recommendation
    pred_payload = {
        "department": "Science",
        "mathematics": "A",
        "english": "A",
        "physics": "B",
        "chemistry": "B",
    }
    cli.post("/predict/", headers=headers, json=pred_payload)

    # Now recommendation should succeed
    rec_after = cli.get("/history/recommendation", headers=headers)
    assert rec_after.status_code == 200
    assert "career_path" in rec_after.json()

    # Chat history should be initially empty
    chat_get = cli.get("/history/chat", headers=headers)
    assert chat_get.status_code == 200
    assert len(chat_get.json()) == 0

    # Clear chat
    clear_res = cli.delete("/history/chat", headers=headers)
    assert clear_res.status_code == 204


# ── 8. Performance & Latency Benchmarks ───────────────────────────────────────

def test_ml_model_latency_performance():
    """Benchmark raw ML inference latency across 10 runs."""
    payload = {
        "department": "Science",
        "mathematics": "A",
        "english": "B",
        "physics": "A",
        "chemistry": "B",
        "biology": "A",
        "aptitude_score_10": 8,
        "cognitive_score_10": 9,
    }

    # Warmup
    run_xgboost(payload)

    iterations = 10
    start_time = time.perf_counter()
    for _ in range(iterations):
        res = run_xgboost(payload)
        assert res["predicted_career"] != "Unknown"
    end_time = time.perf_counter()

    total_duration = end_time - start_time
    avg_latency_ms = (total_duration / iterations) * 1000.0

    print(f"\n[PERFORMANCE] ML Model Inference: Total={total_duration:.3f}s, Avg={avg_latency_ms:.2f}ms/call")
    assert avg_latency_ms < 1500.0, f"ML latency too high: {avg_latency_ms:.2f}ms"


def test_api_endpoint_throughput_performance():
    """Benchmark FastAPI public endpoint throughput and response latency."""
    payload = {
        "department": "Engineering & Technology",
        "mathematics": "A",
        "english": "B",
        "physics": "A",
        "chemistry": "B",
    }

    iterations = 10
    start_time = time.perf_counter()
    for _ in range(iterations):
        res = client.post("/predict/ml", json=payload)
        assert res.status_code == 200
    end_time = time.perf_counter()

    total_duration = end_time - start_time
    avg_latency_ms = (total_duration / iterations) * 1000.0

    print(f"\n[PERFORMANCE] /predict/ml Endpoint: Total={total_duration:.3f}s, Avg={avg_latency_ms:.2f}ms/req")
    assert avg_latency_ms < 1500.0, f"API endpoint latency too high: {avg_latency_ms:.2f}ms"
