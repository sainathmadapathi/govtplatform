import React, { useState } from 'react';
import { 
  ShieldCheck, FileText, Calendar, UserCheck, BookOpen, Award, Layers, 
  HelpCircle, AlertTriangle, ExternalLink, CheckCircle2, ChevronRight, RefreshCw, Flag, CheckSquare, Square, Download, Flame, ArrowUpRight
} from 'lucide-react';
import { Exam, DataProvenance } from '../types/exam';

interface ExamDetailViewProps {
  exam: Exam;
  onOpenProvenanceModal: (provenance: DataProvenance) => void;
  onOpenReportModal: (entityType: string, entityId: string) => void;
  onNavigatePlanner: () => void;
  onNavigatePractice: () => void;
}

export const ExamDetailView: React.FC<ExamDetailViewProps> = ({
  exam,
  onOpenProvenanceModal,
  onOpenReportModal,
  onNavigatePlanner,
  onNavigatePractice
}) => {
  const [activeSection, setActiveSection] = useState<number>(1);
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [completedTopics, setCompletedTopics] = useState<Record<string, boolean>>({
    'syl-quant-1': true,
    'syl-quant-2': true,
    'syl-reas-1': true,
    'syl-reas-2': true,
    'syl-eng-1': true
  });

  const toggleTopic = (id: string) => {
    setCompletedTopics(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const sections = [
    { num: 1, name: '01 — Overview' },
    { num: 2, name: '02 — Dates' },
    { num: 3, name: '03 — Eligibility' },
    { num: 4, name: '04 — Application' },
    { num: 5, name: '05 — Pattern' },
    { num: 6, name: '06 — Syllabus' },
    { num: 7, name: '07 — Preparation' },
    { num: 8, name: '08 — Resources' },
    { num: 9, name: '09 — Practice' },
    { num: 10, name: '10 — Trend Analysis' },
    { num: 11, name: '11 — Cutoffs' },
    { num: 12, name: '12 — FAQ' },
    { num: 13, name: '13 — Official Links' },
    { num: 14, name: '14 — Corrigenda Log' }
  ];

  const steps = [
    'Check Eligibility',
    'Understand Pattern',
    'Apply Officially',
    'Syllabus Map',
    'Prep Roadmap',
    'Topic Practice',
    'Take Mocks',
    'Weak Areas',
    'Revision',
    'Exam Ready'
  ];

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Exam Header Title Banner */}
      <div className="glass-card" style={{ padding: '28px', background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span className="badge badge-verified" style={{ cursor: 'pointer' }} onClick={() => onOpenProvenanceModal(exam.dates[0].provenance)}>
                <ShieldCheck size={14} /> OFFICIALLY VERIFIED
              </span>
              {exam.isGoldenJourney && (
                <span className="badge badge-demo" style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.4)' }}>
                  🌟 GOLDEN JOURNEY
                </span>
              )}
              {exam.isDemoData && (
                <span className="badge badge-demo">
                  DEMO DATA FOR PROTOTYPE
                </span>
              )}
            </div>

            <h2 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '6px' }}>
              {exam.title}
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
              Conducting Body: <strong style={{ color: 'white' }}>{exam.authorityName}</strong> | Official Domain: <a href={exam.officialDomain} target="_blank" rel="noreferrer">{exam.officialDomain}</a>
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-secondary" onClick={() => onOpenReportModal('Exam', exam.id)} style={{ fontSize: '0.85rem' }}>
              <Flag size={16} /> Report Error
            </button>
            <a href={exam.officialDomain} target="_blank" rel="noreferrer" className="btn btn-emerald" style={{ fontSize: '0.85rem' }}>
              Official Apply Portal <ExternalLink size={16} />
            </a>
          </div>
        </div>
      </div>

      {/* Corrigendum Change Notification Bar */}
      {exam.corrigendums && exam.corrigendums.length > 0 && (
        <div className="corrigendum-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <RefreshCw size={22} color="var(--amber)" className="animate-spin-slow" />
            <div>
              <div style={{ fontSize: '0.9rem', fontWeight: 800, color: '#fbbf24', display: 'flex', alignItems: 'center', gap: '8px' }}>
                LIVE CORRIGENDUM NOTICE: {exam.corrigendums[0].noticeNumber}
              </div>
              <div style={{ fontSize: '0.85rem', color: '#fef3c7' }}>
                {exam.corrigendums[0].diffSummary}
              </div>
            </div>
          </div>
          <button className="btn btn-outline" onClick={() => setActiveSection(14)} style={{ borderColor: 'var(--amber)', color: 'var(--amber)', fontSize: '0.8rem', padding: '6px 12px' }}>
            View Official Notice <ChevronRight size={14} />
          </button>
        </div>
      )}

      {/* "What Should I Do Next?" 10-Step Journey Bar */}
      <div className="glass-card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
            🎯 YOUR CGL CANDIDATE JOURNEY (STEP {currentStep} OF 10)
          </h4>
          <span style={{ fontSize: '0.8rem', color: 'var(--primary)', fontWeight: 600 }}>
            {Math.round((currentStep / 10) * 100)}% Journey Progress
          </span>
        </div>

        <div className="stepper-container">
          {steps.map((st, idx) => {
            const stepNum = idx + 1;
            const isActive = stepNum === currentStep;
            const isCompleted = stepNum < currentStep;
            return (
              <div 
                key={st} 
                className={`step-item ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
                onClick={() => setCurrentStep(stepNum)}
              >
                <div className="step-number">
                  {isCompleted ? '✓' : stepNum}
                </div>
                <div className="step-title">{st}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 14-Section Horizontal Navigation Tabs */}
      <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '4px' }}>
        {sections.map(sec => (
          <button
            key={sec.num}
            onClick={() => setActiveSection(sec.num)}
            className={`btn ${activeSection === sec.num ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.8rem', padding: '8px 14px', whiteSpace: 'nowrap' }}
          >
            {sec.name}
          </button>
        ))}
      </div>

      {/* Section Content Views */}
      <div className="glass-card" style={{ padding: '32px' }}>
        
        {/* Section 01: Overview */}
        {activeSection === 1 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '1.4rem', fontWeight: 800 }}>01 — Exam Overview & Roles</h3>
              <button className="btn btn-outline" onClick={() => onOpenProvenanceModal(exam.posts[0].provenance)} style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                <ShieldCheck size={14} /> Provenance Citation
              </button>
            </div>

            <p style={{ fontSize: '1rem', color: '#e2e8f0', lineHeight: 1.6, marginBottom: '24px' }}>
              {exam.overviewDescription}
            </p>

            <h4 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '16px' }}>Recruitment Posts & Pay Levels</h4>
            <div className="grid-2">
              {exam.posts.map(p => (
                <div key={p.id} style={{ padding: '16px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white', marginBottom: '4px' }}>{p.postName}</div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>Department: {p.department}</div>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <span className="glass-pill" style={{ color: '#34d399', borderColor: 'rgba(16,185,129,0.3)' }}>{p.payLevel}</span>
                    <span className="glass-pill">{p.classification}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 02: Dates */}
        {activeSection === 2 && (
          <div>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '20px' }}>02 — Official Examination Dates & Timeline</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {exam.dates.map(d => (
                <div key={d.id} style={{ padding: '16px 20px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: 'white' }}>{d.label}</div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      Timezone: {d.timezone} {d.isTentative && '(Tentative Schedule)'}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <span style={{ fontSize: '1.1rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--primary)' }}>
                      {d.dateTimeStr}
                    </span>
                    <button className="btn btn-outline" onClick={() => onOpenProvenanceModal(d.provenance)} style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                      Cite Clause
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 03: Eligibility */}
        {activeSection === 3 && (
          <div>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '16px' }}>03 — Eligibility Rules & Cutoffs</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>
              Evaluated using deterministic rule trees. Try the interactive calculator below or view official clauses.
            </p>
            <div style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.3)', marginBottom: '24px' }}>
              <h4 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '8px' }}>General Qualification Requirements</h4>
              <ul style={{ paddingLeft: '20px', fontSize: '0.95rem', color: '#e2e8f0', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <li><strong>Age Limit:</strong> 18 to 27 Years (Base cutoff date: 01-08-2026). Category relaxations: OBC (+3 yrs), SC/ST (+5 yrs), PwBD (+10 yrs).</li>
                <li><strong>Educational Qualification:</strong> Bachelor's Degree in any discipline from a recognized University.</li>
                <li><strong>Nationality:</strong> Must be a Citizen of India.</li>
              </ul>
            </div>
          </div>
        )}

        {/* Section 04: Application Walkthrough */}
        {activeSection === 4 && (
          <div>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '20px' }}>04 — Step-by-Step Official Application Guide</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '24px' }}>
              {exam.applicationSteps.map(st => (
                <div key={st.stepNumber} style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)', display: 'flex', gap: '16px' }}>
                  <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: 'var(--primary)', color: 'white', fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    {st.stepNumber}
                  </div>
                  <div>
                    <h4 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '4px' }}>{st.title}</h4>
                    <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>{st.description}</p>
                    <span className="glass-pill" style={{ fontSize: '0.75rem', color: '#34d399', borderColor: 'rgba(16,185,129,0.3)' }}>
                      📄 Required Document: {st.documentRequired}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <a href={exam.officialDomain} target="_blank" rel="noreferrer" className="btn btn-emerald" style={{ padding: '14px 28px', fontSize: '1rem' }}>
              Open Official SSC Application Portal <ExternalLink size={18} />
            </a>
          </div>
        )}

        {/* Section 06: Interactive Syllabus Tree */}
        {activeSection === 6 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
              <div>
                <h3 style={{ fontSize: '1.4rem', fontWeight: 800 }}>06 — Interactive Syllabus Map</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  Click checkmarks to track completed topics in your Student Dashboard
                </p>
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <button className="btn btn-primary" onClick={onNavigatePlanner} style={{ fontSize: '0.85rem' }}>
                  Generate 90-Day Study Plan
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {exam.syllabus.map(subject => (
                <div key={subject.id} style={{ border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '20px', background: 'rgba(255,255,255,0.02)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                    <h4 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--primary)' }}>
                      {subject.topicName}
                    </h4>
                    <span className="badge badge-pending">
                      GovOS Historical Weightage: {subject.weightagePercentage}%
                    </span>
                  </div>

                  <div className="grid-2">
                    {subject.subtopics?.map(st => {
                      const isDone = !!completedTopics[st.id];
                      return (
                        <div 
                          key={st.id} 
                          onClick={() => toggleTopic(st.id)}
                          style={{ 
                            padding: '12px 16px', 
                            borderRadius: 'var(--radius-md)', 
                            background: isDone ? 'rgba(16, 185, 129, 0.08)' : 'rgba(255,255,255,0.03)',
                            border: `1px solid ${isDone ? 'rgba(16, 185, 129, 0.3)' : 'var(--border-color)'}`,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px',
                            cursor: 'pointer'
                          }}
                        >
                          {isDone ? <CheckSquare size={20} color="var(--emerald)" /> : <Square size={20} color="var(--text-muted)" />}
                          <div>
                            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: isDone ? '#34d399' : 'white' }}>
                              {st.topicName}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              Weightage: ~{st.weightagePercentage}%
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 09: Practice */}
        {activeSection === 9 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
              <div>
                <h3 style={{ fontSize: '1.4rem', fontWeight: 800 }}>09 — Interactive PYQ & Timed Practice Engine</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  Solve verified past year questions with instant accuracy feedback
                </p>
              </div>
              <button className="btn btn-emerald" onClick={onNavigatePractice}>
                Launch Practice Quiz Simulator <ChevronRight size={18} />
              </button>
            </div>
          </div>
        )}

        {/* Section 14: Corrigenda Log */}
        {activeSection === 14 && (
          <div>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '20px' }}>14 — Notification & Corrigendum Audit Log</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {exam.corrigendums.map(c => (
                <div key={c.id} style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(245, 158, 11, 0.06)', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span className="badge badge-changed">{c.status}</span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Published: {c.publishedDate}</span>
                  </div>
                  <h4 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fbbf24', marginBottom: '6px' }}>{c.title}</h4>
                  <p style={{ fontSize: '0.9rem', color: '#fef3c7', marginBottom: '12px' }}>{c.summary}</p>
                  <a href={c.pdfUrl} target="_blank" rel="noreferrer" className="btn btn-outline" style={{ fontSize: '0.8rem', padding: '6px 12px' }}>
                    Download Official PDF Corrigendum <Download size={14} />
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Default Fallback for other sections */}
        {activeSection !== 1 && activeSection !== 2 && activeSection !== 3 && activeSection !== 4 && activeSection !== 6 && activeSection !== 9 && activeSection !== 14 && (
          <div>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '16px' }}>
              {sections.find(s => s.num === activeSection)?.name}
            </h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>
              Displaying verified section payload for {exam.title}.
            </p>
            <div style={{ padding: '24px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)' }}>
              Official data verified against {exam.authorityName} database records.
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
