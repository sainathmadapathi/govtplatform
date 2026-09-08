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

  // --- Facts derived from the verified exam records, not hardcoded ---

  const minAgeOf = (exam: Exam) =>
    exam.posts.length > 0 ? Math.min(...exam.posts.map(p => p.minAge)) : null;

  const maxAgeOf = (exam: Exam) =>
    exam.posts.length > 0 ? Math.max(...exam.posts.map(p => p.maxAge)) : null;

  const ageRangeLabel = (exam: Exam) => {
    const lo = minAgeOf(exam);
    const hi = maxAgeOf(exam);
    if (lo === null || hi === null) return 'Not specified in register';
    const lows = Array.from(new Set(exam.posts.map(p => p.minAge)));
    const highs = Array.from(new Set(exam.posts.map(p => p.maxAge)));
    const suffix = lows.length > 1 || highs.length > 1 ? ' (varies by post)' : '';
    return lo + ' \u2013 ' + hi + ' Years' + suffix;
  };

  const qualificationLabel = (exam: Exam) => {
    switch (exam.minimumQualification) {
      case 'CLASS_10': return 'Class 10th Pass';
      case 'CLASS_12': return 'Class 12th Pass';
      case 'GRADUATION': return "Bachelor's Degree (Any Stream)";
      case 'POST_GRADUATION': return "Master's Degree";
      default: return 'See official notification';
    }
  };

  const payLevelLabel = (exam: Exam) => {
    const levels = Array.from(new Set(exam.posts.map(p => p.payLevel))).filter(Boolean);
    if (levels.length === 0) return 'Not specified in register';
    if (levels.length === 1) return levels[0];
    const levelNumber = (v: string) => {
      const m = v.match(/[0-9]+/);
      return m ? parseInt(m[0], 10) : 0;
    };
    const sorted = [...levels].sort((a, b) => levelNumber(a) - levelNumber(b));
    return levels.length + ' pay levels (' + sorted[0] + ' \u2013 ' + sorted[sorted.length - 1] + ')';
  };

  const stagesLabel = (exam: Exam) => {
    if (exam.stages.length === 0) return 'Not specified in register';
    return exam.stages.map(st => st.stageName.split(':')[0].trim()).join(' \u2192 ');
  };

  const physicalLabel = (exam: Exam) => {
    const count = exam.posts.filter(p => p.physicalRequired).length;
    if (count === 0) return 'Not required for any post';
    return 'Required for ' + count + ' of ' + exam.posts.length + ' posts';
  };

  const latestCutoffLabel = (exam: Exam) => {
    if (exam.cutoffsHistory.length === 0) return 'No published cut-off in register';
    const latest = [...exam.cutoffsHistory].sort((a, b) => b.year - a.year)[0];
    return latest.tier1Cutoff + ' marks (' + latest.category + ', ' + latest.year + ')';
  };

  const nextDateLabel = (exam: Exam) => {
    const active = exam.dates.filter(d => d.status !== 'SUPERSEDED');
    if (active.length === 0) return 'Schedule not yet announced';
    const sorted = [...active].sort((a, b) => a.dateTimeStr.localeCompare(b.dateTimeStr));
    const next = sorted.find(d => d.type === 'APPLICATION_CLOSE') || sorted[0];
    return next.label + ' \u2014 ' + next.dateTimeStr.split(' ')[0];
  };

  const rows: { label: string; render: (exam: Exam) => React.ReactNode }[] = [
    { label: 'Conducting Authority', render: e => <strong>{e.authorityName}</strong> },
    { label: 'Total Vacancies', render: e => e.vacanciesTotal || 'Not yet announced' },
    { label: 'Age Limit (Unreserved)', render: e => ageRangeLabel(e) },
    { label: 'Education Requirement', render: e => qualificationLabel(e) },
    {
      label: 'Pay Scale Grade',
      render: e => <span style={{ color: '#34d399', fontWeight: 700 }}>{payLevelLabel(e)}</span>
    },
    { label: 'Posts in Register', render: e => e.posts.length + ' post' + (e.posts.length === 1 ? '' : 's') },
    { label: 'Selection Stages', render: e => stagesLabel(e) },
    { label: 'Physical / Medical Standards', render: e => physicalLabel(e) },
    { label: 'Latest Published Cut-off', render: e => latestCutoffLabel(e) },
    { label: 'Key Upcoming Date', render: e => nextDateLabel(e) },
    {
      label: 'Career Fields',
      render: e => (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {(e.careerFields || []).map(f => (
            <span key={f} className="glass-pill" style={{ fontSize: '0.72rem' }}>{f}</span>
          ))}
          {(!e.careerFields || e.careerFields.length === 0) && <span>Not categorised</span>}
        </div>
      )
    }
  ];

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
              Every row below is read directly from the verified exam register — no figure is hardcoded.
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
            {rows.map(row => (
              <tr key={row.label} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)', verticalAlign: 'top' }}>{row.label}</td>
                <td style={{ padding: '16px', verticalAlign: 'top' }}>{row.render(exam1)}</td>
                <td style={{ padding: '16px', verticalAlign: 'top' }}>{row.render(exam2)}</td>
              </tr>
            ))}
            <tr>
              <td style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Action</td>
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
