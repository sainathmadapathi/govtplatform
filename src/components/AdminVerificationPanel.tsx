import React, { useState } from 'react';
import { Terminal, ShieldCheck, RefreshCw, AlertTriangle, FileText, CheckCircle2, XCircle, Database, Lock, Eye } from 'lucide-react';
import { SourceHealthLog } from '../types/exam';

interface AdminVerificationPanelProps {
  onOpenProvenanceModal: (provenance: any) => void;
}

export const AdminVerificationPanel: React.FC<AdminVerificationPanelProps> = ({ onOpenProvenanceModal }) => {
  const [activeTab, setActiveTab] = useState<'HEALTH' | 'EXTRACTION' | 'CORRIGENDUM' | 'REPORTS'>('HEALTH');
  
  const [healthLogs, setHealthLogs] = useState<SourceHealthLog[]>([
    {
      id: 'sh-01',
      endpointUrl: 'https://ssc.gov.in/api/attachment/notice/ssc_cgl_2026_notification.pdf',
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
      endpointUrl: 'https://ssc.gov.in/api/attachment/notice/cgl_2026_corrigendum_02.pdf',
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
