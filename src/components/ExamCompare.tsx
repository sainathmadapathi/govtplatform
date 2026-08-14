import React, { useState } from 'react';
import { Scale, CheckCircle2, ShieldCheck, ChevronRight } from 'lucide-react';
import { ALL_EXAMS } from '../data/examsData';
import { Exam } from '../types/exam';

interface ExamCompareProps {
  onSelectExam: (exam: Exam) => void;
}

export const ExamCompare: React.FC<ExamCompareProps> = ({ onSelectExam }) => {
  const [exam1Id, setExam1Id] = useState<string>(ALL_EXAMS[0].id);
  const [exam2Id, setExam2Id] = useState<string>(ALL_EXAMS[1]?.id || ALL_EXAMS[0].id);

  const exam1 = ALL_EXAMS.find(e => e.id === exam1Id) || ALL_EXAMS[0];
  const exam2 = ALL_EXAMS.find(e => e.id === exam2Id) || ALL_EXAMS[1] || ALL_EXAMS[0];

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* Header */}
      <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(17, 24, 39, 0.9) 100%)', borderColor: 'rgba(168, 85, 247, 0.3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--purple)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
            <Scale size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800 }}>
              Side-by-Side Exam Comparison Matrix
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              Compare eligibility, pay scales, stages, difficulty, and competitive intensity across exams.
            </p>
          </div>
        </div>
      </div>

      {/* Selectors */}
      <div className="grid-2">
        <div>
          <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
            Select Exam 1
          </label>
          <select value={exam1Id} onChange={(e) => setExam1Id(e.target.value)} style={{ width: '100%', padding: '12px', borderRadius: 'var(--radius-md)', background: 'var(--bg-input)', border: '1px solid var(--border-color)', color: 'white', fontWeight: 600 }}>
            {ALL_EXAMS.map(e => <option key={e.id} value={e.id}>{e.title}</option>)}
          </select>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
            Select Exam 2
          </label>
          <select value={exam2Id} onChange={(e) => setExam2Id(e.target.value)} style={{ width: '100%', padding: '12px', borderRadius: 'var(--radius-md)', background: 'var(--bg-input)', border: '1px solid var(--border-color)', color: 'white', fontWeight: 600 }}>
            {ALL_EXAMS.map(e => <option key={e.id} value={e.id}>{e.title}</option>)}
          </select>
        </div>
      </div>

      {/* Comparison Matrix Table */}
      <div className="glass-card" style={{ padding: '24px', overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <th style={{ padding: '16px', color: 'var(--text-secondary)', fontSize: '0.9rem', width: '25%' }}>ATTRIBUTE</th>
              <th style={{ padding: '16px', color: 'white', fontSize: '1.1rem', width: '37.5%' }}>{exam1.title}</th>
              <th style={{ padding: '16px', color: 'white', fontSize: '1.1rem', width: '37.5%' }}>{exam2.title}</th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <td style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Conducting Authority</td>
              <td style={{ padding: '16px', fontWeight: 700 }}>{exam1.authorityName}</td>
              <td style={{ padding: '16px', fontWeight: 700 }}>{exam2.authorityName}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <td style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Minimum Age</td>
              <td style={{ padding: '16px' }}>18 Years</td>
              <td style={{ padding: '16px' }}>21 Years</td>
            </tr>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <td style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Maximum Age (General)</td>
              <td style={{ padding: '16px' }}>27 - 30 Years (Post-wise)</td>
              <td style={{ padding: '16px' }}>32 Years</td>
            </tr>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <td style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Education Requirement</td>
              <td style={{ padding: '16px' }}>Bachelor's Degree (Any Stream)</td>
              <td style={{ padding: '16px' }}>Bachelor's Degree (Any Stream)</td>
            </tr>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <td style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Pay Scale Grade</td>
              <td style={{ padding: '16px', color: '#34d399', fontWeight: 700 }}>Pay Level 4 to 8 (₹25.5K to ₹142K)</td>
              <td style={{ padding: '16px', color: '#34d399', fontWeight: 700 }}>Pay Level 10+ (Group A Officers)</td>
            </tr>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <td style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Selection Stages</td>
              <td style={{ padding: '16px' }}>Tier 1 (Prelims) + Tier 2 (Mains)</td>
              <td style={{ padding: '16px' }}>Prelims + Mains (Written) + Interview</td>
            </tr>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <td style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Competitive Intensity</td>
              <td style={{ padding: '16px' }}><span className="badge badge-changed">High (~2.5 Million Applicants)</span></td>
              <td style={{ padding: '16px' }}><span className="badge badge-superseded">Very High (~1.1 Million Applicants)</span></td>
            </tr>
            <tr>
              <td style={{ padding: '16px' }}>Action</td>
              <td style={{ padding: '16px' }}>
                <button className="btn btn-primary" onClick={() => onSelectExam(exam1)} style={{ fontSize: '0.8rem', padding: '6px 12px' }}>
                  Explore {exam1.title.split(' ')[0]} <ChevronRight size={14} />
                </button>
              </td>
              <td style={{ padding: '16px' }}>
                <button className="btn btn-primary" onClick={() => onSelectExam(exam2)} style={{ fontSize: '0.8rem', padding: '6px 12px' }}>
                  Explore {exam2.title.split(' ')[0]} <ChevronRight size={14} />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>
  );
};
