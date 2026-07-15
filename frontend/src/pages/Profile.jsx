import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { Users, Key, BarChart, Bookmark, Wrench, ShieldCheck, Clock3, CheckCircle2, Star } from 'lucide-react';

const Profile = () => {
  const { user, logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [results, setResults] = useState([]);
  const [tests, setTests] = useState({ completed: [], scores: {} });
  const [recommendation, setRecommendation] = useState(null);
  const [saving, setSaving] = useState(false);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const fetchProfile = async () => {
    setLoading(true);
    setError('');
    try {
      const [resRes, testsRes, recRes] = await Promise.all([
        api.get('/results/'),
        api.get('/tests/'),
        api.get('/history/recommendation').catch(() => null),
      ]);
      setResults(resRes.data || []);
      setTests(testsRes.data || { completed: [], scores: {} });
      setRecommendation(recRes ? recRes.data : null);
    } catch (err) {
      console.error('Error loading profile data', err);
      setError('Unable to load profile information at the moment.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setMessage('');
    setError('');

    if (!oldPassword || !newPassword) {
      setError('Please enter both current and new passwords.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.');
      return;
    }

    setSaving(true);
    try {
      const response = await api.post('/auth/user/change-password', {
        old_password: oldPassword,
        new_password: newPassword,
      });
      setMessage(response.data?.message || 'Password updated successfully.');
      setTimeout(() => logout(), 1500);
    } catch (err) {
      console.error('Password change error', err);
      setError(err?.response?.data?.detail || 'Failed to change password.');
    } finally {
      setSaving(false);
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
  };
 
  const topCareerPaths = Array.isArray(recommendation?.top3) ? recommendation.top3.slice(0, 3) : [];
  const parseImprovementTips = (narrative) => {
    if (!narrative) return [];
    const lines = narrative
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);
 
    const sectionStart = lines.findIndex((line) => /areas to strengthen/i.test(line));
    const tips = [];
    for (let i = sectionStart >= 0 ? sectionStart + 1 : 0; i < lines.length; i += 1) {
      const line = lines[i];
      if (/^##\s*/.test(line)) break;
      const cleaned = line.replace(/^[-*]\s*/, '').trim();
      if (cleaned) tips.push(cleaned);
      if (tips.length >= 5) break;
    }
 
    if (tips.length > 0) {
      return tips;
    }
 
    return lines
      .filter((line) => /^[-*]\s+/.test(line))
      .map((line) => line.replace(/^[-*]\s+/, ''))
      .slice(0, 5);
  };
 
  const improvementTips = parseImprovementTips(recommendation?.narrative);
 
  return (
    <div className="animate-fade-in" style={{ maxWidth: '1100px', margin: '0 auto', paddingBottom: '40px' }}>
      <div className="page-header">
        <h2 className="page-title">👤 My Profile</h2>
        <p className="page-subtitle">Account settings, performance insights, and your saved career recommendations.</p>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '280px' }}>
          <div className="spinner" />
        </div>
      ) : (
        <>
          <section style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '20px', marginBottom: '28px' }}>
            <div style={{ background: 'var(--glass-bg)', padding: '24px', borderRadius: '20px', border: '1px solid var(--glass-border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '24px' }}>
                <div style={{ width: '56px', height: '56px', borderRadius: '18px', backgroundColor: 'rgba(44, 73, 127, 0.35)', display: 'grid', placeItems: 'center', color: '#2C497F' }}>
                  <Users size={28} />
                </div>
                <div>
                  <h3 style={{ margin: 0 }}>{user.full_name.toUpperCase()}</h3>
                  <p style={{ margin: 0, color: '#8897BD' }}>{user.email}</p>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '16px' }}>
                <div style={{ padding: '18px', background: 'rgba(41, 57, 97, 0.45)', borderRadius: '16px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                  <div style={{ color: '#8897BD', fontSize: '0.85rem', marginBottom: '6px' }}>Class level</div>
                  <div style={{ fontWeight: 700, color: '#E3E4FA' }}>{user.class_level || 'N/A'}</div>
                </div>
                <div style={{ padding: '18px', background: 'rgba(41, 57, 97, 0.45)', borderRadius: '16px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                  <div style={{ color: '#8897BD', fontSize: '0.85rem', marginBottom: '6px' }}>Department</div>
                  <div style={{ fontWeight: 700, color: '#E3E4FA' }}>{user.department || 'Not specified'}</div>
                </div>
                <div style={{ padding: '18px', background: 'rgba(41, 57, 97, 0.45)', borderRadius: '16px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                  <div style={{ color: '#8897BD', fontSize: '0.85rem', marginBottom: '6px' }}>Saved recommendation</div>
                  <div style={{ fontWeight: 700, color: '#E3E4FA' }}>{recommendation?.career_path || 'None yet'}</div>
                </div>
                <div style={{ padding: '18px', background: 'rgba(41, 57, 97, 0.45)', borderRadius: '16px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                  <div style={{ color: '#8897BD', fontSize: '0.85rem', marginBottom: '6px' }}>Confidence</div>
                  <div style={{ fontWeight: 700, color: '#E3E4FA' }}>{recommendation ? `${recommendation.confidence}%` : 'N/A'}</div>
                </div>
              </div>
            </div>

            <aside style={{ background: 'var(--glass-bg)', padding: '24px', borderRadius: '20px', border: '1px solid var(--glass-border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
                <div>
                  <div style={{ color: 'var(--slate-500)', fontSize: '0.85rem' }}>Account status</div>
                  <div style={{ fontWeight: 700 }}>Active</div>
                </div>
                <ShieldCheck size={24} style={{ color: 'var(--emerald-600)' }} />
              </div>
              <div style={{ color: '#E3E4FA', fontSize: '0.95rem', lineHeight: 1.7 }}>
                Your profile stores your assessment progress and recommended career pathways securely. Use the password form below to keep your account safe and update your data anytime.
              </div>
            </aside>
          </section>

          <section style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '28px' }}>
            <article style={{ background: 'var(--glass-bg)', padding: '24px', borderRadius: '20px', border: '1px solid var(--glass-border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '18px' }}>
                <BarChart size={18} />
                <h3 style={{ margin: 0 }}>Performance summary</h3>
              </div>
              <div style={{ display: 'grid', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '16px', background: 'rgba(41, 57, 97, 0.45)', borderRadius: '16px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                  <div>
                    <div style={{ color: '#8897BD', fontSize: '0.85rem' }}>Tests completed</div>
                    <div style={{ fontWeight: 700, color: '#E3E4FA' }}>{tests.completed?.length || 0} / 4</div>
                  </div>
                  <CheckCircle2 size={22} style={{ color: '#2C497F' }} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '16px', background: 'rgba(41, 57, 97, 0.45)', borderRadius: '16px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                  <div>
                    <div style={{ color: '#8897BD', fontSize: '0.85rem' }}>Saved grades</div>
                    <div style={{ fontWeight: 700, color: '#E3E4FA' }}>{results.length || 0}</div>
                  </div>
                  <Clock3 size={22} style={{ color: '#8897BD' }} />
                </div>
                <div style={{ display: 'grid', gap: '10px', padding: '16px', background: 'rgba(41, 57, 97, 0.45)', borderRadius: '16px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                  <div style={{ color: '#8897BD', fontSize: '0.85rem' }}>Latest recommendation</div>
                  {recommendation ? (
                    <div>
                      <div style={{ fontWeight: 700, color: '#E3E4FA' }}>{recommendation.career_path}</div>
                      <div style={{ color: '#8897BD', marginTop: '6px' }}>Saved on {formatDate(recommendation.generated_at)}</div>
                    </div>
                  ) : (
                    <div style={{ color: '#8897BD' }}>No recommendation generated yet.</div>
                  )}
                </div>
              </div>
            </article>

            <article style={{ background: 'var(--glass-bg)', padding: '24px', borderRadius: '20px', border: '1px solid var(--glass-border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '18px' }}>
                <Bookmark size={18} />
                <h3 style={{ margin: 0 }}>Saved career paths</h3>
              </div>
              {topCareerPaths.length ? (
                <div style={{ display: 'grid', gap: '14px' }}>
                  {topCareerPaths.map((item, index) => {
                    const careerLabel = item?.career ?? (typeof item === 'string' ? item : item?.[0] ?? 'Career option');
                    const careerConfidence = item?.confidence_percent ?? item?.confidence ?? (typeof item === 'number' ? item : 'N/A');
                    return (
                      <div key={index} style={{ padding: '18px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '16px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                          <div>
                            <div style={{ fontWeight: 700, color: 'var(--text-light)' }}>{careerLabel}</div>
                            <div style={{ color: 'var(--slate-400)', fontSize: '0.9rem' }}>#{index + 1} recommendation</div>
                          </div>
                          <div style={{ color: 'var(--primary-600)', fontWeight: 700 }}>{careerConfidence}%</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ color: 'var(--slate-600)' }}>Complete the required tests and generate recommendations to save career paths.</div>
              )}
            </article>
          </section>

          <section style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px', marginBottom: '28px' }}>
            <article style={{ background: 'var(--glass-bg)', padding: '24px', borderRadius: '20px', border: '1px solid var(--glass-border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '18px' }}>
                <Star size={18} />
                <h3 style={{ margin: 0 }}>Improvement plan</h3>
              </div>
              {recommendation ? (
                <div style={{ color: '#8897BD', lineHeight: 1.8 }}>
                  <div style={{ marginBottom: '14px' }}><strong>Review these improvement areas to strengthen your recommendation:</strong></div>
                  {improvementTips.length ? (
                    <ul style={{ paddingLeft: '18px', color: '#E3E4FA' }}>
                      {improvementTips.map((tip, idx) => (
                        <li key={idx} style={{ marginBottom: '10px' }}>{tip}</li>
                      ))}
                    </ul>
                  ) : (
                    <p style={{ color: 'var(--slate-600)' }}>No specific improvement notes are available yet. Generate a recommendation report to receive targeted guidance.</p>
                  )}
                </div>
              ) : (
                <div style={{ color: 'var(--slate-600)' }}>No recommendation has been saved yet. Generate your first report to capture specific improvement guidance.</div>
              )}
            </article>
          </section>

          <section style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '20px' }}>
            <div style={{ background: 'var(--glass-bg)', padding: '24px', borderRadius: '20px', border: '1px solid var(--glass-border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '18px' }}>
                <Wrench size={18} />
                <h3 style={{ margin: 0 }}>Recommendation summary</h3>
              </div>
              {recommendation ? (
                <div style={{ color: '#8897BD', lineHeight: 1.8 }}>
                  <div style={{ marginBottom: '16px' }}><strong>Your main recommended path:</strong> {recommendation.career_path}</div>
                  <div style={{ marginBottom: '12px' }}><strong>Confidence:</strong> {recommendation.confidence}%</div>
                  <div style={{ marginBottom: '12px' }}><strong>Why it matters:</strong> This recommendation is based on your assessment performance, latest academic grades, and personalised career match logic.</div>
                  <div><strong>Next steps:</strong> Review your recommendation in the Recommendations tab, use the chat assistant for guidance, and update your grades/tests if you want a refreshed path.</div>
                </div>
              ) : (
                <div style={{ color: 'var(--slate-600)' }}>No recommendation is currently saved. Complete your profile and assessments, then visit Recommendations to generate one.</div>
              )}
            </div>

            <div style={{ background: 'var(--glass-bg)', padding: '24px', borderRadius: '20px', border: '1px solid var(--glass-border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '18px' }}>
                <Key size={18} />
                <h3 style={{ margin: 0 }}>Change password</h3>
              </div>
              <form onSubmit={handleChangePassword} style={{ display: 'grid', gap: '14px' }}>
                <input
                  type="password"
                  placeholder="Current password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                />
                <input
                  type="password"
                  placeholder="New password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
                <input
                  type="password"
                  placeholder="Confirm new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
                <button className="btn btn-primary" type="submit" disabled={saving}>
                  {saving ? 'Updating...' : 'Save new password'}
                </button>
                {message && <div style={{ color: 'var(--emerald-600)', fontWeight: 600 }}>{message}</div>}
                {error && <div style={{ color: 'var(--rose-600)', fontWeight: 600 }}>{error}</div>}
              </form>
            </div>
          </section>
        </>
      )}
    </div>
  );
};

export default Profile;
