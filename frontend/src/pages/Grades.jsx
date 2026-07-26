import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { getSubjectsForDepartment, scoreToGrade } from '../utils/subjectMapper';
import { Trash2 } from 'lucide-react';

const Grades = () => {
  const { user } = useAuth();
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Table input states
  const [editingScores, setEditingScores] = useState({}); // { "Subject Name": "85" }
  const [savingSubjects, setSavingSubjects] = useState({}); // { "Subject Name": true/false }

  const fetchResults = async () => {
    try {
      const response = await api.get('/results/');
      // Filter only current grade results
      const currentGrades = response.data.filter((r) => r.result_type === 'Current Grade');
      setResults(currentGrades);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching academic results:', err);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, []);

  const handleEditChange = (subject, value) => {
    setEditingScores((prev) => ({ ...prev, [subject]: value }));
  };

  const handleSave = async (subject, oldResultId = null) => {
    const scoreVal = editingScores[subject];
    const scoreNum = parseFloat(scoreVal);
    
    if (isNaN(scoreNum) || scoreNum < 0 || scoreNum > 100) {
      alert('Please enter a valid score between 0 and 100.');
      return;
    }
    
    setSavingSubjects((prev) => ({ ...prev, [subject]: true }));
    try {
      // If updating an existing grade, delete the old one first
      if (oldResultId) {
        await api.delete(`/results/${oldResultId}`);
      }
      
      // Save the new grade
      await api.post('/results/', {
        result_type: 'Current Grade',
        subject: subject,
        score: scoreNum,
        exam_date: new Date().toISOString().split('T')[0],
      });
      
      // Clear from editing state
      setEditingScores((prev) => {
        const next = { ...prev };
        delete next[subject];
        return next;
      });
      
      fetchResults();
    } catch (err) {
      console.error('Error saving grade:', err);
      alert(err.response?.data?.detail || 'Failed to save grade. Please try again.');
    } finally {
      setSavingSubjects((prev) => ({ ...prev, [subject]: false }));
    }
  };

  const startEdit = (subject, currentScore) => {
    setEditingScores((prev) => ({ ...prev, [subject]: currentScore.toString() }));
  };

  const cancelEdit = (subject) => {
    setEditingScores((prev) => {
        const next = { ...prev };
        delete next[subject];
        return next;
    });
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this grade?')) return;
    try {
      await api.delete(`/results/${id}`);
      fetchResults();
    } catch (err) {
      console.error('Error deleting result:', err);
      alert('Failed to delete grade.');
    }
  };

  // Compute Stats
  const totalRecords = results.length;
  const avgScore = totalRecords > 0
    ? parseFloat((results.reduce((acc, r) => acc + r.score, 0) / totalRecords).toFixed(1))
    : 0;
  const topScore = totalRecords > 0 ? Math.max(...results.map((r) => r.score)) : 0;

  const subjectList = getSubjectsForDepartment(user.department);

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h2 className="page-title">Current Subject Grades</h2>
        <p className="page-subtitle">
          Manage scores for {user.class_level} ({user.department || 'General'} department)
        </p>
      </div>

      {/* Stats Chips */}
      <div style={{ display: 'flex', gap: '20px', marginBottom: '32px', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, background: 'var(--glass-bg)', borderRadius: '16px', padding: '16px 20px', border: '1px solid var(--glass-border)', boxShadow: 'var(--shadow-sm)', minWidth: '150px' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--slate-600)', textTransform: 'uppercase' }}>Subjects Entered</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#0AFFFF', marginTop: '4px' }}>{totalRecords}</div>
        </div>
        <div style={{ flex: 1, background: 'var(--glass-bg)', borderRadius: '16px', padding: '16px 20px', border: '1px solid var(--glass-border)', boxShadow: 'var(--shadow-sm)', minWidth: '150px' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--slate-600)', textTransform: 'uppercase' }}>Average Score</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#0AFFFF', marginTop: '4px' }}>{avgScore}%</div>
        </div>
        <div style={{ flex: 1, background: 'var(--glass-bg)', borderRadius: '16px', padding: '16px 20px', border: '1px solid var(--glass-border)', boxShadow: 'var(--shadow-sm)', minWidth: '150px' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--slate-600)', textTransform: 'uppercase' }}>Top Score</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#0AFFFF', marginTop: '4px' }}>{topScore}%</div>
        </div>
      </div>

      {/* Ledger Section / Input Table */}
      <div style={{ background: 'var(--glass-bg)', borderRadius: '24px', padding: '28px', border: '1px solid var(--glass-border)', boxShadow: 'var(--shadow-md)', marginBottom: '32px' }}>
        <h3 className="rec-card-title">📂 Department Subject Scores</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '20px' }}>
          Input your score grades for all available subjects.
        </p>
        
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
            <div className="spinner spinner-dark" />
          </div>
        ) : (
          <div className="ledger-table-container">
            <table className="ledger-table">
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Score</th>
                  <th>Grade</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {subjectList.map((subj) => {
                  const existingResult = results.find((r) => r.subject.toLowerCase() === subj.toLowerCase());
                  const isEditing = editingScores.hasOwnProperty(subj);
                  const isSaving = savingSubjects[subj];
                  
                  return (
                    <tr key={subj}>
                      <td style={{ fontWeight: 600 }}>{subj}</td>
                      
                      {existingResult && !isEditing ? (
                        <>
                          <td>{existingResult.score}%</td>
                          <td>
                            <span style={{
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontWeight: 700,
                              fontSize: '0.85rem',
                              backgroundColor: existingResult.score >= 75 ? 'rgba(16, 185, 129, 0.1)' : existingResult.score >= 50 ? 'rgba(45, 99, 184, 0.1)' : 'rgba(244, 63, 94, 0.1)',
                              color: existingResult.score >= 75 ? 'var(--emerald-600)' : existingResult.score >= 50 ? '#C9FFE5' : 'var(--rose-500)'
                            }}>
                              {scoreToGrade(existingResult.score)}
                            </span>
                          </td>
                          <td>
                            <div style={{ display: 'flex', gap: '8px' }}>
                              <button
                                className="btn btn-secondary"
                                style={{ padding: '6px 12px', fontSize: '0.8rem', background: 'transparent' }}
                                onClick={() => startEdit(subj, existingResult.score)}
                                title="Edit Grade"
                              >
                                Edit
                              </button>
                              <button
                                className="btn btn-secondary"
                                style={{ padding: '6px', color: 'var(--rose-500)', borderColor: 'rgba(244, 63, 94, 0.2)', background: 'transparent' }}
                                onClick={() => handleDelete(existingResult.id)}
                                title="Delete Grade"
                              >
                                <Trash2 size={16} />
                              </button>
                            </div>
                          </td>
                        </>
                      ) : (
                        <>
                          <td>
                            <input
                              type="number"
                              min="0"
                              max="100"
                              step="any"
                              className="form-input"
                              style={{ width: '100px', padding: '6px 10px', minHeight: '36px', marginBottom: 0 }}
                              placeholder="Score %"
                              value={editingScores[subj] !== undefined ? editingScores[subj] : ''}
                              onChange={(e) => handleEditChange(subj, e.target.value)}
                              disabled={isSaving}
                            />
                          </td>
                          <td>-</td>
                          <td>
                            <div style={{ display: 'flex', gap: '8px' }}>
                              <button
                                className="btn btn-primary"
                                style={{ padding: '6px 16px', fontSize: '0.8rem' }}
                                onClick={() => handleSave(subj, existingResult?.id)}
                                disabled={isSaving || !editingScores[subj]}
                              >
                                {isSaving ? 'Saving...' : 'Save'}
                              </button>
                              {existingResult && isEditing && (
                                <button
                                  className="btn btn-secondary"
                                  style={{ padding: '6px 12px', fontSize: '0.8rem', background: 'transparent' }}
                                  onClick={() => cancelEdit(subj)}
                                  disabled={isSaving}
                                >
                                  Cancel
                                </button>
                              )}
                            </div>
                          </td>
                        </>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default Grades;
