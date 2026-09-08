import React, { useState } from 'react';
import { 
  Calendar, Download, ExternalLink, ShieldCheck, AlertCircle, 
  CheckCircle2, Clock, MapPin, User, FileText, Check, ArrowRight,
  Info, QrCode, Printer, AlertTriangle, Layers, Compass
} from 'lucide-react';
import { Exam } from '../types/exam';

interface AdmitCardSectionProps {
  exam: Exam;
  onNavigateChecklist?: () => void;
}

export const AdmitCardSection: React.FC<AdmitCardSectionProps> = ({
  exam,
  onNavigateChecklist
}) => {
  const [selectedRegion, setSelectedRegion] = useState<string>('NR');

  // Find admit card date from dates array
  const admitDate = exam.dates.find(d => d.type === 'ADMIT_CARD');
  const cityIntimationDate = exam.dates.find(d => d.label.toLowerCase().includes('city') || d.type === 'ADMIT_CARD');
  const examDate = exam.dates.find(d => d.type === 'EXAM_TIER1' || d.type === 'EXAM_TIER2');

  // Admit-card facts declared on the exam record (falls back to the dates array)
  const admitDetails = exam.admitCardDetails;

  // Determine availability status
  const isAvailable = admitDetails?.status === 'AVAILABLE' || admitDate?.status === 'AVAILABLE';
  const releaseDateStr = admitDetails?.releaseDateStr || admitDate?.dateTimeStr || 'To be announced';

  // Regional download mirrors are authority-specific, so they come from the exam
  // record. Exams without declared mirrors show only their single official portal.
  const regionalPortals = (admitDetails?.regionPortals || []).map(rp => ({
    code: rp.regionCode,
    name: rp.statesCovered ? `${rp.regionName} (${rp.statesCovered})` : rp.regionName,
    url: rp.portalUrl,
    status: rp.status
  }));

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Title & Live Status Banner */}
      <div 
        className="glass-card" 
        style={{ 
          padding: '24px', 
          background: isAvailable 
            ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(17, 24, 39, 0.95) 100%)'
            : 'linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(17, 24, 39, 0.95) 100%)',
          borderColor: isAvailable ? 'rgba(16, 185, 129, 0.35)' : 'rgba(245, 158, 11, 0.35)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
              <span className={`badge ${isAvailable ? 'badge-verified' : 'badge-demo'}`}>
                {isAvailable ? '🟢 ADMIT CARD ACTIVE & DOWNLOADABLE' : '🟡 CITY INTIMATION RELEASED — ADMIT CARD SOON'}
              </span>
              <span className="badge" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--text-secondary)' }}>
                Official Board: {exam.authorityName}
              </span>
            </div>

            <h3 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'white', margin: '0 0 6px' }}>
              e-Admit Card & Exam City Intimation Slip
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
              {isAvailable 
                ? 'Your Computer Based Examination (CBT) Call Letter and reporting schedule are live.'
                : `Official admit cards are scheduled for release on ${releaseDateStr}. You can check your exam city intimation slip now.`}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <a 
              href={exam.officialDomain} 
              target="_blank" 
              rel="noreferrer"
              className="btn btn-emerald"
              style={{ fontSize: '0.9rem', padding: '10px 20px', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <Download size={18} /> Official Download Portal <ExternalLink size={14} />
            </a>
          </div>
        </div>
      </div>

      {/* Grid: Instructions & Download Credentials */}
      <div className="grid-2" style={{ gap: '20px' }}>
        
        {/* Box 1: How to Download & Required Credentials */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <h4 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'white', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck size={18} color="var(--primary)" /> Required Login Credentials
          </h4>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
            To access your hall ticket from the official {exam.authorityName.split(' ')[0]} server, keep the following credentials ready:
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ padding: '12px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <User size={16} color="var(--cyan)" />
              <div>
                <strong style={{ fontSize: '0.88rem', color: 'white' }}>Registration Number / Roll Number</strong>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Received via SMS / Email during initial application submission</div>
              </div>
            </div>

            <div style={{ padding: '12px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Calendar size={16} color="var(--emerald)" />
              <div>
                <strong style={{ fontSize: '0.88rem', color: 'white' }}>Date of Birth (Password)</strong>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Format: DD/MM/YYYY or as chosen during registration</div>
              </div>
            </div>

            <div style={{ padding: '12px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <FileText size={16} color="#fbbf24" />
              <div>
                <strong style={{ fontSize: '0.88rem', color: 'white' }}>Live Photo & Mother's Name (Alternative Fallback)</strong>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>If Registration ID is misplaced, use Candidate Name + Father/Mother Name + DoB</div>
              </div>
            </div>
          </div>
        </div>

        {/* Box 2: Crucial Printing & Verification Guidelines */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <h4 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'white', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Printer size={18} color="#60a5fa" /> Essential Printing Rules
          </h4>

          <ul style={{ paddingLeft: '20px', margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '10px', lineHeight: 1.5 }}>
            <li>
              <strong style={{ color: 'white' }}>Print in High Resolution:</strong> Both Color or Laser Black & White prints are acceptable, but the <strong style={{ color: '#93c5fd' }}>QR Code / Barcode</strong> and candidate photograph must be crisp and easily scannable.
            </li>
            <li>
              <strong style={{ color: 'white' }}>Check Candidate Particulars:</strong> Verify Name spelling, Category, Sub-Category, and Date of Birth against your official Class 10th Certificate.
            </li>
            <li>
              <strong style={{ color: 'white' }}>Exam Lab & Shift Timing:</strong> Note the precise <strong style={{ color: '#f87171' }}>Reporting Time and Gate Closing Time</strong>. No candidate is permitted inside the examination center after gate closure.
            </li>
            <li>
              <strong style={{ color: 'white' }}>Self-Declaration Form:</strong> Complete the Covid / Scribe / Identity self-declaration paragraphs in your own handwriting <em>only inside the exam hall in front of the Invigilator</em>.
            </li>
          </ul>
        </div>
      </div>

      {/* Regional Zone Portals Selector — only for authorities that publish zonal mirrors */}
      {regionalPortals.length > 0 && (
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h4 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'white', margin: '0 0 4px' }}>
              Regional & Zonal Download Mirrors
            </h4>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: 0 }}>
              Official server mirrors divided by state jurisdictions for fast hall ticket downloads
            </p>
          </div>
          <span className="badge badge-verified" style={{ fontSize: '0.72rem' }}>
            {regionalPortals.length} ZONAL PORTALS VERIFIED
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
          {regionalPortals.map(rp => (
            <div 
              key={rp.code}
              style={{
                padding: '14px',
                borderRadius: 'var(--radius-md)',
                background: selectedRegion === rp.code ? 'rgba(99,102,241,0.1)' : 'rgba(255,255,255,0.02)',
                border: selectedRegion === rp.code ? '1px solid var(--primary)' : '1px solid var(--border-color)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '10px'
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span className="badge badge-demo" style={{ fontSize: '0.7rem' }}>REGION: {rp.code}</span>
                  <span style={{ fontSize: '0.7rem', color: '#34d399', fontWeight: 600 }}>Active Portal</span>
                </div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'white' }}>{rp.name}</div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '8px' }}>
                <code style={{ fontSize: '0.75rem', color: '#93c5fd' }}>{rp.url.replace('https://', '')}</code>
                <a 
                  href={rp.url} 
                  target="_blank" 
                  rel="noreferrer" 
                  className="btn btn-secondary" 
                  style={{ fontSize: '0.72rem', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  Visit <ExternalLink size={10} />
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>
      )}

      {/* Simulated Sample Admit Card Preview Mockup */}
      <div className="glass-card" style={{ padding: '24px', border: '1px dashed rgba(99, 102, 241, 0.4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <QrCode size={20} color="var(--primary)" />
            <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white', margin: 0 }}>
              Sample Hall Ticket Format Preview
            </h4>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Illustrative layout showing key fields on your official paper
          </span>
        </div>

        <div style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.4)', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '16px' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Candidate Name</span>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'white' }}>CANDIDATE ASPIRANT</div>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Roll Number / User ID</span>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--cyan)', fontFamily: 'var(--font-mono)' }}>2201048291</div>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Exam Date & Shift</span>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#fbbf24' }}>
                {examDate?.dateTimeStr.split(' ')[0] || '28 Oct 2026'} (Shift 1: 09:00 - 10:00 AM)
              </div>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Reporting & Gate Closure</span>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f87171' }}>07:30 AM (Gate Closes: 08:30 AM Strict)</div>
            </div>
          </div>

          <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              <MapPin size={14} color="var(--primary)" />
              <span>Test Venue: iON Digital Zone iDZ, Central Assessment Centre Lab 4, New Delhi</span>
            </div>

            {onNavigateChecklist && (
              <button 
                className="btn btn-primary"
                onClick={onNavigateChecklist}
                style={{ fontSize: '0.8rem', padding: '6px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                Go to Exam-Day Checklist <ArrowRight size={14} />
              </button>
            )}
          </div>
        </div>
      </div>

    </div>
  );
};
