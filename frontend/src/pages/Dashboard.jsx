import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { BookOpen, Award, CheckCircle2, ArrowRight, HelpCircle } from 'lucide-react';

const Dashboard = ({ setActiveTab }) => {
  const { user } = useAuth();
  const [stats, setStats] = useState({
    gradesCount: 0,
    testsCount: 0,
    recReady: false,
    loading: true,
  });

  useEffect(() => {
    const fetchDashboardStats = async () => {
      try {
        // Fetch academic results
        const gradesRes = await api.get('/results/');
        const grades = gradesRes.data.filter((r) => r.result_type === 'Current Grade');
        
        // Fetch tests completion status
        const testsRes = await api.get('/tests/');
        const completedTests = testsRes.data.completed;
        
        // Fetch recommendation
        let recReady = false;
        try {
          const recRes = await api.get('/history/recommendation');
          if (recRes.data && recRes.data.career_path) {
            recReady = true;
          }
        } catch (e) {
          // 404 means not generated yet
          recReady = false;
        }

        setStats({
          gradesCount: grades.length,
          testsCount: completedTests.length,
          recReady,
          loading: false,
        });
      } catch (err) {
        console.error('Error fetching dashboard stats:', err);
        setStats((prev) => ({ ...prev, loading: false }));
      }
    };

    fetchDashboardStats();
  }, []);

  if (stats.loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '300px' }}>
        <div className="spinner spinner-dark" style={{ width: '40px', height: '40px' }} />
      </div>
    );
  }

  const deptText = user.department ? ` — ${user.department}` : '';

  return (
    <div className="animate-fade-in">
      {/* Welcome Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(47,125,246,0.12) 0%, rgba(139,92,246,0.06) 100%)',
        padding: '28px',
        borderRadius: '20px',
        color: 'var(--slate-50)',
        marginBottom: '28px',
        boxShadow: 'var(--shadow-md)',
        border: '1px solid var(--glass-border)'
      }}>
        <h2 style={{ margin: 0, fontWeight: 700, color: 'white', fontSize: '2.5rem', fontFamily: 'var(--font-display)', letterSpacing: '2px' }}>
          Welcome Back, {user.full_name.toUpperCase()}! 👋
        </h2>
        <p style={{ margin: '8px 0 0 0', opacity: 0.9, fontSize: '1rem', fontWeight: 500 }}>
          Class: <span style={{ background: 'rgba(255,255,255,0.2)', padding: '2px 10px', borderRadius: '6px', fontWeight: 700 }}>{user.class_level}{deptText}</span>
        </p>
      </div>

      {/* KPI Cards */}
      <div className="dashboard-grid">
        <div className="metric-card glass-panel" style={{ borderLeft: '5px solid var(--primary-500)' }}>
          <div className="metric-info">
            <span className="metric-label">Subject Grades</span>
            <span className="metric-value">{stats.gradesCount}</span>
          </div>
        <div style={{ color: 'var(--primary-500)' }}>
          <BookOpen size={36} />
        </div>
        </div>

        <div className="metric-card glass-panel" style={{ borderLeft: '5px solid #8b5cf6' }}>
        <div className="metric-info">
          <span className="metric-label">Tests Completed</span>
          <span className="metric-value">{stats.testsCount} / 4</span>
        </div>
        <div style={{ color: '#8b5cf6' }}>
          <Award size={36} />
        </div>
        </div>

        <div className="metric-card glass-panel" style={{ borderLeft: `5px solid ${stats.recReady ? 'var(--emerald-500)' : 'var(--amber-500)'}` }}>
        <div className="metric-info">
          <span className="metric-label">Recommendation</span>
          <span className="metric-value">{stats.recReady ? 'Ready' : 'Pending'}</span>
        </div>
        <div style={{ color: stats.recReady ? 'var(--emerald-500)' : 'var(--amber-500)' }}>
          {stats.recReady ? <CheckCircle2 size={36} /> : <HelpCircle size={36} />}
        </div>
        </div>
      </div>

      {/* System Status Alert Banner */}
      {stats.recReady ? (
        <div className="alert-banner alert-banner-success">
          <CheckCircle2 size={24} style={{ flexShrink: 0 }} />
          <div>
            <strong>Success! Your career path is ready!</strong>
            <p style={{ marginTop: '2px', fontSize: '0.9rem', opacity: 0.9 }}>
              We've analyzed your academic strengths and assessments. Head to the <strong>My Recommendations</strong> tab to view your customized university options, professional mentor matches, and chat with your AI counsellor!
            </p>
          </div>
        </div>
      ) : (
        <div className="alert-banner alert-banner-info">
          <HelpCircle size={24} style={{ flexShrink: 0 }} />
          <div>
            <strong>Assessment Required</strong>
            <p style={{ marginTop: '2px', fontSize: '0.9rem', opacity: 0.9 }}>
              To unlock your tailored AI-powered career recommendation, you must first input your current subject scores and complete all 4 short career diagnostic tests.
            </p>
          </div>
        </div>
      )}

      {/* Journey Steps Section */}
      <div style={{ marginTop: '36px', background: 'var(--glass-bg)', borderRadius: '24px', padding: '32px', border: '1px solid var(--glass-border)' }}>
        <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '2.3rem', color: 'var(--slate-50)', marginBottom: '24px' }}>
          🚀 Journey Map Steps
        </h3>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Step 1 */}
          <div style={{ display: 'flex', gap: '16px', background: 'var(--card-bg)', padding: '20px', borderRadius: '16px', borderLeft: '4px solid #3b82f6', alignItems: 'center' }}>
            <div style={{ flexGrow: 1 }}>
              <h4 style={{ fontWeight: 700, fontSize: '1rem', color: '#8897BD' }}>1. Enter Current Subject Grades</h4>
              <p style={{ fontSize: '1.1rem', color: '#3b82f6', marginTop: '4px', fontWeight: 600 }}>
                Log the grades of your core department subjects. These reflect your baseline academic competencies.
              </p>
            </div>
            <button className="btn btn-secondary" style={{ padding: '8px 16px', whiteSpace: 'nowrap' }} onClick={() => setActiveTab('grades')}>
              Go to Grades <ArrowRight size={16} />
            </button>
          </div>

          {/* Step 2 */}
          <div style={{ display: 'flex', gap: '16px', background: 'var(--card-bg)', padding: '20px', borderRadius: '16px', borderLeft: '4px solid #8b5cf6', alignItems: 'center' }}>
            <div style={{ flexGrow: 1 }}>
              <h4 style={{ fontWeight: 700, fontSize: '1rem', color: '#8897BD' }}>2. Take 4 Career Assessment Tests</h4>
              <p style={{ fontSize: '1.1rem', color: '#8b5cf6', marginTop: '4px', fontWeight: 600 }}>
                Answer the cognitive reasoning and interest questions to measure your logical skill and personal motivations.
              </p>
            </div>
            <button className="btn btn-secondary" style={{ padding: '8px 16px', whiteSpace: 'nowrap' }} onClick={() => setActiveTab('tests')}>
              Start Tests <ArrowRight size={16} />
            </button>
          </div>

          {/* Step 3 */}
          <div style={{ display: 'flex', gap: '16px', background: 'var(--card-bg)', padding: '20px', borderRadius: '16px', borderLeft: '4px solid #10b981', alignItems: 'center' }}>
            <div style={{ flexGrow: 1 }}>
              <h4 style={{ fontWeight: 700, fontSize: '1rem', color: '#8897BD' }}>3. Unlock Personalized AI Recommendations</h4>
              <p style={{ fontSize: '1.1rem', color: '#10b981', marginTop: '4px', fontWeight: 600 }}>
                Receive a full report detailing your top career matches, cutoff marks for Nigerian universities, and live chat guidance.
              </p>
            </div>
            <button className="btn btn-secondary" style={{ padding: '8px 16px', whiteSpace: 'nowrap' }} onClick={() => setActiveTab('recommendations')} disabled={!stats.recReady}>
              View Recommendations <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
