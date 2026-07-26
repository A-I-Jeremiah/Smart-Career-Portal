import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { Award, CheckCircle, ChevronLeft, ChevronRight, HelpCircle, RefreshCw, Play } from 'lucide-react';

const TEST_META = [
  { key: 'cognitive', icon: '🧩', label: 'Cognitive Test', desc: 'Measures logical reasoning, sequence completion, and mathematical logic.' },
  { key: 'aptitude', icon: '🎯', label: 'Aptitude Test', desc: 'Identifies natural talents and suitability for different academic paths.' },
  { key: 'psychometric', icon: '🧠', label: 'Psychometric Test', desc: 'Analyzes personality traits, work preferences, and behavioral styles.' },
  { key: 'sentiment', icon: '💬', label: 'Sentiment Test', desc: 'Evaluates your interest, academic motivations, and emotional readiness.' }
];

const Tests = () => {
  const { user } = useAuth();
  const [completedList, setCompletedList] = useState([]);
  const [scores, setScores] = useState({});
  const [loading, setLoading] = useState(true);
  
  // Active test execution states
  const [activeTest, setActiveTest] = useState(null); // 'cognitive', 'aptitude', etc.
  const [questions, setQuestions] = useState([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [answers, setAnswers] = useState({}); // { question_id: selected_option_text }
  const [submitting, setSubmitting] = useState(false);
  const [testError, setTestError] = useState('');

  const fetchStatus = async () => {
    try {
      const response = await api.get('/tests/');
      setCompletedList(response.data.completed || []);
      setScores(response.data.scores || {});
      setLoading(false);
    } catch (err) {
      console.error('Error fetching test status:', err);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const startTest = async (testKey) => {
    setLoading(true);
    setTestError('');
    try {
      const response = await api.get(`/tests/${testKey}/questions`);
      // Sanitize, dedupe and randomize questions & options to ensure dynamic unique deliveries
      // Remove question identifiers like "Q17", "Q17:", leading or trailing,
      // and any common variations. Also normalize whitespace.
      const sanitizeText = (t) => {
        let s = String(t || '').trim();
          // Remove patterns like "Q17:", "Q17 -", "Q17.", "(Q17)", "Question 17" etc.
        s = s.replace(/^\s*(?:Q|Question)\s*\d+\s*[:\-\.\)]?\s*/i, '');
        s = s.replace(/\s*[:\-\.\)]?\s*(?:Q|Question)\s*\d+\s*$/i, '');
        // Remove any remaining standalone Q<num> tokens anywhere
        s = s.replace(/\b(?:Q|Question)\s*\d+\b/ig, '');
        // Remove bracketed ids like (Q17) or [Q17]
        s = s.replace(/\([Qq]\s*\d+\)|\[[Qq]\s*\d+\]/g, '');
        return s.replace(/\s+/g, ' ').trim();
      };

      const fisherYates = (arr) => {
        const a = Array.isArray(arr) ? [...arr] : [];
        // Use crypto randomness when available for stronger shuffle variety across retakes
        const rand = (max) => {
          if (typeof window !== 'undefined' && window.crypto && window.crypto.getRandomValues) {
            const r = new Uint32Array(1);
            window.crypto.getRandomValues(r);
            return r[0] % max;
          }
          return Math.floor(Math.random() * max);
        };
        for (let i = a.length - 1; i > 0; i--) {
          const j = rand(i + 1);
          [a[i], a[j]] = [a[j], a[i]];
        }
        return a;
      };

      const raw = Array.isArray(response.data) ? response.data : [];
      const seenText = new Set();
      const seenId = new Set();
      const processed = [];
 
      raw.forEach((q) => {
        const text = sanitizeText(q.text || q.question || '');
        if (!text) return;
        // Deduplicate by sanitized text and by server-provided id to avoid duplicates
        if (seenText.has(text) || (q.id && seenId.has(q.id))) return;
        seenText.add(text);
        if (q.id) seenId.add(q.id);
 
        const opts = Array.isArray(q.options) ? q.options.map((o) => String(o).trim()) : [];
        // dedupe options
        const optSeen = new Set();
        const uniqOpts = opts.filter((o) => {
          if (optSeen.has(o)) return false;
          optSeen.add(o);
          return true;
        });
 
        // shuffle options for dynamic ordering
        const shuffledOpts = fisherYates(uniqOpts);
 
        processed.push({ ...q, text, options: shuffledOpts });
      });

      // shuffle the questions so each student gets a different order
      const shuffledQs = fisherYates(processed);

      setQuestions(shuffledQs);
      setCurrentIdx(0);
      setAnswers({});
      setActiveTest(testKey);
      setLoading(false);
    } catch (err) {
      console.error('Error loading questions:', err);
      setTestError('Failed to fetch test questions. Please check your network connection.');
      setLoading(false);
    }
  };

  const handleOptionSelect = (qId, optionText) => {
    setAnswers((prev) => ({
      ...prev,
      [qId]: optionText,
    }));
  };

  const scoreSuffix = (testKey) => (['aptitude', 'cognitive'].includes(testKey) ? '/10' : '/5');

  const handleNext = () => {
    if (currentIdx < questions.length - 1) {
      setCurrentIdx(currentIdx + 1);
    }
  };

  const handlePrev = () => {
    if (currentIdx > 0) {
      setCurrentIdx(currentIdx - 1);
    }
  };

  const handleSubmit = async () => {
    // Validate that all questions are answered
    const unanswered = questions.filter((q) => answers[q.id] === undefined);
    if (unanswered.length > 0) {
      alert(`Please answer all questions before submitting. (${unanswered.length} remaining)`);
      return;
    }

    setSubmitting(true);
    try {
      const response = await api.post('/tests/submit', {
        test_type: activeTest,
        answers: answers,
        department: user.department || 'Science',
      });
      
      alert(response.data.message || 'Test submitted successfully!');
      setActiveTest(null);
      setQuestions([]);
      fetchStatus();
    } catch (err) {
      console.error('Error submitting test:', err);
      alert('Failed to submit test. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRetake = async (testKey) => {
    if (!window.confirm(`Are you sure you want to clear your ${testKey} test score and retake it?`)) return;
    try {
      await api.delete(`/tests/${testKey}`);
      // Refresh server-side status before starting the retake to ensure the backend cleared previous responses
      await fetchStatus();
      await startTest(testKey);
    } catch (err) {
      console.error('Error resetting test:', err);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '300px' }}>
        <div className="spinner spinner-dark" style={{ width: '40px', height: '40px' }} />
      </div>
    );
  }

  // Render active test taking screen
  if (activeTest) {
    const meta = TEST_META.find((m) => m.key === activeTest);
    const progressPercent = ((currentIdx + 1) / questions.length) * 100;
    const currentQuestion = questions[currentIdx];
    const isLastQuestion = currentIdx === questions.length - 1;

    return (
      <div className="animate-fade-in" style={{ maxWidth: '800px', margin: '0 auto' }}>
        {/* Test Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div>
            <h2 className="page-title" style={{ fontSize: '1.75rem' }}>{meta.icon} {meta.label}</h2>
            <p className="page-subtitle">Question {currentIdx + 1} of {questions.length}</p>
          </div>
          <button className="btn btn-secondary" onClick={() => { setActiveTest(null); setQuestions([]); }} disabled={submitting}>
            Quit Test
          </button>
        </div>

        {/* Progress Bar */}
        <div style={{ marginBottom: '32px' }}>
          <div className="progress-bar-bg" style={{ height: '8px' }}>
            <div className="progress-bar-fill" style={{ width: `${progressPercent}%` }} />
          </div>
        </div>

        {/* Question Panel */}
        {currentQuestion && (
          <div style={{ background: 'var(--glass-bg)', borderRadius: '24px', padding: '32px', border: '1px solid var(--glass-border)', boxShadow: 'var(--shadow-md)', marginBottom: '24px' }}>
            <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--slate-50)', marginBottom: '24px', lineHeight: 1.5 }}>
              {currentQuestion.text}
            </div>

            {/* Options grid */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {currentQuestion.options.map((opt, oIdx) => {
                const isSelected = answers[currentQuestion.id] === opt;
                return (
                  <div
                    key={oIdx}
                    onClick={() => !submitting && handleOptionSelect(currentQuestion.id, opt)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '16px 20px',
                      borderRadius: '16px',
                      color: '#8897BD',
                      border: isSelected ? '2px solid #8897BD' : '1px solid rgba(136, 151, 189, 0.35)',
                      backgroundColor: isSelected ? 'rgba(136, 151, 189, 0.14)' : 'var(--glass-bg)',
                      cursor: submitting ? 'not-allowed' : 'pointer',
                      transition: 'var(--transition-fast)',
                      fontWeight: isSelected ? 700 : 500
                    }}
                  >
                    <div style={{
                      width: '20px',
                      height: '20px',
                      borderRadius: '50%',
                      border: isSelected ? '6px solid var(--primary-500)' : '2px solid var(--slate-400)',
                      marginRight: '16px',
                      backgroundColor: '#0AFFFF',
                      transition: 'var(--transition-fast)'
                    }} />
                    <span style={{ color: '#8897BD', fontSize: '0.98rem' }}>{opt}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Navigation Actions */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button
            className="btn btn-secondary"
            onClick={handlePrev}
            disabled={currentIdx === 0 || submitting}
            style={{ width: '120px' }}
          >
            <ChevronLeft size={18} /> Back
          </button>

          {isLastQuestion ? (
            <button
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={submitting || answers[currentQuestion.id] === undefined}
              style={{ width: '180px', backgroundColor: 'var(--emerald-600)' }}
            >
              {submitting ? <div className="spinner" /> : <><CheckCircle size={18} /> Submit Test</>}
            </button>
          ) : (
            <button
              className="btn btn-primary"
              onClick={handleNext}
              disabled={answers[currentQuestion.id] === undefined}
              style={{ width: '120px' }}
            >
              Next <ChevronRight size={18} />
            </button>
          )}
        </div>
      </div>
    );
  }

  // Otherwise, render main dashboard view of all tests
  const completedCount = completedList.length;
  const overallProgress = (completedCount / TEST_META.length) * 100;

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h2 className="page-title">🧠 Career Assessment Tests</h2>
        <p className="page-subtitle">Complete all four tests to generate your personalized career recommendation.</p>
      </div>

      {testError && (
        <div className="alert-banner alert-banner-warning">
          <span>⚠️ {testError}</span>
        </div>
      )}

      {/* Progress tracker */}
      <div className="test-progress-container">
        <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, fontSize: '0.95rem' }}>
          <span>Overall Diagnostic Progress</span>
          <span>{completedCount} / 4 Tests Completed</span>
        </div>
        <div className="progress-bar-bg">
          <div className="progress-bar-fill" style={{ width: `${overallProgress}%` }} />
        </div>
      </div>

      {completedCount === 4 && (
        <div className="alert-banner alert-banner-success" style={{ marginBottom: '32px' }}>
          <Award size={24} style={{ flexShrink: 0 }} />
          <div>
            <strong>Great job! All diagnostic assessments are complete.</strong>
            <p style={{ marginTop: '2px', fontSize: '0.9rem', opacity: 0.9 }}>
              Click on the <strong>My Recommendations</strong> tab to run the XGBoost prediction and explore your custom career paths.
            </p>
          </div>
        </div>
      )}

      {/* Grid of tests */}
      <div className="test-grid">
        {TEST_META.map((meta) => {
          const isDone = completedList.includes(meta.key);
          const score = scores[meta.key];
          
          return (
            <div key={meta.key} className="test-card">
              <span className="test-icon">{meta.icon}</span>
              <h3 className="test-name">{meta.label}</h3>
              <p className="test-desc">{meta.desc}</p>
              
              <span className={`test-badge ${isDone ? 'test-badge-completed' : 'test-badge-pending'}`}>
                {isDone ? '✅ Done' : '⏳ Pending'}
              </span>

              {isDone && score !== undefined && (
                <div style={{ fontSize: '0.85rem', color: 'var(--emerald-600)', fontWeight: 700, marginBottom: '16px' }}>
                  Score: {score}{scoreSuffix(meta.key)}
                </div>
              )}

              {isDone ? (
                <button
                  className="btn btn-secondary"
                  style={{ width: '100%', fontSize: '0.88rem' }}
                  onClick={() => handleRetake(meta.key)}
                >
                  <RefreshCw size={14} /> Retake Test
                </button>
              ) : (
                <button
                  className="btn btn-primary"
                  style={{ width: '100%', fontSize: '0.88rem' }}
                  onClick={() => startTest(meta.key)}
                >
                  <Play size={14} /> Start Test
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Tests;
