import React, { useState, useEffect, useLayoutEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { buildPredictPayload } from '../utils/subjectMapper';
import GeminiFormattedText from '../utils/formatGeminiText';
import { Award, Brain, Briefcase, GraduationCap, Users, MessageSquare, Send, Sparkles, AlertTriangle, BookOpen } from 'lucide-react';

const TEST_META = [
  { key: 'cognitive', label: 'Cognitive Test' },
  { key: 'aptitude', label: 'Aptitude Test' },
  { key: 'psychometric', label: 'Psychometric Test' },
  { key: 'sentiment', label: 'Sentiment Test' },
];

const normalizeRecommendation = (data) => {
  if (!data) return null;
  return {
    ...data,
    career_path: data.career_path || data.predicted_career || 'Career Pathway',
    confidence: data.confidence ?? data.confidence_percent ?? 0,
    top3: data.top3 || data.top_3 || [],
    generated_at: data.generated_at || new Date().toISOString(),
    narrative: data.narrative || '',
    universities: data.universities || [],
    mentors: data.mentors || [],
  };
};

const scoreLabel = (testKey, score) => {
  if (score === undefined || score === null || score === '') return '-';
  return `${score}${['aptitude', 'cognitive'].includes(testKey) ? '/10' : '/5'}`;
};

const Recommendations = () => {
  const { user } = useAuth();
  
  // Guard states
  const [loading, setLoading] = useState(true);
  const [completedList, setCompletedList] = useState([]);
  const [results, setResults] = useState([]);
  const [testScores, setTestScores] = useState({});

  // Recommendation details
  const [recommendation, setRecommendation] = useState(null);
  const [generating, setGenerating] = useState(false);

  // Chat states
  const [chatMessages, setChatMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [sendingMsg, setSendingMsg] = useState(false);
  const chatEndRef = useRef(null);

  const fetchGuardData = async () => {
    try {
      const [testsRes, resultsRes] = await Promise.all([
        api.get('/tests/'),
        api.get('/results/'),
      ]);

      const completed = testsRes.data.completed || [];
      const currentGrades = resultsRes.data.filter((r) => r.result_type === 'Current Grade');
      const scores = testsRes.data.scores || {};

      setCompletedList(completed);
      setResults(currentGrades);
      setTestScores(scores);

      // Try fetching existing recommendation
      try {
        const recRes = await api.get('/history/recommendation');
        setRecommendation(normalizeRecommendation(recRes.data));
        
        // If recommendation exists, fetch chat history
        const chatRes = await api.get('/history/chat');
        setChatMessages(chatRes.data || []);
      } catch (e) {
        // No recommendation found
        setRecommendation(null);
      }
      
      setLoading(false);
    } catch (err) {
      console.error('Error fetching recommendation dependencies:', err);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGuardData();
  }, []);

  // Track how many messages existed when we first loaded from the server
  const initialMsgCount = React.useRef(null);

  // Scroll to top immediately when component mounts using useLayoutEffect
  // This runs BEFORE the browser paints, ensuring top scroll happens first
  useLayoutEffect(() => {
    try {
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
      window.scrollTo(0, 0);
    } catch (e) {
      // ignore in environments without window
    }
  }, []);

  // Auto-scroll to new chat messages, but ONLY when user sends a new message
  // (not on the initial server load which would scroll the page to the bottom)
  useEffect(() => {
    // Record the initial count the first time chatMessages is populated from the server
    if (initialMsgCount.current === null) {
      initialMsgCount.current = chatMessages.length;
      return;
    }

    // Only scroll if messages grew beyond the initial server-loaded count
    if (chatMessages.length > initialMsgCount.current) {
      try {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      } catch (e) {
        // ignore environments without DOM
      }
    }
  }, [chatMessages]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const payload = buildPredictPayload(results, user.department, testScores);
      const response = await api.post('/predict/', payload);
      setRecommendation(normalizeRecommendation(response.data));
      
      // Refresh chat logs (should be cleared on backend)
      setChatMessages([]);
      alert('Your career pathway recommendations have been generated!');
    } catch (err) {
      console.error('Error generating recommendation:', err);
      alert('Failed to generate career recommendations. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!userInput.trim() || sendingMsg) return;

    const userText = userInput.trim();
    setUserInput('');
    setSendingMsg(true);

    // Optimistically add user bubble
    setChatMessages((prev) => [...prev, { role: 'user', message: userText }]);

    try {
      const response = await api.post('/history/chat', { message: userText });
      setChatMessages((prev) => [...prev, response.data]);
    } catch (err) {
      console.error('Error sending message:', err);
      const detail = err.response?.data?.detail;
      const message = typeof detail === 'string'
        ? detail
        : 'Sorry, I encountered an issue replying. Please try again shortly.';
      setChatMessages((prev) => [
        ...prev,
        { role: 'assistant', message },
      ]);
    } finally {
      setSendingMsg(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '300px' }}>
        <div className="spinner spinner-dark" style={{ width: '40px', height: '40px' }} />
      </div>
    );
  }

  // 1. Guard check: Must complete 4 tests
  if (completedList.length < 4) {
    const missing = TEST_META.filter((t) => !completedList.includes(t.key)).map((t) => t.label);
    return (
      <div className="animate-fade-in">
        <div className="page-header">
          <h2 className="page-title">Career Recommendations</h2>
        </div>
        <div className="alert-banner alert-banner-warning">
          <AlertTriangle size={24} style={{ flexShrink: 0 }} />
          <div>
            <strong>Assessment Incomplete</strong>
            <p style={{ marginTop: '2px', fontSize: '0.9rem', opacity: 0.9 }}>
              Please complete all 4 diagnostics before generating recommendations. Pending assessments: <strong>{missing.join(', ')}</strong>.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // 2. Guard check: Must enter at least one academic grade
  if (results.length === 0) {
    return (
      <div className="animate-fade-in">
        <div className="page-header">
          <h2 className="page-title">Career Recommendations</h2>
        </div>
        <div className="alert-banner alert-banner-warning">
          <AlertTriangle size={24} style={{ flexShrink: 0 }} />
          <div>
            <strong>No Grades Entered</strong>
            <p style={{ marginTop: '2px', fontSize: '0.9rem', opacity: 0.9 }}>
              Please add at least one subject grade under the <strong>Subject Grades</strong> tab to evaluate your academic performance.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h2 className="page-title">My Career Pathway Report</h2>
        <p className="page-subtitle">XGBoost Classifier + Gemini Generative Recommendations</p>
      </div>

      {generating && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', background: 'rgba(2, 6, 23, 0.7)', backdropFilter: 'blur(4px)', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', zIndex: 999, color: 'white' }}>
          <div className="spinner" style={{ width: '50px', height: '50px', borderWidth: '4px', marginBottom: '16px' }} />
          <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700 }}>AI Consultant is analyzing your scores...</h3>
          <p style={{ opacity: 0.8, fontSize: '0.9rem' }}>This may take up to 30 seconds</p>
        </div>
      )}

      {/* Trigger Predict Button */}
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '32px' }}>
        <button className="btn btn-primary" onClick={handleGenerate} style={{ padding: '14px 28px', fontSize: '1.05rem', boxShadow: 'var(--shadow-lg)' }}>
          <Sparkles size={20} /> {recommendation ? 'Regenerate Career Pathway' : 'Generate My Recommendation'}
        </button>
      </div>

      {recommendation ? (
        <>
          {/* Hero Recommendation Card */}
          <div className="rec-hero">
            <h1 style={{ display: 'flex', alignItems: 'center', gap: '12px' }}><Award size={28} style={{ color: 'var(--primary-500)' }} /> {recommendation.career_path}</h1>
            <p>
              Match Confidence: <strong>{recommendation.confidence}%</strong> &nbsp;|&nbsp; Generated on:{' '}
              {new Date(recommendation.generated_at).toLocaleDateString()} &nbsp;|&nbsp; Powered by Gemini AI
            </p>
          </div>

          {/* Scores Breakdown Grid */}
          <div className="rec-grid">
            {/* Top Matching List */}
            <div style={{ background: 'var(--glass-bg)', borderRadius: '24px', padding: '24px', border: '1px solid var(--glass-border)', boxShadow: 'var(--shadow-md)' }}>
              <h3 className="rec-card-title">Top Career Match Probabilities</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {[...(recommendation.top3 || [])]
                .sort((a, b) => {
                  const confA = typeof a === 'string' ? 0 : (a.confidence_percent ?? a[1] ?? 0);
                  const confB = typeof b === 'string' ? 0 : (b.confidence_percent ?? b[1] ?? 0);
                  return confB - confA;
                })
                .map((match, idx) => {
                  const careerName = typeof match === 'string' ? match : (match.career || match[0]);
                  const careerConf = typeof match === 'string' ? (idx === 0 ? recommendation.confidence : 10) : (match.confidence_percent || match[1]);
                  const medals = ['🥇', '🥈', '🥉'];
                  
                  return (
                    <div key={idx} className="score-bar-container">
                      <div className="score-bar-header">
                        <span>{medals[idx]} {careerName}</span>
                        <span>{careerConf}% match</span>
                      </div>
                      <div className="score-bar-bg">
                        <div className="score-bar-fill" style={{ width: `${careerConf}%`, backgroundColor: idx === 0 ? 'var(--primary-500)' : idx === 1 ? '#8b5cf6' : 'var(--slate-400)' }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Test Summary scores */}
            <div style={{ background: 'var(--glass-bg)', borderRadius: '24px', padding: '24px', border: '1px solid var(--glass-border)', boxShadow: 'var(--shadow-md)' }}>
              <h3 className="rec-card-title">🧩 Diagnostic Scores</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid var(--glass-border)' }}>
                  <span style={{ fontWeight: 600, color: '#8897BD' }}>🧩 Cognitive Reasoning</span>
                  <strong>{scoreLabel('cognitive', testScores.cognitive)}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid var(--glass-border)' }}>
                  <span style={{ fontWeight: 600, color: '#8897BD' }}>🎯 Career Aptitude</span>
                  <strong>{scoreLabel('aptitude', testScores.aptitude)}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid var(--glass-border)' }}>
                  <span style={{ fontWeight: 600, color: '#8897BD' }}>🧠 Psychometric traits</span>
                  <strong>{scoreLabel('psychometric', testScores.psychometric)}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid var(--glass-border)' }}>
                  <span style={{ fontWeight: 600, color: '#8897BD' }}>💬 Mindset Sentiment</span>
                  <strong>{scoreLabel('sentiment', testScores.sentiment)}</strong>
                </div>
              </div>
            </div>
          </div>

          {/* Narrative Detailed Report */}
          <div style={{ background: 'var(--glass-bg)', borderRadius: '24px', padding: '36px', border: '1px solid var(--glass-border)', boxShadow: 'var(--shadow-md)', marginBottom: '32px' }}>
            <h3 className="rec-card-title" style={{ borderBottom: '2px solid var(--glass-border)', paddingBottom: '12px', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BookOpen size={22} style={{ color: 'var(--primary-500)' }} /> Personal Career Analysis Report
            </h3>
            <div style={{ textAlign: 'left' }}>
              <GeminiFormattedText text={recommendation.narrative} />
            </div>
          </div>

          {/* Universities & Mentors Section */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px', marginBottom: '32px' }}>
            {/* Universities */}
            <div style={{ background: 'var(--glass-bg)', borderRadius: '24px', padding: '28px', border: '1px solid var(--glass-border)', boxShadow: 'var(--shadow-md)' }}>
              <h3 className="rec-card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <GraduationCap style={{ color: 'var(--primary-500)' }} /> Recommended Universities
              </h3>
              <p style={{ fontSize: '0.95rem', color: '#E3E4FA', marginBottom: '16px' }}>
                Top Nigerian universities offering quality programs in {recommendation.career_path}:
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {recommendation.universities?.map((uni, idx) => (
                  <div key={idx} style={{ background: 'rgba(255, 255, 255, 0.06)', padding: '14px', borderRadius: '12px', borderLeft: '3px solid var(--primary-500)', color: 'var(--text-light)' }}>
                    <div className="uni-name">{uni.name}</div>
                    <div className="uni-course">📚 {uni.course}</div>
                    <div className="uni-meta">JAMB Cutoff: <strong>{uni.cutoff}</strong> | 📍 {uni.location}</div>
                    <a href={uni.url} target="_blank" rel="noopener noreferrer" className="uni-link">
                      Visit Website ↗
                    </a>
                  </div>
                ))}
              </div>
            </div>

            {/* Mentors */}
            <div style={{ background: 'var(--glass-bg)', borderRadius: '24px', padding: '28px', border: '1px solid var(--glass-border)', boxShadow: 'var(--shadow-md)' }}>
              <h3 className="rec-card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Users style={{ color: '#8b5cf6' }} /> Suggested LinkedIn Mentors
              </h3>
              <p style={{ fontSize: '0.85rem', color: '#E3E4FA', marginBottom: '16px' }}>
                Search these actual Nigerian professionals in your path to get real-world career context:
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {recommendation.mentors?.map((mentor, idx) => (
                  <div key={idx} style={{ background: 'rgba(255, 255, 255, 0.05)', padding: '14px', borderRadius: '12px', borderLeft: '3px solid #8b5cf6', fontSize: '0.88rem', color: 'var(--text-light)', lineHeight: 1.4 }}>
                    👤 {mentor}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* AI Counsellor Chatbot */}
          <div className="chat-container animate-fade-in" style={{ marginBottom: '32px' }}>
            <div style={{ background: 'linear-gradient(135deg, #1e3a8a, var(--primary-600))', padding: '16px 20px', color: 'white', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <MessageSquare size={20} />
              <div>
                <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>AI Career Advisor Chatbot</div>
                <div style={{ fontSize: '0.78rem', opacity: 0.8 }}>Counselling on JAMB scoring, subject combos, and admission advice</div>
              </div>
            </div>

            <div className="chat-messages">
              {chatMessages.length === 0 ? (
                <div className="chat-bubble chat-bubble-ai">
                  Hi {user.full_name}! 👋 I am your AI career counsellor.
                  I've reviewed your assessment scores and recommended career path of <strong>{recommendation.career_path}</strong>.
                  Ask me anything about which subjects to register in WAEC/JAMB, cutoff marks for Nigerian universities, or the details of these jobs! 😊
                </div>
              ) : (
                chatMessages.map((msg, idx) => (
                  <div key={idx} className={`chat-bubble ${msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}`}>
                    {msg.role === 'user' ? msg.message : <GeminiFormattedText text={msg.message} compact />}
                  </div>
                ))
              )}
              {sendingMsg && (
                <div className="chat-bubble chat-bubble-ai" style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  <div className="spinner spinner-dark" style={{ width: '14px', height: '14px', borderTopColor: 'var(--slate-600)' }} />
                  <span>Thinking...</span>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <form onSubmit={handleSendMessage} className="chat-input-area">
              <input
                type="text"
                className="chat-input"
                placeholder="Ask about JAMB subjects or university cut-offs..."
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                disabled={sendingMsg}
              />
              <button type="submit" className="btn btn-primary" style={{ padding: '10px 16px' }} disabled={sendingMsg || !userInput.trim()}>
                <Send size={18} />
              </button>
            </form>
          </div>
        </>
      ) : (
        <div style={{ textAlign: 'center', padding: '80px 20px', border: '2px dashed var(--slate-300)', borderRadius: '24px', background: 'var(--glass-bg)', borderStyle: 'dashed' }}>
          <Sparkles size={48} style={{ color: 'var(--amber-500)', marginBottom: '16px' }} />
          <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 800, color: 'var(--slate-50)', fontSize: '1.25rem' }}>Recommendations Report Locked</h3>
          <p style={{ color: 'var(--slate-600)', fontSize: '0.9rem', maxWidth: '400px', margin: '8px auto 20px auto' }}>
            Click the button above to run our XGBoost classifier model against your grades ledger and assessment scores to compile your recommendations!
          </p>
        </div>
      )}
    </div>
  );
};

export default Recommendations;
