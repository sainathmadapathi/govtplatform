import React, { useState } from 'react';
import { 
  ShieldCheck, FileText, Calendar, UserCheck, BookOpen, Award, Layers, 
  HelpCircle, AlertTriangle, ExternalLink, CheckCircle2, ChevronRight, 
  RefreshCw, Flag, CheckSquare, Square, Download, Flame, ArrowUpRight,
  Camera, Briefcase, Clock, Building, Target, Scale, Zap, Info, Star,
  PlayCircle, Youtube, Eye, Compass
} from 'lucide-react';
import { Exam, DataProvenance, ResourceItem } from '../types/exam';
import { ApplicationGuide } from './ApplicationGuide';
import { PreparationPlanner } from './PreparationPlanner';
import { PracticeEngine } from './PracticeEngine';
import { ResourceReaderModal } from './ResourceReaderModal';
import { ResourceAIAssistant } from './ResourceAIAssistant';
import { PostStudyPathEngine } from './PostStudyPathEngine';

interface ExamDetailViewProps {
  exam: Exam;
  onOpenProvenanceModal: (provenance: DataProvenance) => void;
  onOpenReportModal: (entityType: string, entityId: string) => void;
  onNavigateEligibility?: () => void;
  onNavigatePlanner?: () => void;
  onNavigatePractice?: () => void;
}

export const ExamDetailView: React.FC<ExamDetailViewProps> = ({
  exam,
  onOpenProvenanceModal,
  onOpenReportModal,
  onNavigateEligibility,
  onNavigatePlanner,
  onNavigatePractice
}) => {
  const [activeSection, setActiveSection] = useState<number>(1);
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [resourceSubjectFilter, setResourceSubjectFilter] = useState<string>('ALL');
  const [selectedResourceForModal, setSelectedResourceForModal] = useState<ResourceItem | null>(null);
  const [syllabusViewMode, setSyllabusViewMode] = useState<'POST_STUDY_PATH' | 'OFFICIAL_BLUEPRINT'>('POST_STUDY_PATH');
  const [completedTopics, setCompletedTopics] = useState<Record<string, boolean>>({
    'syl-quant-arithmetic': true,
    'syl-reas-analogy-series': true,
    'syl-eng-grammar': true,
    'syl-ga-polity': true
  });

  const toggleTopic = (id: string) => {
    setCompletedTopics(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const activeCorrigendum = exam.corrigendums.find(c => c.status === 'ACTIVE');

  const sections = [
    { num: 1, name: '01 — Overview & Posts' },
    { num: 2, name: '02 — Dates & Timeline' },
    { num: 3, name: '03 — Eligibility Rules' },
    { num: 4, name: '04 — Application & Docs' },
    { num: 5, name: '05 — Exam Pattern' },
    { num: 6, name: '06 — Post Study Plan & Syllabus' },
    { num: 7, name: '07 — Study Roadmap' },
    { num: 8, name: '08 — Trusted Resources' },
    { num: 9, name: '09 — CBT Practice & PYQs' },
    { num: 10, name: '10 — Cutoff History' },
    { num: 11, name: '11 — FAQs & Clauses' },
    { num: 12, name: '12 — Official Links' },
    { num: 13, name: '13 — Corrigenda Log' }
  ];

  const steps = [
    { num: 1, label: '1. Check Eligibility', sec: 3 },
    { num: 2, label: '2. Understand Pattern', sec: 5 },
    { num: 3, label: '3. Application & Docs', sec: 4 },
    { num: 4, label: '4. Syllabus Blueprint', sec: 6 },
    { num: 5, label: '5. Study Roadmap', sec: 7 },
    { num: 6, label: '6. CBT PYQ Practice', sec: 9 }
  ];

  const filteredResources = resourceSubjectFilter === 'ALL'
    ? exam.resources
    : exam.resources.filter(r => r.subject === resourceSubjectFilter);

  const resourceCategories = ['ALL', 'English Comprehension', 'Quantitative Aptitude', 'Reasoning', 'General Awareness & Static GK', 'Computer & Typing', 'Official Gazette'];

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Exam Header Title Banner */}
      <div className="glass-card" style={{ padding: '28px', background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
              {exam.isGoldenJourney && (
                <span className="badge badge-demo" style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.4)' }}>
                  🌟 GOLDEN BENCHMARK EXAM
                </span>
              )}
              <span className="badge badge-verified">
                <ShieldCheck size={14} /> 100% OFFICIALLY VERIFIED
              </span>
              {exam.vacanciesTotal && (
                <span className="badge badge-demo" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa' }}>
                  {exam.vacanciesTotal}
                </span>
              )}
            </div>

            <h2 style={{ fontSize: '2rem', fontWeight: 800, color: 'white', marginBottom: '6px' }}>
              {exam.title}
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', margin: 0 }}>
              Conducting Body: <strong style={{ color: 'white' }}>{exam.authorityName}</strong> | Official Domain: <a href={exam.officialDomain} target="_blank" rel="noreferrer" style={{ color: '#93c5fd' }}>{exam.officialDomain}</a>
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-secondary" onClick={() => onOpenReportModal('Exam', exam.id)} style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Flag size={16} /> Report Error
            </button>
            <a href={exam.officialDomain} target="_blank" rel="noreferrer" className="btn btn-emerald" style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
              Official Website <ExternalLink size={16} />
            </a>
          </div>
        </div>
      </div>

      {/* Corrigendum Change Notification Bar */}
      {activeCorrigendum && (
        <div className="corrigendum-bar animate-fade-in" style={{ padding: '16px 20px', borderRadius: 'var(--radius-md)', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.4)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <RefreshCw size={22} color="var(--amber)" />
            <div>
              <div style={{ fontSize: '0.9rem', fontWeight: 800, color: '#fbbf24', display: 'flex', alignItems: 'center', gap: '8px' }}>
                ACTIVE CORRIGENDUM NOTICE: {activeCorrigendum.noticeNumber}
              </div>
              <div style={{ fontSize: '0.85rem', color: '#fef3c7' }}>
                {activeCorrigendum.diffSummary}
              </div>
            </div>
          </div>
          <button className="btn btn-outline" onClick={() => setActiveSection(13)} style={{ borderColor: 'var(--amber)', color: 'var(--amber)', fontSize: '0.8rem', padding: '6px 12px' }}>
            View Full Notice <ChevronRight size={14} />
          </button>
        </div>
      )}

      {/* 6-Step Guided Candidate Journey Bar */}
      <div className="glass-card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
          <h4 style={{ fontSize: '0.95rem', fontWeight: 800, color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Target size={18} color="var(--emerald)" /> STEP-BY-STEP CANDIDATE LIFECYCLE
          </h4>
          <span style={{ fontSize: '0.8rem', color: 'var(--primary)', fontWeight: 700 }}>
            Click any step to navigate
          </span>
        </div>

        <div className="stepper-container" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px' }}>
          {steps.map((st) => {
            const isCurrent = activeSection === st.sec;
            return (
              <div 
                key={st.num} 
                className={`step-item ${isCurrent ? 'active' : ''}`}
                onClick={() => {
                  setActiveSection(st.sec);
                  setCurrentStep(st.num);
                }}
                style={{
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  background: isCurrent ? 'rgba(59, 130, 246, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                  border: isCurrent ? '1px solid var(--primary)' : '1px solid var(--border-color)',
                  cursor: 'pointer',
                  textAlign: 'center',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: isCurrent ? '#93c5fd' : 'var(--text-secondary)' }}>
                  {st.label}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 13-Section Horizontal Navigation Tabs */}
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
      <div className="glass-card" style={{ padding: '28px' }}>
        
        {/* Section 01: Overview & Posts */}
        {activeSection === 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'white', margin: 0 }}>
                01 — Official Exam Profile & All {exam.posts.length} Posts Breakdown
              </h3>
              {exam.posts[0] && (
                <button className="btn btn-outline" onClick={() => onOpenProvenanceModal(exam.posts[0].provenance)} style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                  <ShieldCheck size={14} /> Provenance Citation
                </button>
              )}
            </div>

            <p style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
              {exam.overviewDescription}
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
              {exam.posts.map(p => (
                <div key={p.id} style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '8px' }}>
                    <div>
                      <h4 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'white', margin: 0 }}>{p.postName}</h4>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>{p.department}</div>
                      {p.ministry && <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{p.ministry}</div>}
                    </div>
                    <span className="badge badge-verified" style={{ fontSize: '0.75rem' }}>{p.payLevel}</span>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <span className="glass-pill" style={{ color: '#34d399', borderColor: 'rgba(16,185,129,0.3)', fontSize: '0.75rem' }}>{p.payScale}</span>
                    <span className="glass-pill" style={{ fontSize: '0.75rem' }}>Age: {p.minAge}–{p.maxAge} Yrs</span>
                    <span className="glass-pill" style={{ fontSize: '0.75rem' }}>{p.classification}</span>
                  </div>

                  {p.natureOfWork && (
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                      <strong>Job Nature:</strong> {p.natureOfWork}
                    </div>
                  )}

                  {p.physicalRequired && (
                    <div style={{ padding: '8px 10px', borderRadius: 'var(--radius-sm)', background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.25)', fontSize: '0.78rem', color: '#fef3c7' }}>
                      ⚡ <strong>Uniformed Physical Post:</strong> {p.physicalNote || 'Physical test & measurement required.'}
                    </div>
                  )}

                  <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '8px' }}>
                    <button 
                      className="btn btn-outline" 
                      onClick={() => onOpenProvenanceModal(p.provenance)}
                      style={{ fontSize: '0.7rem', padding: '2px 8px' }}
                    >
                      <ShieldCheck size={12} /> Sourced Clause
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 02: Dates & Timeline */}
        {activeSection === 2 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'white', margin: 0 }}>
              02 — Official Examination Dates & Corrigenda Timeline
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {exam.dates.map(d => (
                <div key={d.id} style={{ padding: '16px 20px', borderRadius: 'var(--radius-md)', background: d.status === 'SUPERSEDED' ? 'rgba(239, 68, 68, 0.05)' : 'rgba(255,255,255,0.03)', border: d.status === 'SUPERSEDED' ? '1px dashed rgba(239, 68, 68, 0.3)' : '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '1rem', fontWeight: 700, color: d.status === 'SUPERSEDED' ? '#fca5a5' : 'white', textDecoration: d.status === 'SUPERSEDED' ? 'line-through' : 'none' }}>
                        {d.label}
                      </span>
                      {d.status === 'SUPERSEDED' && (
                        <span className="badge badge-superseded" style={{ fontSize: '0.7rem' }}>SUPERSEDED BY CORRIGENDUM</span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      Timezone: {d.timezone} {d.isTentative && '(Tentative Schedule)'}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <span style={{ fontSize: '1.05rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: d.status === 'SUPERSEDED' ? '#fca5a5' : 'var(--primary)' }}>
                      {d.dateTimeStr}
                    </span>
                    <button className="btn btn-outline" onClick={() => onOpenProvenanceModal(d.provenance)} style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                      <ShieldCheck size={13} /> Sourced Clause
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 03: Eligibility Rules */}
        {activeSection === 3 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'white', margin: 0 }}>
                  03 — Configured Eligibility Rules (Crucial Date: {exam.crucialEligibilityDate})
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: '4px 0 0 0' }}>
                  Deterministic verification rules configured directly from official SSC CGL gazette notification.
                </p>
              </div>

              {onNavigateEligibility && (
                <button onClick={onNavigateEligibility} className="btn btn-emerald" style={{ fontSize: '0.9rem' }}>
                  <UserCheck size={16} /> Open "Am I Eligible?" Calculator
                </button>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
              <div style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
                <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#93c5fd', marginBottom: '8px' }}>1. Crucial Cutoff Date</h4>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', margin: 0 }}>
                  Candidate age is calculated strictly as of <strong>01-08-2026</strong>. Final year degree holders must possess their qualifying degree on or before this date.
                </p>
              </div>

              <div style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#34d399', marginBottom: '8px' }}>2. Category Age Relaxations</h4>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', margin: 0 }}>
                  • <strong>OBC:</strong> +3 Years<br />
                  • <strong>SC / ST:</strong> +5 Years<br />
                  • <strong>PwBD (Unreserved):</strong> +10 Years<br />
                  • <strong>PwBD (OBC):</strong> +13 Years<br />
                  • <strong>PwBD (SC/ST):</strong> +15 Years
                </p>
              </div>

              <div style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#fbbf24', marginBottom: '8px' }}>3. Specialized Degree Posts</h4>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', margin: 0 }}>
                  • <strong>JSO:</strong> 60% in 12th Maths OR Degree with Statistics.<br />
                  • <strong>Stat Investigator Gr II:</strong> Statistics in all 3 years of Degree.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Section 04: Application & Docs (Embeds ApplicationGuide) */}
        {activeSection === 4 && (
          <ApplicationGuide 
            guide={exam.applicationGuide}
            onOpenProvenanceModal={onOpenProvenanceModal}
          />
        )}

        {/* Section 05: Exam Pattern */}
        {activeSection === 5 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'white', margin: 0 }}>
              05 — Complete 2-Tier Exam Pattern & Scheme
            </h3>

            {exam.stages.map(stage => (
              <div key={stage.id} style={{ padding: '22px', borderRadius: 'var(--radius-md)', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                  <div>
                    <span className="badge badge-verified" style={{ marginBottom: '4px' }}>{stage.tier}</span>
                    <h4 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'white', margin: 0 }}>{stage.stageName}</h4>
                  </div>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <span className="glass-pill" style={{ color: '#38bdf8' }}>{stage.durationMinutes} Mins</span>
                    <span className="glass-pill" style={{ color: 'var(--emerald)' }}>{stage.totalMarks} Marks</span>
                    <span className="glass-pill">{stage.negativeMarking}</span>
                  </div>
                </div>

                <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', margin: 0 }}>
                  <strong>Nature of Stage:</strong> {stage.qualifyingNature}
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {stage.sections.map((sec, sIdx) => (
                    <div key={sIdx} style={{ padding: '14px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                      <div>
                        <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'white' }}>{sec.sectionName}</div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                          {sec.modules.join(' • ')}
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: '12px', fontSize: '0.85rem' }}>
                        <span style={{ color: '#93c5fd' }}>{sec.questions} Questions</span>
                        <span style={{ color: 'var(--emerald)', fontWeight: 700 }}>{sec.marks} Marks</span>
                        <span style={{ color: 'var(--text-muted)' }}>{sec.durationMinutes} Mins</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Section 06: Post Study Plan & Official Syllabus */}
        {activeSection === 6 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'white', margin: 0 }}>
                  06 — Targeted Post Study Plan & Official Syllabus
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', margin: '4px 0 0 0' }}>
                  Distinguishing common stage requirements from post-specific modules and non-required subjects.
                </p>
              </div>

              {/* View Switcher: Post-Specific Plan vs Official Legal Blueprint */}
              <div style={{ display: 'flex', gap: '6px', background: 'rgba(255, 255, 255, 0.05)', padding: '4px', borderRadius: 'var(--radius-md)' }}>
                <button
                  onClick={() => setSyllabusViewMode('POST_STUDY_PATH')}
                  className={`btn ${syllabusViewMode === 'POST_STUDY_PATH' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ fontSize: '0.82rem', padding: '6px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <Compass size={14} /> Post Study Plan
                </button>
                <button
                  onClick={() => setSyllabusViewMode('OFFICIAL_BLUEPRINT')}
                  className={`btn ${syllabusViewMode === 'OFFICIAL_BLUEPRINT' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ fontSize: '0.82rem', padding: '6px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <FileText size={14} /> Official Gazette Syllabus
                </button>
              </div>
            </div>

            {/* View 1: Dynamic Post Study Path Engine */}
            {syllabusViewMode === 'POST_STUDY_PATH' && (
              <PostStudyPathEngine 
                onOpenProvenanceModal={onOpenProvenanceModal}
                onNavigatePractice={onNavigatePractice}
              />
            )}

            {/* View 2: Official Micro-Topic Syllabus Blueprint */}
            {syllabusViewMode === 'OFFICIAL_BLUEPRINT' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                <div style={{ padding: '14px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.25)', fontSize: '0.86rem', color: '#93c5fd' }}>
                  ℹ️ <strong>Official Legal Blueprint:</strong> This is the unadjusted statutory syllabus extracted directly from the SSC Gazette Notification Section 13.
                </div>

                {exam.syllabus.map(topic => {
                  const isDone = !!completedTopics[topic.id];
                  return (
                    <div key={topic.id} style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: isDone ? 'rgba(16, 185, 129, 0.04)' : 'rgba(255, 255, 255, 0.02)', border: isDone ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <div onClick={() => toggleTopic(topic.id)} style={{ cursor: 'pointer' }}>
                            {isDone ? <CheckSquare size={22} color="var(--emerald)" /> : <Square size={22} color="var(--text-muted)" />}
                          </div>
                          <div>
                            <div style={{ fontSize: '0.78rem', color: '#93c5fd', fontWeight: 700, textTransform: 'uppercase' }}>
                              {topic.subject} • {topic.tier}
                            </div>
                            <h4 style={{ fontSize: '1.05rem', fontWeight: 800, color: isDone ? '#86efac' : 'white', margin: 0 }}>
                              {topic.topicName}
                            </h4>
                          </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          {topic.isHighYield && (
                            <span className="badge badge-demo" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#f87171' }}>
                              🔥 HIGH-YIELD TOPIC
                            </span>
                          )}
                          <span className="badge badge-verified">
                            Weightage: ~{topic.weightagePercentage}% (~{topic.avgQuestions} Qs/Shift)
                          </span>
                        </div>
                      </div>

                      {topic.subtopics && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', paddingLeft: '34px' }}>
                          {topic.subtopics.map((sub, sIdx) => (
                            <span key={sIdx} className="glass-pill" style={{ fontSize: '0.78rem' }}>
                              {sub}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Section 07: Study Roadmap (Embeds PreparationPlanner) */}
        {activeSection === 7 && (
          <PreparationPlanner exam={exam} />
        )}

        {/* Section 08: Trusted Resources (Topper Consensus & Official Sources) */}
        {activeSection === 8 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'white', margin: 0 }}>
                  08 — Most Trusted Resources (Topper Consensus & Official Standards)
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', margin: '4px 0 0 0' }}>
                  Handpicked reference books, previous year question compendiums, typing simulators, and official gazettes vetted by thousands of successful candidates.
                </p>
              </div>
            </div>

            {/* Resource Category Filter Bar */}
            <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
              {resourceCategories.map(cat => (
                <button
                  key={cat}
                  onClick={() => setResourceSubjectFilter(cat)}
                  className={`btn ${resourceSubjectFilter === cat ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ fontSize: '0.82rem', padding: '6px 14px', whiteSpace: 'nowrap' }}
                >
                  {cat}
                </button>
              ))}
            </div>

            {/* AI Resource Navigator & Assistant */}
            <ResourceAIAssistant 
              resources={exam.resources || []} 
              onOpenResourceModal={(res) => setSelectedResourceForModal(res)}
            />

            {/* Resources Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
              {filteredResources.map(res => (
                <div key={res.id} style={{ padding: '22px', borderRadius: 'var(--radius-md)', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '14px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px' }}>
                      <span className="badge badge-verified" style={{ fontSize: '0.72rem' }}>
                        {res.officialTag || res.subject}
                      </span>
                      {res.rating && (
                        <span style={{ fontSize: '0.78rem', color: '#fbbf24', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Star size={13} fill="#fbbf24" color="#fbbf24" /> {res.rating}
                        </span>
                      )}
                    </div>

                    <h4 style={{ fontSize: '1.08rem', fontWeight: 800, color: 'white', margin: 0 }}>
                      {res.title}
                    </h4>
                    
                    <div style={{ fontSize: '0.82rem', color: '#93c5fd', fontWeight: 600 }}>
                      Author / Sourced Body: {res.author}
                    </div>

                    <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
                      {res.description}
                    </p>

                    <div style={{ padding: '8px 10px', borderRadius: 'var(--radius-sm)', background: 'rgba(16, 185, 129, 0.06)', border: '1px solid rgba(16, 185, 129, 0.2)', fontSize: '0.8rem', color: '#86efac' }}>
                      <strong>Recommended Use:</strong> {res.recommendedFor}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '12px' }}>
                    {res.resourceFormat === 'YOUTUBE_COURSE' ? (
                      <>
                        <a 
                          href={res.youtubeUrl || res.url} 
                          target="_blank" 
                          rel="noreferrer" 
                          className="btn btn-emerald" 
                          style={{ fontSize: '0.82rem', padding: '7px 16px', display: 'flex', alignItems: 'center', gap: '6px' }}
                        >
                          <PlayCircle size={16} /> Watch Direct Video on YouTube <ExternalLink size={13} />
                        </a>
                        <button 
                          onClick={() => setSelectedResourceForModal(res)}
                          className="btn btn-secondary" 
                          style={{ fontSize: '0.8rem', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                          title="Watch Video inside App"
                        >
                          <Eye size={14} /> Play in App
                        </button>
                      </>
                    ) : res.resourceFormat === 'ONLINE_TOOL' ? (
                      <>
                        <a 
                          href={res.url} 
                          target="_blank" 
                          rel="noreferrer" 
                          className="btn btn-emerald" 
                          style={{ fontSize: '0.82rem', padding: '6px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
                        >
                          Launch Typing Simulator <ExternalLink size={14} />
                        </a>
                      </>
                    ) : res.directPdfUrl ? (
                      <>
                        <button 
                          onClick={() => setSelectedResourceForModal(res)}
                          className="btn btn-emerald" 
                          style={{ fontSize: '0.82rem', padding: '7px 16px', display: 'flex', alignItems: 'center', gap: '6px' }}
                        >
                          <BookOpen size={16} /> Read Handbook & Notes
                        </button>
                        <a 
                          href={res.directPdfUrl}
                          download={res.downloadFileName || 'GovOS_Official_Resource.pdf'}
                          className="btn btn-outline" 
                          style={{ fontSize: '0.8rem', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                        >
                          <Download size={14} /> Download PDF
                        </a>
                      </>
                    ) : (
                      <>
                        <button 
                          onClick={() => setSelectedResourceForModal(res)}
                          className="btn btn-emerald" 
                          style={{ fontSize: '0.82rem', padding: '6px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
                        >
                          <BookOpen size={15} /> Read Full Handbook & Notes
                        </button>
                        <button 
                          onClick={() => setSelectedResourceForModal(res)}
                          className="btn btn-outline" 
                          style={{ fontSize: '0.8rem', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                        >
                          <Download size={14} /> Save / Print PDF
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 09: CBT Practice & PYQs (Embeds PracticeEngine) */}
        {activeSection === 9 && (
          <PracticeEngine 
            exam={exam}
            onOpenProvenanceModal={onOpenProvenanceModal}
          />
        )}

        {/* Section 10: Cutoff History */}
        {activeSection === 10 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'white', margin: 0 }}>
              10 — Official Category Cutoff History (2021 to 2024)
            </h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                    <th style={{ padding: '12px' }}>Year</th>
                    <th style={{ padding: '12px' }}>Category</th>
                    <th style={{ padding: '12px' }}>Tier-1 Cutoff (Out of 200)</th>
                    <th style={{ padding: '12px' }}>Tier-2 Final Cutoff (Out of 390)</th>
                    <th style={{ padding: '12px' }}>Source Provenance</th>
                  </tr>
                </thead>
                <tbody>
                  {exam.cutoffsHistory.map((c, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                      <td style={{ padding: '12px', fontWeight: 700, color: 'white' }}>{c.year}</td>
                      <td style={{ padding: '12px', color: '#93c5fd' }}>{c.category}</td>
                      <td style={{ padding: '12px', fontWeight: 700, color: 'var(--emerald)', fontFamily: 'var(--font-mono)' }}>{c.tier1Cutoff}</td>
                      <td style={{ padding: '12px', fontWeight: 700, color: 'var(--primary)', fontFamily: 'var(--font-mono)' }}>{c.tier2Cutoff || 'N/A'}</td>
                      <td style={{ padding: '12px' }}>
                        <button onClick={() => onOpenProvenanceModal(c.provenance)} className="btn btn-outline" style={{ fontSize: '0.7rem', padding: '2px 8px' }}>
                          <ShieldCheck size={11} /> Official PDF
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Section 11: FAQs & Clauses */}
        {activeSection === 11 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'white', margin: 0 }}>
              11 — Frequently Asked Questions with Official Gazette Citations
            </h3>
            {exam.faqs.map(faq => (
              <div key={faq.id} style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                  <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white', margin: 0 }}>{faq.question}</h4>
                  <span className="badge badge-verified" style={{ fontSize: '0.72rem' }}>{faq.officialClause}</span>
                </div>
                <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
                  {faq.answer}
                </p>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                  <button onClick={() => onOpenProvenanceModal(faq.provenance)} className="btn btn-outline" style={{ fontSize: '0.7rem', padding: '2px 8px' }}>
                    <ShieldCheck size={11} /> View Source Document
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Section 12: Official Links */}
        {activeSection === 12 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'white', margin: 0 }}>
              12 — Authoritative Government Portals & Directory
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
              <a href="https://ssc.gov.in" target="_blank" rel="noreferrer" className="glass-card" style={{ padding: '18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'white' }}>Staff Selection Commission</h4>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>ssc.gov.in (Official Application & Result Portal)</div>
                </div>
                <ExternalLink size={18} color="var(--primary)" />
              </a>

              <a href="https://ncbc.nic.in" target="_blank" rel="noreferrer" className="glass-card" style={{ padding: '18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'white' }}>NCBC Central OBC List</h4>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>ncbc.nic.in (Central OBC Caste Verification)</div>
                </div>
                <ExternalLink size={18} color="var(--primary)" />
              </a>

              <a href="https://www.digilocker.gov.in" target="_blank" rel="noreferrer" className="glass-card" style={{ padding: '18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'white' }}>DigiLocker Government Portal</h4>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>digilocker.gov.in (Verified Marksheets & ID)</div>
                </div>
                <ExternalLink size={18} color="var(--primary)" />
              </a>
            </div>
          </div>
        )}

        {/* Section 13: Corrigenda Log */}
        {activeSection === 13 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'white', margin: 0 }}>
              13 — Official Corrigenda & Modification Notices Log
            </h3>
            {exam.corrigendums.map(corr => (
              <div key={corr.id} style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(245, 158, 11, 0.06)', border: '1px solid rgba(245, 158, 11, 0.3)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                  <span className="badge badge-changed">{corr.status}</span>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Published: {corr.publishedDate}</span>
                </div>
                <h4 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fbbf24', margin: 0 }}>{corr.title}</h4>
                <div style={{ fontSize: '0.82rem', color: '#fef3c7', fontWeight: 600 }}>Notice Ref: {corr.noticeNumber}</div>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', margin: 0 }}>{corr.summary}</p>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                  <a href={corr.pdfUrl} target="_blank" rel="noreferrer" className="btn btn-outline" style={{ fontSize: '0.8rem', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Download size={14} /> Open Official Notices Portal
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Resource Reader & YouTube Video Player Modal */}
      {selectedResourceForModal && (
        <ResourceReaderModal 
          resource={selectedResourceForModal}
          onClose={() => setSelectedResourceForModal(null)}
        />
      )}

    </div>
  );
};
