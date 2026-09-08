import React, { useState, useEffect } from 'react';
import { Terminal, ShieldCheck, RefreshCw, AlertTriangle, FileText, CheckCircle2, XCircle, Database, Lock, Eye } from 'lucide-react';
import { SourceHealthLog } from '../types/exam';
import { ALL_EXAMS } from '../data/examsData';

interface AdminVerificationPanelProps {
  onOpenProvenanceModal: (provenance: any) => void;
}

export const AdminVerificationPanel: React.FC<AdminVerificationPanelProps> = ({ onOpenProvenanceModal }) => {
  const [activeTab, setActiveTab] = useState<'HEALTH' | 'EXTRACTION' | 'CORRIGENDUM' | 'REPORTS'>('HEALTH');
  const [reports, setReports] = useState<any[]>([]);
  const [reportsStatus, setReportsStatus] = useState<'IDLE' | 'LOADING' | 'OFFLINE'>('IDLE');

  const loadReports = async () => {
    setReportsStatus('LOADING');
    try {
      const res = await fetch('/api/reports');
      if (res.ok) {
        const data = await res.json();
        setReports(Array.isArray(data.reports) ? data.reports : []);
        setReportsStatus('IDLE');
        return;
      }
    } catch {
      // server unreachable
    }
    setReportsStatus('OFFLINE');
  };

  useEffect(() => {
    if (activeTab === 'REPORTS') {
      loadReports();
    }
  }, [activeTab]);

  const handleResolveReport = async (id: number, status: 'RESOLVED' | 'REJECTED') => {
    try {
      await fetch(`/api/reports/${id}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      });
      setReports(prev => prev.map(r => (r.id === id ? { ...r, status } : r)));
    } catch {
      // offline: leave the row as-is
    }
  };

  
  const [healthLogs, setHealthLogs] = useState<SourceHealthLog[]>([
    {
      id: 'sh-01',
      endpointUrl: 'https://ssc.gov.in',
      authorityCode: 'SSC',
      httpStatus: 200,
      checkedAt: '2026-08-14 20:30:00 UTC',
      rawContentHash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      normalizedContentHash: '7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
      textChanged: false,
      adminReviewStatus: 'HEALTHY'
    },
    {
      id: 'sh-02',
      endpointUrl: 'https://ssc.gov.in',
      authorityCode: 'SSC',
      httpStatus: 200,
      checkedAt: '2026-08-22 14:15:00 UTC',
      rawContentHash: '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8',
      normalizedContentHash: 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
      textChanged: true,
      adminReviewStatus: 'CONFLICT_DETECTED',
      previousValue: 'Application Deadline: 20 September 2026',
      newValue: 'Application Deadline: 27 September 2026'
    },
    {
      id: 'sh-03',
      endpointUrl: 'https://upsc.gov.in/examinations/active-exams',
      authorityCode: 'UPSC',
      httpStatus: 200,
      checkedAt: '2026-08-14 18:00:00 UTC',
      rawContentHash: '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a',
      normalizedContentHash: 'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d',
      textChanged: false,
      adminReviewStatus: 'HEALTHY'
    }
  ]);

  // Every corrigendum published across the verified exam register.
  const allCorrigenda = ALL_EXAMS.flatMap(exam =>
    exam.corrigendums.map(c => ({ ...c, examTitle: exam.title, examCode: exam.code }))
  );
  const openConflicts = healthLogs.filter(l => l.adminReviewStatus === 'CONFLICT_DETECTED');

  const handleApproveConflict = (id: string) => {
    setHealthLogs(prev => prev.map(log => log.id === id ? { ...log, adminReviewStatus: 'REVIEWED', textChanged: false } : log));
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* Header Banner */}
      <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(17, 24, 39, 0.95) 100%)', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{ width: '42px', height: '42px', borderRadius: '12px', background: 'var(--emerald)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
              <Terminal size={24} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.5rem', fontWeight: 800 }}>
                Trust Pipeline & Source Health Monitoring Console
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                Multi-layer SHA-256 hash checks, official domain security boundary, and human verifier approval workflow.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <span className="badge badge-verified" style={{ padding: '6px 12px' }}>
              <Lock size={14} /> SECURITY BOUNDARY ACTIVE
            </span>
          </div>
        </div>
      </div>

      {/* Admin Tabs */}
      <div style={{ display: 'flex', gap: '8px' }}>
        <button className={`btn ${activeTab === 'HEALTH' ? 'btn-emerald' : 'btn-secondary'}`} onClick={() => setActiveTab('HEALTH')} style={{ fontSize: '0.85rem' }}>
          <RefreshCw size={16} /> Source Health Monitor (SHA-256)
        </button>
        <button className={`btn ${activeTab === 'CORRIGENDUM' ? 'btn-emerald' : 'btn-secondary'}`} onClick={() => setActiveTab('CORRIGENDUM')} style={{ fontSize: '0.85rem' }}>
          <AlertTriangle size={16} /> Corrigendum & Conflict Queue
        </button>
        <button className={`btn ${activeTab === 'REPORTS' ? 'btn-emerald' : 'btn-secondary'}`} onClick={() => setActiveTab('REPORTS')} style={{ fontSize: '0.85rem' }}>
          <FileText size={16} /> Candidate Accuracy Reports
        </button>
        <button className={`btn ${activeTab === 'EXTRACTION' ? 'btn-emerald' : 'btn-secondary'}`} onClick={() => setActiveTab('EXTRACTION')} style={{ fontSize: '0.85rem' }}>
          <Database size={16} /> AI PDF Extraction Simulator
        </button>
      </div>

      {/* Subsystem 8 View: Source Health Log */}
      {activeTab === 'HEALTH' && (
        <div className="glass-card" style={{ padding: '28px' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <RefreshCw size={20} color="var(--emerald)" /> Monitored Official Source Endpoints ({healthLogs.length})
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {healthLogs.map(log => (
              <div 
                key={log.id} 
                style={{ 
                  padding: '20px', 
                  borderRadius: 'var(--radius-md)', 
                  background: log.adminReviewStatus === 'CONFLICT_DETECTED' ? 'rgba(245, 158, 11, 0.08)' : 'rgba(255,255,255,0.03)',
                  border: `1px solid ${log.adminReviewStatus === 'CONFLICT_DETECTED' ? 'rgba(245, 158, 11, 0.4)' : 'var(--border-color)'}`
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', flexWrap: 'wrap', gap: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span className="badge badge-verified" style={{ fontFamily: 'var(--font-mono)' }}>{log.authorityCode}</span>
                    <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'white', wordBreak: 'break-all' }}>{log.endpointUrl}</span>
                  </div>

                  <span className={`badge ${log.adminReviewStatus === 'HEALTHY' ? 'badge-verified' : 'badge-changed'}`}>
                    {log.adminReviewStatus}
                  </span>
                </div>

                {log.textChanged && log.previousValue && (
                  <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', marginBottom: '14px' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fbbf24', marginBottom: '4px' }}>
                      🚨 SHA-256 Hash Divergence Detected (Corrigendum Event)
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#fef3c7' }}>
                      Old Fact: <span style={{ textDecoration: 'line-through' }}>{log.previousValue}</span>
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#34d399', fontWeight: 700 }}>
                      New Fact: {log.newValue}
                    </div>
                  </div>
                )}

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  <div>
                    HTTP Status: <strong style={{ color: '#34d399' }}>{log.httpStatus} OK</strong> | Last Checked: {log.checkedAt}
                  </div>
                  <div>
                    DOM Hash: {log.normalizedContentHash.slice(0, 16)}...
                  </div>

                  {log.adminReviewStatus === 'CONFLICT_DETECTED' && (
                    <button className="btn btn-emerald" onClick={() => handleApproveConflict(log.id)} style={{ fontSize: '0.75rem', padding: '6px 12px' }}>
                      Approve & Publish Corrigendum V2 <CheckCircle2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Corrigendum & Conflict Queue */}
      {activeTab === 'CORRIGENDUM' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

          {/* Unresolved hash divergences awaiting a human verifier */}
          <div className="glass-card" style={{ padding: '28px' }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={20} color="var(--amber)" /> Unresolved Source Conflicts ({openConflicts.length})
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: '18px' }}>
              Endpoints whose normalized content hash changed since the last audit. Each must be approved by a human verifier before the revised fact is published to candidates.
            </p>

            {openConflicts.length === 0 ? (
              <div style={{ padding: '28px', textAlign: 'center', borderRadius: 'var(--radius-md)', background: 'rgba(16, 185, 129, 0.06)', border: '1px solid rgba(16, 185, 129, 0.25)' }}>
                <CheckCircle2 size={32} color="var(--emerald)" style={{ marginBottom: '8px' }} />
                <div style={{ fontWeight: 800, color: 'white', marginBottom: '4px' }}>No Open Conflicts</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  Every monitored official endpoint matches its last verified snapshot.
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {openConflicts.map(log => (
                  <div key={log.id} style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.4)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span className="badge badge-verified" style={{ fontFamily: 'var(--font-mono)' }}>{log.authorityCode}</span>
                        <span style={{ fontWeight: 700, color: 'white', wordBreak: 'break-all' }}>{log.endpointUrl}</span>
                      </div>
                      <span className="badge badge-changed">{log.adminReviewStatus}</span>
                    </div>

                    <div style={{ fontSize: '0.85rem', color: '#fef3c7', marginBottom: '4px' }}>
                      Old Fact: <span style={{ textDecoration: 'line-through' }}>{log.previousValue}</span>
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#34d399', fontWeight: 700, marginBottom: '12px' }}>
                      New Fact: {log.newValue}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      <span>Detected: {log.checkedAt} | DOM Hash: {log.normalizedContentHash.slice(0, 16)}...</span>
                      <button className="btn btn-emerald" onClick={() => handleApproveConflict(log.id)} style={{ fontSize: '0.75rem', padding: '6px 12px' }}>
                        Approve &amp; Publish Corrigendum V2 <CheckCircle2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Corrigenda already published to candidate-facing guides */}
          <div className="glass-card" style={{ padding: '28px' }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={20} color="var(--primary)" /> Published Corrigenda Register ({allCorrigenda.length})
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: '18px' }}>
              Official amendment notices already verified and live on candidate exam guides.
            </p>

            {allCorrigenda.length === 0 ? (
              <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                No corrigenda have been published for the exams currently in the register.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {allCorrigenda.map(c => (
                  <div key={c.examCode + '-' + c.id} style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)' }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '8px' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
                          <span className="badge badge-demo" style={{ fontSize: '0.7rem' }}>{c.examCode}</span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{c.noticeNumber}</span>
                        </div>
                        <div style={{ fontSize: '1rem', fontWeight: 700, color: 'white' }}>{c.title}</div>
                      </div>
                      <span className={c.status === 'ACTIVE' ? 'badge badge-verified' : 'badge badge-superseded'}>{c.status}</span>
                    </div>

                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px', lineHeight: 1.5 }}>
                      {c.summary}
                    </div>

                    <div style={{ padding: '10px 14px', borderRadius: 'var(--radius-sm)', background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.25)', fontSize: '0.82rem', color: '#fef3c7', marginBottom: '10px' }}>
                      <strong>Change Applied:</strong> {c.diffSummary}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      <span>Published: {c.publishedDate} | Effective: {c.effectiveDate}</span>
                      <a href={c.pdfUrl} target="_blank" rel="noreferrer" className="btn btn-outline" style={{ fontSize: '0.72rem', padding: '4px 10px' }}>
                        <Eye size={12} /> Open Official Notice
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Candidate-Submitted Accuracy Reports */}
      {activeTab === 'REPORTS' && (
        <div className="glass-card" style={{ padding: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: '18px' }}>
            <div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={20} color="var(--primary)" /> Candidate Accuracy Reports ({reports.length})
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', margin: 0 }}>
                Discrepancies flagged by candidates via Report Error, queued in the SQLite audit table for human verification.
              </p>
            </div>
            <button className="btn btn-secondary" onClick={loadReports} style={{ fontSize: '0.8rem' }}>
              <RefreshCw size={14} className={reportsStatus === 'LOADING' ? 'animate-spin' : ''} /> Refresh Queue
            </button>
          </div>

          {reportsStatus === 'OFFLINE' ? (
            <div style={{ padding: '24px', borderRadius: 'var(--radius-md)', background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.3)', fontSize: '0.88rem', color: '#fef3c7' }}>
              <strong>Audit database unreachable.</strong> Start the GovOS server (<code style={{ fontFamily: 'var(--font-mono)' }}>python app.py</code>) to load the report queue from govos.db.
            </div>
          ) : reports.length === 0 ? (
            <div style={{ padding: '28px', textAlign: 'center', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)' }}>
              <CheckCircle2 size={30} color="var(--emerald)" style={{ marginBottom: '8px' }} />
              <div style={{ fontWeight: 800, color: 'white', marginBottom: '4px' }}>Report Queue Empty</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                No candidate has flagged a data discrepancy yet.
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {reports.map(r => (
                <div key={r.id} style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span className="badge badge-demo" style={{ fontSize: '0.7rem' }}>{r.entityType}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{r.entityId}</span>
                    </div>
                    <span className={r.status === 'RESOLVED' ? 'badge badge-verified' : r.status === 'REJECTED' ? 'badge badge-superseded' : 'badge badge-pending'}>
                      {r.status}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.9rem', color: '#e2e8f0', lineHeight: 1.5, marginBottom: '10px' }}>
                    {r.description || <em style={{ color: 'var(--text-muted)' }}>No description provided.</em>}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <span>Submitted: {r.submittedAt}</span>
                    {r.status === 'PENDING_REVIEW' && (
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button className="btn btn-emerald" onClick={() => handleResolveReport(r.id, 'RESOLVED')} style={{ fontSize: '0.72rem', padding: '4px 10px' }}>
                          <CheckCircle2 size={12} /> Mark Resolved
                        </button>
                        <button className="btn btn-secondary" onClick={() => handleResolveReport(r.id, 'REJECTED')} style={{ fontSize: '0.72rem', padding: '4px 10px' }}>
                          <XCircle size={12} /> Reject
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* PDF Extraction Simulator */}
      {activeTab === 'EXTRACTION' && (
        <div className="glass-card" style={{ padding: '28px' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '16px' }}>AI Notification PDF Ingestion Simulator</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>
            Simulates PDF download → OCR text extraction → JSON schema mapping → Admin verification queue.
          </p>

          <div style={{ background: 'var(--bg-input)', padding: '20px', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: '#34d399', lineHeight: 1.6, overflowX: 'auto' }}>
{`{
  "authority": "SSC",
  "document_title": "SSC CGL 2026 Official Notification.pdf",
  "published_date": "2026-08-10",
  "extracted_schema": {
    "age_limit_min": 18,
    "age_limit_max": 27,
    "age_cutoff_date": "2026-08-01",
    "application_start": "2026-08-15",
    "application_close": "2026-09-27",
    "clause_reference": "Section 3.1, Page 12"
  },
  "extraction_confidence": 0.994,
  "human_verification_status": "OFFICIALLY_VERIFIED"
}`}
          </div>
        </div>
      )}

    </div>
  );
};
