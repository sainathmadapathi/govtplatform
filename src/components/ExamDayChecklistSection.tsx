import React, { useState, useEffect } from 'react';
import { 
  CheckSquare, Square, ShieldCheck, AlertTriangle, Clock, 
  FileText, Ban, CheckCircle2, AlertCircle, Sparkles, RefreshCw,
  Eye, Zap, Camera, Lock, UserCheck
} from 'lucide-react';
import { Exam } from '../types/exam';

interface ExamDayChecklistSectionProps {
  exam: Exam;
}

interface ChecklistItem {
  id: string;
  category: 'DOCUMENTS' | 'TIMING' | 'ITEMS_ALLOWED' | 'ITEMS_PROHIBITED' | 'CENTRE_RULES';
  title: string;
  description: string;
  isCrucial: boolean;
}

export const ExamDayChecklistSection: React.FC<ExamDayChecklistSectionProps> = ({ exam }) => {
  const storageKey = `govos_checklist_${exam.id}`;

  const defaultItems: ChecklistItem[] = [
    // 1. Documents
    {
      id: 'doc-admit',
      category: 'DOCUMENTS',
      title: 'Printed Copy of Official e-Admit Card (Clear & Unsmudged)',
      description: 'Ensure the candidate barcode, roll number, and photograph are sharply printed. Color or B&W laser printout is accepted.',
      isCrucial: true
    },
    {
      id: 'doc-photos',
      category: 'DOCUMENTS',
      title: '2 Recent Passport-Sized Colour Photographs',
      description: 'Must match or closely resemble the photo uploaded during application. Paste one on the commission copy inside the lab.',
      isCrucial: true
    },
    {
      id: 'doc-original-id',
      category: 'DOCUMENTS',
      title: 'Original Valid Government Photo ID Proof (Original Only)',
      description: 'Accepted: Aadhaar Card / e-Aadhaar printout, Voter ID, Driving License, PAN Card, or Passport. Photocopies or digital phone screenshots are strictly NOT accepted.',
      isCrucial: true
    },
    {
      id: 'doc-dob-proof',
      category: 'DOCUMENTS',
      title: 'Secondary DoB Certificate (If ID lacks complete DD/MM/YYYY)',
      description: 'If your Aadhaar/PAN only mentions the year of birth (YYYY), you MUST carry your Original Class 10th Certificate or Birth Certificate as proof of full date of birth.',
      isCrucial: true
    },
    {
      id: 'doc-scribe',
      category: 'DOCUMENTS',
      title: 'PwD Disability Certificate & Scribe Approval Letter (If Applicable)',
      description: 'Original medical certificate and official scribe proforma in the prescribed Annexure format.',
      isCrucial: false
    },

    // 2. Timing & Centre Protocol
    {
      id: 'time-reporting',
      category: 'TIMING',
      title: 'Arrival 90 Minutes Prior to Exam Start',
      description: 'Arrive at the examination venue at the specified Reporting Time. Biometric iris and thumb scan takes up to 20-30 minutes per candidate batch.',
      isCrucial: true
    },
    {
      id: 'time-gate-closing',
      category: 'TIMING',
      title: 'Strict Gate Closing Policy (No Entry After Deadline)',
      description: 'Examination center gates are locked exactly 30 minutes before exam commencement. Server login locks automatically under central CCTV audit.',
      isCrucial: true
    },

    // 3. Allowed Items
    {
      id: 'item-pen',
      category: 'ITEMS_ALLOWED',
      title: 'Transparent Body Blue or Black Ballpoint Pen',
      description: 'Pen with clear barrel. Gel pens or fountain pens are not recommended for signing biometric slips.',
      isCrucial: false
    },
    {
      id: 'item-water',
      category: 'ITEMS_ALLOWED',
      title: 'Transparent Water Bottle (500ml, Without Sticker/Label)',
      description: 'Bottles with wrappers or opaque colored plastic are prohibited.',
      isCrucial: false
    },
    {
      id: 'item-sanitizer',
      category: 'ITEMS_ALLOWED',
      title: 'Small Transparent Hand Sanitizer Bottle (50ml)',
      description: 'Optional personal hygiene bottle.',
      isCrucial: false
    },

    // 4. Prohibited Items
    {
      id: 'ban-electronics',
      category: 'ITEMS_PROHIBITED',
      title: 'Mobile Phones, Smartwatches, Bluetooth & Earphones',
      description: 'Strictly prohibited. Possession of any electronic device inside the exam zone leads to immediate cancellation and a 3-5 year debarment.',
      isCrucial: true
    },
    {
      id: 'ban-metallic',
      category: 'ITEMS_PROHIBITED',
      title: 'Metallic Accessories, Belts with Large Buckles & Wallets',
      description: 'Metal detectors frisk all candidates. Avoid belts with heavy brass buckles, key rings, coins, or metallic hairpins.',
      isCrucial: false
    },
    {
      id: 'ban-stationery',
      category: 'ITEMS_PROHIBITED',
      title: 'Bags, Books, Notes, Paper Scraps & Calculators',
      description: 'Rough sheets are provided inside the computer lab. Carrying personal blank sheets is considered unfair means (UFM).',
      isCrucial: true
    },

    // 5. CBT Lab Protocol
    {
      id: 'lab-mouse-test',
      category: 'CENTRE_RULES',
      title: 'Verify Mouse & Keyboard During Buffer Time',
      description: 'Before the exam countdown begins, test that the left mouse click, right click, and scroll wheel are fully functional on the virtual test screen.',
      isCrucial: false
    },
    {
      id: 'lab-rough-sheet',
      category: 'CENTRE_RULES',
      title: 'Write Roll No & Name on Rough Sheet Immediately',
      description: 'Sign your allocated rough sheets and submit them into the collection box before exiting the examination hall.',
      isCrucial: false
    }
  ];

  const [checkedIds, setCheckedIds] = useState<Record<string, boolean>>(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) return JSON.parse(saved);
    } catch (e) {
      console.warn('Checklist localstorage read error:', e);
    }
    return {
      'doc-admit': true,
      'doc-photos': true,
      'doc-original-id': true
    };
  });

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(checkedIds));
    } catch (e) {
      console.warn('Checklist localstorage save error:', e);
    }
  }, [checkedIds, storageKey]);

  const toggleCheck = (id: string) => {
    setCheckedIds(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const handleResetChecklist = () => {
    setCheckedIds({});
  };

  const totalItems = defaultItems.length;
  const completedCount = defaultItems.filter(i => checkedIds[i.id]).length;
  const progressPercent = Math.round((completedCount / totalItems) * 100);

  const categories = [
    { key: 'DOCUMENTS', name: '1. Mandatory Documents to Carry', icon: FileText, color: '#60a5fa' },
    { key: 'TIMING', name: '2. Reporting Schedule & Strict Gate Closing', icon: Clock, color: '#f59e0b' },
    { key: 'ITEMS_ALLOWED', name: '3. Allowed Physical Items', icon: CheckCircle2, color: '#34d399' },
    { key: 'ITEMS_PROHIBITED', name: '4. Strictly Prohibited Articles (Debarment Risk)', icon: Ban, color: '#ef4444' },
    { key: 'CENTRE_RULES', name: '5. Computer Lab & CBT Examination Protocols', icon: ShieldCheck, color: 'var(--primary)' }
  ];

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Top Banner with Packing Progress Bar */}
      <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(17, 24, 39, 0.95) 100%)', borderColor: 'rgba(99, 102, 241, 0.35)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span className="badge badge-verified">
                <ShieldCheck size={14} /> OFFICIAL EXAM-DAY PROTOCOL
              </span>
              <span className="badge badge-demo">
                {exam.code}
              </span>
            </div>

            <h3 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'white', margin: '0 0 4px' }}>
              Candidate Exam-Day Readiness Checklist
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
              Physically tick off items as you pack your exam kit. Never get turned away at the entry gate.
            </p>
          </div>

          <button 
            className="btn btn-secondary"
            onClick={handleResetChecklist}
            style={{ fontSize: '0.8rem', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={14} /> Reset Checks
          </button>
        </div>

        {/* Live Progress Bar */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.85rem' }}>
            <span style={{ color: '#e2e8f0', fontWeight: 600 }}>
              Packing & Verification Status: <strong style={{ color: progressPercent === 100 ? '#34d399' : 'var(--primary)' }}>{completedCount} of {totalItems} confirmed</strong>
            </span>
            <span style={{ fontWeight: 800, color: progressPercent === 100 ? '#34d399' : 'var(--primary)' }}>
              {progressPercent}% READY
            </span>
          </div>

          <div style={{ width: '100%', height: '8px', borderRadius: '4px', background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
            <div 
              style={{ 
                width: `${progressPercent}%`, 
                height: '100%', 
                background: progressPercent === 100 ? 'var(--emerald)' : 'linear-gradient(90deg, #6366f1 0%, #10b981 100%)', 
                transition: 'width 0.3s ease' 
              }} 
            />
          </div>

          {progressPercent === 100 && (
            <div className="animate-fade-in" style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: '#34d399' }}>
              <Sparkles size={16} /> All mandatory documents and items packed! Best wishes for your examination.
            </div>
          )}
        </div>
      </div>

      {/* Shift Timing Reference Table */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <h4 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'white', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Clock size={18} color="var(--amber)" /> Standard Shift Timings & Gate Closing Deadlines
        </h4>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '10px 14px' }}>Shift</th>
                <th style={{ padding: '10px 14px' }}>Reporting Time</th>
                <th style={{ padding: '10px 14px', color: '#f87171' }}>Gate Closing (Strict)</th>
                <th style={{ padding: '10px 14px' }}>Exam Timing (1 Hour CBT)</th>
              </tr>
            </thead>
            <tbody>
              {[
                { shift: 'Shift 1 (Morning)', rep: '07:45 AM', close: '08:30 AM', exam: '09:00 AM – 10:00 AM' },
                { shift: 'Shift 2 (Noon)', rep: '10:30 AM', close: '11:15 AM', exam: '11:45 AM – 12:45 PM' },
                { shift: 'Shift 3 (Afternoon)', rep: '01:15 PM', close: '02:00 PM', exam: '02:30 PM – 03:30 PM' },
                { shift: 'Shift 4 (Evening)', rep: '04:00 PM', close: '04:45 PM', exam: '05:15 PM – 06:15 PM' }
              ].map(s => (
                <tr key={s.shift} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <td style={{ padding: '12px 14px', fontWeight: 600, color: 'white' }}>{s.shift}</td>
                  <td style={{ padding: '12px 14px', color: 'var(--text-secondary)' }}>{s.rep}</td>
                  <td style={{ padding: '12px 14px', fontWeight: 700, color: '#f87171' }}>{s.close}</td>
                  <td style={{ padding: '12px 14px', fontWeight: 600, color: '#93c5fd' }}>{s.exam}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Categorized Checklists */}
      {categories.map(cat => {
        const items = defaultItems.filter(i => i.category === cat.key);
        const CatIcon = cat.icon;

        return (
          <div key={cat.key} className="glass-card" style={{ padding: '24px' }}>
            <h4 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'white', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CatIcon size={18} color={cat.color} /> {cat.name}
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {items.map(item => {
                const isChecked = Boolean(checkedIds[item.id]);

                return (
                  <div
                    key={item.id}
                    onClick={() => toggleCheck(item.id)}
                    style={{
                      padding: '14px 18px',
                      borderRadius: 'var(--radius-md)',
                      background: isChecked ? 'rgba(16, 185, 129, 0.05)' : 'rgba(255, 255, 255, 0.02)',
                      border: isChecked ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--border-color)',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '14px',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <div style={{ marginTop: '2px', color: isChecked ? 'var(--emerald)' : 'var(--text-muted)' }}>
                      {isChecked ? <CheckSquare size={20} /> : <Square size={20} />}
                    </div>

                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <div style={{ 
                          fontSize: '0.95rem', 
                          fontWeight: 700, 
                          color: isChecked ? '#e2e8f0' : 'white',
                          textDecoration: isChecked ? 'line-through' : 'none'
                        }}>
                          {item.title}
                        </div>
                        {item.isCrucial && (
                          <span className="badge" style={{ fontSize: '0.65rem', background: 'rgba(239, 68, 68, 0.2)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.4)' }}>
                            MANDATORY
                          </span>
                        )}
                      </div>

                      <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: '4px 0 0', lineHeight: 1.45 }}>
                        {item.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

    </div>
  );
};
