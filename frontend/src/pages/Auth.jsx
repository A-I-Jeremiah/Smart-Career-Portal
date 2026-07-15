import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { LogIn, UserPlus, GraduationCap, Calendar, Mail, Lock, User } from 'lucide-react';

const Auth = () => {
  const { login, register } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  
  // Login Form States
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  
  // Register Form States
  const [fullName, setFullName] = useState('');
  const [dob, setDob] = useState('');
  const [classLevel, setClassLevel] = useState('SSS 1');
  const [department, setDepartment] = useState('Science');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  
  // UI States
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    if (!loginEmail || !loginPassword) {
      setError('Please fill in all fields.');
      return;
    }
    setError('');
    setLoading(true);
    const result = await login(loginEmail, loginPassword);
    setLoading(false);
    if (!result.success) {
      setError(result.error);
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    if (!fullName || !dob || !registerEmail || !registerPassword) {
      setError('Please fill in all fields.');
      return;
    }
    
    const isSSS = ['SSS 1', 'SSS 2', 'SSS 3', 'SS1', 'SS2', 'SS3'].includes(classLevel);
    const userData = {
      full_name: fullName,
      dob,
      class_level: classLevel,
      department: isSSS ? department : null,
      email: registerEmail,
      password: registerPassword,
    };
    
    setError('');
    setSuccess('');
    setLoading(true);
    const result = await register(userData);
    setLoading(false);
    
    if (result.success) {
      setSuccess('Account created successfully! Please sign in.');
      setIsLogin(true);
      // Reset registration form
      setFullName('');
      setDob('');
      setRegisterEmail('');
      setRegisterPassword('');
    } else {
      setError(result.error);
    }
  };

  const isSSSClass = ['SSS 1', 'SSS 2', 'SSS 3', 'SS1', 'SS2', 'SS3'].includes(classLevel);

  return (
    <div className="auth-container animate-fade-in">
      <div className="auth-card glass-panel">
        <div className="auth-header">
          <div className="sidebar-logo" style={{ justifyContent: 'center', marginBottom: '16px' }}>
            <span style={{ fontSize: '2.5rem' }}>🎓</span>
            <span className="sidebar-logo-text" style={{ fontSize: '1.75rem' }}>Smart Career Portal</span>
          </div>
          <p className="auth-subtitle">AI-Powered Career Guidance for Nigerian Secondary Students</p>
        </div>

        {/* Tab Switches */}
        <div style={{ display: 'flex', background: 'rgba(8, 35, 79, 0.72)', borderRadius: '12px', padding: '4px', marginBottom: '24px', border: '1px solid rgba(147, 197, 253, 0.22)' }}>
          <button
            onClick={() => { setIsLogin(true); setError(''); setSuccess(''); }}
            className={`btn ${isLogin ? 'btn-primary' : 'btn-secondary'}`}
            style={{ flex: 1, border: 'none', background: isLogin ? 'var(--primary-500)' : 'transparent', boxShadow: isLogin ? 'var(--shadow-sm)' : 'none', color: isLogin ? 'white' : '#bfdbfe' }}
          >
            <LogIn size={18} /> Sign In
          </button>
          <button
            onClick={() => { setIsLogin(false); setError(''); setSuccess(''); }}
            className={`btn ${!isLogin ? 'btn-primary' : 'btn-secondary'}`}
            style={{ flex: 1, border: 'none', background: !isLogin ? 'var(--primary-500)' : 'transparent', boxShadow: !isLogin ? 'var(--shadow-sm)' : 'none', color: !isLogin ? 'white' : '#bfdbfe' }}
          >
            <UserPlus size={18} /> Register
          </button>
        </div>

        {/* Alert banners */}
        {error && (
          <div className="alert-banner alert-banner-warning" style={{ marginBottom: '20px' }}>
            <span>⚠️ {error}</span>
          </div>
        )}
        {success && (
          <div className="alert-banner alert-banner-success" style={{ marginBottom: '20px' }}>
            <span>🎉 {success}</span>
          </div>
        )}

        {isLogin ? (
          /* LOGIN FORM */
          <form onSubmit={handleLoginSubmit}>
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <div style={{ position: 'relative' }}>
                <Mail size={18} style={{ position: 'absolute', left: '14px', top: '14px', color: 'var(--slate-400)' }} />
                <input
                  type="email"
                  className="form-input"
                  style={{ paddingLeft: '44px' }}
                  placeholder="student@example.com"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <div style={{ position: 'relative' }}>
                <Lock size={18} style={{ position: 'absolute', left: '14px', top: '14px', color: 'var(--slate-400)' }} />
                <input
                  type="password"
                  className="form-input"
                  style={{ paddingLeft: '44px' }}
                  placeholder="••••••••"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '12px', marginTop: '12px' }} disabled={loading}>
              {loading ? <div className="spinner" /> : 'Sign In'}
            </button>
          </form>
        ) : (
          /* REGISTRATION FORM */
          <form onSubmit={handleRegisterSubmit}>
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <div style={{ position: 'relative' }}>
                <User size={18} style={{ position: 'absolute', left: '14px', top: '14px', color: 'var(--slate-400)' }} />
                <input
                  type="text"
                  className="form-input"
                  style={{ paddingLeft: '44px' }}
                  placeholder="Chinedu Ada Obi"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Date of Birth</label>
              <div style={{ position: 'relative' }}>
                <Calendar size={18} style={{ position: 'absolute', left: '14px', top: '14px', color: 'var(--slate-400)' }} />
                <input
                  type="date"
                  className="form-input"
                  style={{ paddingLeft: '44px' }}
                  value={dob}
                  onChange={(e) => setDob(e.target.value)}
                  required
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '16px' }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Class Level</label>
                <div style={{ position: 'relative' }}>
                  <GraduationCap size={18} style={{ position: 'absolute', left: '14px', top: '14px', color: 'var(--slate-400)' }} />
                  <select
                    className="form-select"
                    style={{ paddingLeft: '44px' }}
                    value={classLevel}
                    onChange={(e) => setClassLevel(e.target.value)}
                  >
                    <option value="JSS 1">JSS 1</option>
                    <option value="JSS 2">JSS 2</option>
                    <option value="JSS 3">JSS 3</option>
                    <option value="SSS 1">SSS 1</option>
                    <option value="SSS 2">SSS 2</option>
                    <option value="SSS 3">SSS 3</option>
                  </select>
                </div>
              </div>

              {isSSSClass && (
                <div className="form-group animate-fade-in" style={{ flex: 1 }}>
                  <label className="form-label">Department</label>
                  <select
                    className="form-select"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                  >
                    <option value="Science">Science</option>
                    <option value="Arts">Arts</option>
                    <option value="Commercial">Commercial</option>
                  </select>
                </div>
              )}
            </div>

            <div className="form-group">
              <label className="form-label">Email Address</label>
              <div style={{ position: 'relative' }}>
                <Mail size={18} style={{ position: 'absolute', left: '14px', top: '14px', color: 'var(--slate-400)' }} />
                <input
                  type="email"
                  className="form-input"
                  style={{ paddingLeft: '44px' }}
                  placeholder="student@example.com"
                  value={registerEmail}
                  onChange={(e) => setRegisterEmail(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <div style={{ position: 'relative' }}>
                <Lock size={18} style={{ position: 'absolute', left: '14px', top: '14px', color: 'var(--slate-400)' }} />
                <input
                  type="password"
                  className="form-input"
                  style={{ paddingLeft: '44px' }}
                  placeholder="••••••••"
                  value={registerPassword}
                  onChange={(e) => setRegisterPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '12px', marginTop: '12px' }} disabled={loading}>
              {loading ? <div className="spinner" /> : 'Create Account'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default Auth;
