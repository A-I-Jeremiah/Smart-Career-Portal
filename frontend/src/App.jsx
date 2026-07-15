import React, { useEffect, useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';
import Grades from './pages/Grades';
import Tests from './pages/Tests';
import Recommendations from './pages/Recommendations';
import Profile from './pages/Profile';
import api from './utils/api';
import { LayoutDashboard, BookOpen, Brain, BarChart, LogOut, Menu, X, Users } from 'lucide-react';

const AppContent = () => {
  const { user, loading, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [recommendationReady, setRecommendationReady] = useState(false);

  useEffect(() => {
    if (!user) return;

    const refreshRecommendationGate = async () => {
      try {
        const [testsRes, resultsRes] = await Promise.all([
          api.get('/tests/'),
          api.get('/results/'),
        ]);
        const completedCount = testsRes.data.completed?.length || 0;
        const currentGrades = (resultsRes.data || []).filter((r) => r.result_type === 'Current Grade');
        setRecommendationReady(completedCount >= 4 && currentGrades.length > 0);
      } catch (err) {
        setRecommendationReady(false);
      }
    };

    refreshRecommendationGate();
    const intervalId = window.setInterval(refreshRecommendationGate, 5000);
    return () => window.clearInterval(intervalId);
  }, [user, activeTab]);

  useEffect(() => {
    if (activeTab === 'recommendations' && !recommendationReady) {
      setActiveTab('dashboard');
    }
  }, [activeTab, recommendationReady]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', width: '100vw', height: '100vh', background: 'linear-gradient(180deg, rgba(38, 40, 66, 0.95) 0%, rgba(22, 26, 48, 0.95) 100%)' }}>
        <div className="spinner spinner-dark" style={{ width: '50px', height: '50px' }} />
      </div>
    );
  }

  // Unauthenticated shell
  if (!user) {
    return <Auth />;
  }

  const renderActiveTabContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard setActiveTab={setActiveTab} />;
      case 'grades':
        return <Grades />;
      case 'tests':
        return <Tests />;
      case 'recommendations':
        return <Recommendations />;
      case 'profile':
        return <Profile />;
      default:
        return <Dashboard setActiveTab={setActiveTab} />;
    }
  };

  const navItems = [
    { key: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
    { key: 'grades', label: 'Subject Grades', icon: <BookOpen size={20} /> },
    { key: 'tests', label: 'Take 4 Tests', icon: <Brain size={20} /> },
    {
      key: 'recommendations',
      label: 'Recommendations',
      icon: <BarChart size={20} />,
      disabled: !recommendationReady,
      title: 'Upload grades and complete all four tests first',
    },
    { key: 'profile', label: 'Profile', icon: <Users size={20} /> },
  ];

  return (
    <div className="app-layout">
      {/* Mobile Top Navigation bar */}
      <div className="mobile-header glass-panel">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <LayoutDashboard size={28} style={{ color: 'var(--primary-600)' }} />
          <span className="sidebar-logo-text" style={{ fontSize: '1.1rem' }}>Smart Career</span>
        </div>
        <button
          className="btn btn-secondary"
          style={{ padding: '8px', border: 'none', background: 'transparent' }}
          onClick={() => setMobileSidebarOpen(!mobileSidebarOpen)}
        >
          {mobileSidebarOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Responsive Sidebar Navigation */}
      <aside className={`sidebar glass-panel ${mobileSidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-logo">
          <LayoutDashboard size={36} style={{ color: 'var(--primary-600)' }} />
          <span className="sidebar-logo-text">Smart Career</span>
        </div>

        {/* Profile Card */}
        <div className="sidebar-profile">
          <div className="sidebar-name" title={user.full_name}>{user.full_name}</div>
          <span className="sidebar-class">
            {user.class_level}
            {user.department ? ` — ${user.department}` : ''}
          </span>
        </div>

        {/* Tabs Ledger */}
        <nav className="sidebar-nav">
          {navItems.map((item) => {
            const isActive = activeTab === item.key;
            return (
              <button
                key={item.key}
                className={`nav-item ${isActive ? 'active' : ''} ${item.disabled ? 'disabled' : ''}`}
                disabled={item.disabled}
                title={item.title}
                onClick={() => {
                  if (item.disabled) return;
                  setActiveTab(item.key);
                  setMobileSidebarOpen(false);
                }}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Logout bottom trigger */}
        <div className="sidebar-footer">
          <button className="nav-item" onClick={logout} style={{ color: 'var(--rose-500)', gap: '12px' }}>
            <LogOut size={20} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Layout pane */}
      <main className="main-content">
        {renderActiveTabContent()}
      </main>
    </div>
  );
};

const App = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;
