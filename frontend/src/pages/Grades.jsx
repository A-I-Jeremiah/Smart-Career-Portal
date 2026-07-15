import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { getSubjectsForDepartment, scoreToGrade } from '../utils/subjectMapper';
import { Trash2, Upload, FileSpreadsheet, PlusCircle, AlertCircle, CheckCircle } from 'lucide-react';
import * as XLSX from 'xlsx';

const Grades = () => {
  const { user } = useAuth();
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Manual form states
  const [selectedSubject, setSelectedSubject] = useState('');
  const [manualScore, setManualScore] = useState('');
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');

  // Bulk upload states
  const [uploadProgress, setUploadProgress] = useState(null);
  const [uploadError, setUploadError] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState('');
  const fileInputRef = useRef(null);

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

  const handleManualSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');

    if (!selectedSubject) {
      setFormError('Please select a subject.');
      return;
    }

    const scoreNum = parseFloat(manualScore);
    if (isNaN(scoreNum) || scoreNum < 0 || scoreNum > 100) {
      setFormError('Please enter a valid score between 0 and 100.');
      return;
    }

    try {
      await api.post('/results/', {
        result_type: 'Current Grade',
        subject: selectedSubject,
        score: scoreNum,
        exam_date: new Date().toISOString().split('T')[0],
      });
      
      setFormSuccess(`Successfully saved ${selectedSubject}!`);
      setManualScore('');
      setSelectedSubject('');
      fetchResults();
    } catch (err) {
      console.error('Error adding result:', err);
      const detail = err.response?.data?.detail || 'Failed to save grade. Is it a duplicate?';
      setFormError(detail);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this grade?')) return;
    try {
      await api.delete(`/results/${id}`);
      fetchResults();
    } catch (err) {
      console.error('Error deleting result:', err);
    }
  };

  // Bulk Excel/CSV parser
  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setUploadError('');
    setUploadSuccess('');
    setUploadProgress('Reading file...');

    const reader = new FileReader();

    reader.onload = async (evt) => {
      try {
        const data = evt.target.result;
        let rows = [];

        if (file.name.endsWith('.csv')) {
          // Parse CSV
          const text = new TextDecoder().decode(data);
          const lines = text.split('\n');
          const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
          
          for (let i = 1; i < lines.length; i++) {
            if (!lines[i].trim()) continue;
            const values = lines[i].split(',').map(v => v.trim());
            const rowObj = {};
            headers.forEach((h, idx) => {
              rowObj[h] = values[idx];
            });
            rows.push(rowObj);
          }
        } else {
          // Parse Excel binary
          const workbook = XLSX.read(data, { type: 'binary' });
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          rows = XLSX.utils.sheet_to_json(worksheet);
        }

        // Standardize column casings
        const normalizedRows = rows.map((row) => {
          const newRow = {};
          Object.keys(row).forEach((key) => {
            const normalizedKey = key.trim().toLowerCase().replace('_', ' ');
            newRow[normalizedKey] = row[key];
          });
          return newRow;
        });

        // Validate headers
        if (normalizedRows.length === 0) {
          throw new Error('The file is empty.');
        }

        const sample = normalizedRows[0];
        if (!('subject' in sample) || !('score' in sample)) {
          throw new Error('Missing columns. File must contain "Subject" and "Score" headers.');
        }

        setUploadProgress(`Importing 0 / ${normalizedRows.length} records...`);
        let savedCount = 0;
        let duplicateCount = 0;

        for (let i = 0; i < normalizedRows.length; i++) {
          const r = normalizedRows[i];
          const subjectName = String(r.subject).trim();
          const scoreNum = parseFloat(r.score);
          const examDate = r['exam date'] ? String(r['exam date']).trim() : new Date().toISOString().split('T')[0];

          if (!subjectName || isNaN(scoreNum) || scoreNum < 0 || scoreNum > 100) {
            continue; // Skip invalid records
          }

          try {
            await api.post('/results/', {
              result_type: 'Current Grade',
              subject: subjectName,
              score: scoreNum,
              exam_date: examDate,
            });
            savedCount++;
          } catch (err) {
            if (err.response?.status === 409) {
              duplicateCount++;
            }
          }
          setUploadProgress(`Importing ${i + 1} / ${normalizedRows.length} records...`);
        }

        setUploadSuccess(`Successfully imported ${savedCount} grades!${duplicateCount > 0 ? ` (${duplicateCount} duplicate records skipped)` : ''}`);
        setUploadProgress(null);
        fetchResults();
      } catch (err) {
        console.error('File parsing error:', err);
        setUploadError(err.message || 'Failed to process file. Make sure headers are correct.');
        setUploadProgress(null);
      }
    };

    if (file.name.endsWith('.csv')) {
      reader.readAsArrayBuffer(file);
    } else {
      reader.readAsBinaryString(file);
    }
  };

  const triggerFileSelect = () => {
    fileInputRef.current.click();
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
        <h2 className="page-title">📤 Current Subject Grades</h2>
        <p className="page-subtitle">
          Add or upload scores for {user.class_level} ({user.department || 'General'} department)
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

      {/* Ledger Section */}
      <div style={{ background: 'var(--glass-bg)', borderRadius: '24px', padding: '28px', border: '1px solid var(--glass-border)', boxShadow: 'var(--shadow-md)', marginBottom: '32px' }}>
        <h3 className="rec-card-title">📂 Current Grade Ledger</h3>
        
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
            <div className="spinner spinner-dark" />
          </div>
        ) : totalRecords > 0 ? (
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
                {results.map((row) => (
                  <tr key={row.id}>
                    <td style={{ fontWeight: 600 }}>{row.subject}</td>
                    <td>{row.score}%</td>
                    <td>
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontWeight: 700,
                        fontSize: '0.85rem',
                        backgroundColor: row.score >= 75 ? 'rgba(16, 185, 129, 0.1)' : row.score >= 50 ? 'rgba(45, 99, 184, 0.1)' : 'rgba(244, 63, 94, 0.1)',
                        color: row.score >= 75 ? 'var(--emerald-600)' : row.score >= 50 ? '#C9FFE5' : 'var(--rose-500)'
                      }}>
                        {scoreToGrade(row.score)}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '6px', color: 'var(--rose-500)', borderColor: 'rgba(244, 63, 94, 0.2)', background: 'transparent' }}
                        onClick={() => handleDelete(row.id)}
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '40px 20px', border: '2px dashed rgba(255,255,255,0.18)', borderRadius: '20px', background: 'rgba(255, 255, 255, 0.05)' }}>
            <div style={{ display: 'flex', justifyContent: 'center' }}><FileSpreadsheet size={48} style={{ color: 'var(--primary-500)', marginBottom: '12px' }} /></div>
            <h4 style={{ color: 'var(--text-light)', margin: '12px 0 6px 0', fontWeight: 700 }}>No Subject Grades Recorded Yet</h4>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', maxWidth: '380px', margin: '0 auto' }}>
              Add your current department subject scores below or upload an Excel sheet to analyze your academic competencies.
            </p>
          </div>
        )}
      </div>

      {/* Excel / CSV File Uploader */}
      <div style={{ background: 'var(--glass-bg)', borderRadius: '24px', padding: '28px', border: '1px solid var(--glass-border)', boxShadow: 'var(--shadow-md)', marginBottom: '32px' }}>
        <h3 className="rec-card-title">📊 Import Grades from Spreadsheet</h3>
        <p style={{ fontSize: '0.88rem', color: 'var(--slate-400)', marginBottom: '20px' }}>
          Drop your school report Excel sheet or CSV file here to upload all grades instantly.
        </p>

        {uploadProgress && (
          <div className="alert-banner alert-banner-info" style={{ marginBottom: '16px' }}>
            <div className="spinner spinner-dark" style={{ flexShrink: 0, borderTopColor: 'var(--primary-500)' }} />
            <span>{uploadProgress}</span>
          </div>
        )}
        {uploadError && (
          <div className="alert-banner alert-banner-warning" style={{ marginBottom: '16px' }}>
            <AlertCircle size={20} style={{ flexShrink: 0 }} />
            <span>{uploadError}</span>
          </div>
        )}
        {uploadSuccess && (
          <div className="alert-banner alert-banner-success" style={{ marginBottom: '16px' }}>
            <CheckCircle size={20} style={{ flexShrink: 0 }} />
            <span>{uploadSuccess}</span>
          </div>
        )}

        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileUpload}
          accept=".xlsx, .xls, .csv"
          style={{ display: 'none' }}
        />

        <div className="upload-dropzone" onClick={triggerFileSelect}>
          <Upload size={36} style={{ color: 'var(--primary-500)', marginBottom: '12px' }} />
          <h4 style={{ fontWeight: 700, color: '#8897BD', fontSize: '1rem' }}>Click or Drag File to Upload</h4>
          <p style={{ fontSize: '0.8rem', color: 'var(--slate-400)', marginTop: '4px' }}>
            Supports Excel (.xlsx, .xls) and CSV (.csv) reports. Header fields must contain: <strong>Subject</strong>, <strong>Score</strong>.
          </p>
        </div>
      </div>

      {/* Manual Input Form */}
      <div style={{ background: 'var(--glass-bg)', borderRadius: '24px', padding: '28px', border: '1px solid var(--glass-border)', boxShadow: 'var(--shadow-md)' }}>
        <h3 className="rec-card-title">✍️ Add Grade Manually</h3>
        
        {formError && (
          <div className="alert-banner alert-banner-warning" style={{ marginBottom: '16px' }}>
            <AlertCircle size={20} style={{ flexShrink: 0 }} />
            <span>{formError}</span>
          </div>
        )}
        {formSuccess && (
          <div className="alert-banner alert-banner-success" style={{ marginBottom: '16px' }}>
            <CheckCircle size={20} style={{ flexShrink: 0 }} />
            <span>{formSuccess}</span>
          </div>
        )}

        <form onSubmit={handleManualSubmit} style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div className="form-group" style={{ flex: 2, minWidth: '200px', marginBottom: 0 }}>
            <label className="form-label">Select Subject</label>
            <select
              className="form-select"
              value={selectedSubject}
              onChange={(e) => setSelectedSubject(e.target.value)}
            >
              <option value="">-- Choose Subject --</option>
              {subjectList.map((subj) => (
                <option key={subj} value={subj}>{subj}</option>
              ))}
            </select>
          </div>

          <div className="form-group" style={{ flex: 1, minWidth: '120px', marginBottom: 0 }}>
            <label className="form-label">Score (0-100)</label>
            <input
              type="number"
              step="any"
              className="form-input"
              placeholder="e.g. 85.5"
              value={manualScore}
              onChange={(e) => setManualScore(e.target.value)}
            />
          </div>

          <button type="submit" className="btn btn-primary" style={{ padding: '12px 24px', height: '46px' }}>
            <PlusCircle size={18} /> Save Grade
          </button>
        </form>
      </div>
    </div>
  );
};

export default Grades;
