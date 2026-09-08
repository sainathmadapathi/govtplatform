import React, { useState } from 'react';
import { 
  Award, CheckCircle2, AlertTriangle, ArrowRight, ShieldCheck, 
  FileText, Compass, BookOpen, Clock, Target, Sparkles, Scale,
  Keyboard, Check, RefreshCw, HelpCircle
} from 'lucide-react';
import { Exam } from '../types/exam';

interface ResultNextStepsSectionProps {
  exam: Exam;
  onNavigateSection: (sectionNum: number) => void;
  onNavigatePractice?: () => void;
  onSelectAlternativeExam?: (examCode: string) => void;
}

type CandidateResultStatus = 'QUALIFIED_TIER2' | 'SKILL_TEST' | 'DOC_VERIFICATION' | 'NOT_QUALIFIED';

export const ResultNextStepsSection: React.FC<ResultNextStepsSectionProps> = ({
  exam,
  onNavigateSection,
  onNavigatePractice,
  onSelectAlternativeExam
}) => {
  const [selectedStatus, setSelectedStatus] = useState<CandidateResultStatus>('QUALIFIED_TIER2');

  const resultDate = exam.dates.find(d => d.type === 'RESULT');
  const ansKeyDate = exam.dates.find(d => d.type === 'ANSWER_KEY');
  const latestCutoff = exam.cutoffsHistory[0];

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Top Banner */}
      <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(234, 179, 8, 0.12) 0%, rgba(17, 24, 39, 0.95) 100%)', borderColor: 'rgba(234, 179, 8, 0.35)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
              <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.2)', color: '#facc15', border: '1px solid rgba(234, 179, 8, 0.4)' }}>
                🏆 RESULT & SCORECARD NAVIGATION
              </span>
              <span className="badge badge-verified">
                OFFICIALLY AUDITED
              </span>
            </div>

            <h3 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'white', margin: '0 0 6px' }}>
              Post-Result Personalized Next Step Flow
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
              Official Tier-1 shortlist announcement: <strong style={{ color: '#facc15' }}>{resultDate?.dateTimeStr || '15 Dec 2026'}</strong>. Select your result status below to view your exact official action plan.
            </p>
          </div>

          {latestCutoff && (
            <div style={{ padding: '10px 16px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-color)', textAlign: 'right' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Latest General (UR) Cutoff</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--primary)' }}>{latestCutoff.tier1Cutoff} Marks</div>
            </div>
          )}
        </div>
      </div>

      {/* Interactive Candidate Status Switcher */}
      <div className="glass-card" style={{ padding: '20px' }}>
        <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Select Your Candidate Examination Status:
        </label>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px' }}>
          <button 
            className={`btn ${selectedStatus === 'QUALIFIED_TIER2' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSelectedStatus('QUALIFIED_TIER2')}
            style={{ fontSize: '0.85rem', padding: '12px 14px', display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'flex-start', textAlign: 'left' }}
          >
            <Award size={18} color={selectedStatus === 'QUALIFIED_TIER2' ? 'white' : '#34d399'} />
            <div>
              <div style={{ fontWeight: 700 }}>Qualified for Tier-2</div>
              <div style={{ fontSize: '0.72rem', opacity: 0.8 }}>Shortlisted for Main Examination</div>
            </div>
          </button>

          <button 
            className={`btn ${selectedStatus === 'SKILL_TEST' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSelectedStatus('SKILL_TEST')}
            style={{ fontSize: '0.85rem', padding: '12px 14px', display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'flex-start', textAlign: 'left' }}
          >
            <Keyboard size={18} color={selectedStatus === 'SKILL_TEST' ? 'white' : '#60a5fa'} />
            <div>
              <div style={{ fontWeight: 700 }}>Skill Test / DEST</div>
              <div style={{ fontSize: '0.72rem', opacity: 0.8 }}>Typing speed & accuracy threshold</div>
            </div>
          </button>

          <button 
            className={`btn ${selectedStatus === 'DOC_VERIFICATION' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSelectedStatus('DOC_VERIFICATION')}
            style={{ fontSize: '0.85rem', padding: '12px 14px', display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'flex-start', textAlign: 'left' }}
          >
            <FileText size={18} color={selectedStatus === 'DOC_VERIFICATION' ? 'white' : '#a855f7'} />
            <div>
              <div style={{ fontWeight: 700 }}>Document Verification</div>
              <div style={{ fontSize: '0.72rem', opacity: 0.8 }}>Certificates & crucial date scrutiny</div>
            </div>
          </button>

          <button 
            className={`btn ${selectedStatus === 'NOT_QUALIFIED' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSelectedStatus('NOT_QUALIFIED')}
            style={{ fontSize: '0.85rem', padding: '12px 14px', display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'flex-start', textAlign: 'left' }}
          >
            <RefreshCw size={18} color={selectedStatus === 'NOT_QUALIFIED' ? 'white' : '#f87171'} />
            <div>
              <div style={{ fontWeight: 700 }}>Missed the Cutoff</div>
              <div style={{ fontSize: '0.72rem', opacity: 0.8 }}>Diagnosis & immediate alternative exams</div>
            </div>
          </button>
        </div>
      </div>

      {/* STATUS 1: QUALIFIED FOR TIER-2 */}
      {selectedStatus === 'QUALIFIED_TIER2' && (
        <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="glass-card" style={{ padding: '24px', borderLeft: '4px solid #10b981' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(16,185,129,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#34d399' }}>
                <CheckCircle2 size={20} />
              </div>
              <h4 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'white', margin: 0 }}>
                Congratulations! You are Shortlisted for Tier-2 Computer Based Exam
              </h4>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0, lineHeight: 1.5 }}>
              Your Tier-1 score exceeded the normalized qualifying mark. Tier-2 marks determine your <strong>final all-India merit rank and Ministry allocation</strong>. Follow this immediate 4-step action schedule:
            </p>
          </div>

          <div className="grid-2" style={{ gap: '16px' }}>
            <div className="glass-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '14px' }}>
              <div>
                <span className="badge badge-demo" style={{ fontSize: '0.7rem', marginBottom: '8px' }}>PRIORITY STEP 1</span>
                <h5 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white', margin: '0 0 6px' }}>
                  Pivot to Tier-2 Weightage Blueprint
                </h5>
                <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
                  Tier-2 Paper-I is compulsory for all posts. Section-I (Maths + Reasoning: 60 Qs = 180 Marks) and Section-II (English + GA: 70 Qs = 210 Marks). Negative marking increases to <strong>1.00 mark per wrong answer</strong>.
                </p>
              </div>
              <button 
                className="btn btn-primary"
                onClick={() => onNavigateSection(6)}
                style={{ fontSize: '0.8rem', padding: '8px 14px', alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                Open Post Study Plan (Section 6) <ArrowRight size={14} />
              </button>
            </div>

            <div className="glass-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '14px' }}>
              <div>
                <span className="badge badge-demo" style={{ fontSize: '0.7rem', marginBottom: '8px' }}>PRIORITY STEP 2</span>
                <h5 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white', margin: '0 0 6px' }}>
                  Secure Computer Knowledge Module (CKT)
                </h5>
                <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
                  Section-III Module-I (20 Questions, 60 Marks) is qualifying in nature, but failure disqualifies you from <em>every single post</em>. A higher cutoff is mandated for ASO in CSS and Inspector (CBIC). Target 30+ marks.
                </p>
              </div>
              <button 
                className="btn btn-secondary"
                onClick={() => onNavigateSection(8)}
                style={{ fontSize: '0.8rem', padding: '8px 14px', alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                View Computer Masterclass (Section 8) <ArrowRight size={14} />
              </button>
            </div>

            <div className="glass-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '14px' }}>
              <div>
                <span className="badge badge-demo" style={{ fontSize: '0.7rem', marginBottom: '8px' }}>PRIORITY STEP 3</span>
                <h5 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white', margin: '0 0 6px' }}>
                  DEST Speed Typing Drill (Daily 30 Mins)
                </h5>
                <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
                  Data Entry Speed Test (~27 WPM, 2000 key depressions) is held on the exact same day as Tier-2 Paper-I. Build muscle memory on physical membrane keyboards.
                </p>
              </div>
              <button 
                className="btn btn-secondary"
                onClick={() => setSelectedStatus('SKILL_TEST')}
                style={{ fontSize: '0.8rem', padding: '8px 14px', alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                Explore Skill Test Protocols <ArrowRight size={14} />
              </button>
            </div>

            <div className="glass-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '14px' }}>
              <div>
                <span className="badge badge-demo" style={{ fontSize: '0.7rem', marginBottom: '8px' }}>PRIORITY STEP 4</span>
                <h5 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white', margin: '0 0 6px' }}>
                  Full-Length 2.5-Hour CBT Endurance Tests
                </h5>
                <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
                  Sit for continuous 2 hour 15 minute mocks without intermission. Time management across English comprehension passages and multi-statement reasoning is decisive.
                </p>
              </div>
              {onNavigatePractice && (
                <button 
                  className="btn btn-emerald"
                  onClick={onNavigatePractice}
                  style={{ fontSize: '0.8rem', padding: '8px 14px', alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  Launch Practice Engine <ArrowRight size={14} />
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* STATUS 2: SKILL TEST / DEST TYPING */}
      {selectedStatus === 'SKILL_TEST' && (
        <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="glass-card" style={{ padding: '24px', borderLeft: '4px solid #3b82f6' }}>
            <h4 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'white', margin: '0 0 8px' }}>
              Data Entry Speed Test (DEST) & Skill Qualifying Protocols
            </h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0, lineHeight: 1.5 }}>
              The DEST typing test is compulsory for all candidates. It evaluates typing accuracy on a computer keyboard for a given master passage.
            </p>
          </div>

          <div className="grid-3" style={{ gap: '16px' }}>
            <div className="glass-card" style={{ padding: '20px' }}>
              <span className="badge badge-verified" style={{ fontSize: '0.7rem', marginBottom: '8px' }}>SPEED BENCHMARK</span>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'white', margin: '6px 0' }}>2000</div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                Key depressions required in <strong>15 minutes</strong> (~27 Words Per Minute).
              </div>
            </div>

            <div className="glass-card" style={{ padding: '20px' }}>
              <span className="badge badge-demo" style={{ fontSize: '0.7rem', marginBottom: '8px' }}>UR MAX ERROR LIMIT</span>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#34d399', margin: '6px 0' }}>5% Error</div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                Maximum permissible error percentage for Unreserved (UR) category.
              </div>
            </div>

            <div className="glass-card" style={{ padding: '20px' }}>
              <span className="badge badge-demo" style={{ fontSize: '0.7rem', marginBottom: '8px' }}>RESERVED CATEGORIES</span>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#60a5fa', margin: '6px 0' }}>7% Error</div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                Permissible mistake margin for OBC, EWS, SC, ST, and PwBD candidates.
              </div>
            </div>
          </div>

          <div className="glass-card" style={{ padding: '24px' }}>
            <h5 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white', marginBottom: '12px' }}>
              Key Rules for Calculating Typing Errors
            </h5>
            <ul style={{ paddingLeft: '20px', margin: 0, fontSize: '0.88rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '8px', lineHeight: 1.5 }}>
              <li><strong style={{ color: 'white' }}>Full Mistakes:</strong> Omission of each word/figure, substitution of wrong word, and addition of words not found in the master passage.</li>
              <li><strong style={{ color: 'white' }}>Half Mistakes:</strong> Spacing errors (no space between two words or extra space), spelling errors (repetition or missing letters), wrong capitalisation.</li>
              <li><strong style={{ color: 'white' }}>Backspace Key:</strong> The backspace and arrow keys are fully functional on the examination software. Correct errors promptly as you type.</li>
            </ul>
          </div>
        </div>
      )}

      {/* STATUS 3: DOCUMENT VERIFICATION (DV) */}
      {selectedStatus === 'DOC_VERIFICATION' && (
        <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="glass-card" style={{ padding: '24px', borderLeft: '4px solid #a855f7' }}>
            <h4 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'white', margin: '0 0 8px' }}>
              Document Verification (DV) & Crucial Date Scrutiny Guidelines
            </h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0, lineHeight: 1.5 }}>
              Document Verification is conducted directly by the user departments/ministries post-shortlisting. Prepare your complete dossier in advance.
            </p>
          </div>

          <div className="glass-card" style={{ padding: '24px' }}>
            <h5 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white', marginBottom: '16px' }}>
              Mandatory Original Dossier Checklist
            </h5>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {[
                { title: 'Matriculation (10th) Certificate / Marksheet', desc: 'Proof of Date of Birth, Full Name, and Father\'s Name. Name must strictly match the admit card.' },
                { title: 'Essential Degree Certificate / Provisional Marksheet', desc: 'Must prove acquisition of Bachelor\'s Degree on or before the crucial cutoff date (01-08-2026).' },
                { title: 'OBC (Non-Creamy Layer) Certificate in Central Govt Format', desc: 'Must be issued in Annexure-VI format within 3 years prior to the application closing date.' },
                { title: 'EWS Income & Asset Certificate', desc: 'Valid for Financial Year 2026-2027 based on gross annual family income of previous FY 2025-2026.' },
                { title: 'SC / ST Caste Certificate', desc: 'Issued by designated competent authorities (District Magistrate / Tehsildar) in central format.' },
                { title: 'No Objection Certificate (NOC) for Govt Servants', desc: 'Mandatory for candidates already employed in Central/State Government departments.' }
              ].map(doc => (
                <div key={doc.title} style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                  <CheckCircle2 size={18} color="#a855f7" style={{ marginTop: '2px', flexShrink: 0 }} />
                  <div>
                    <div style={{ fontSize: '0.92rem', fontWeight: 700, color: 'white' }}>{doc.title}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>{doc.desc}</div>
                  </div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: '18px', display: 'flex', justifyContent: 'flex-end' }}>
              <button 
                className="btn btn-primary"
                onClick={() => onNavigateSection(4)}
                style={{ fontSize: '0.85rem', padding: '8px 18px', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                Review Application & Certificate Clauses (Section 4) <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* STATUS 4: NOT QUALIFIED (RECOVERY ROADMAP & ALTERNATIVE EXAMS) */}
      {selectedStatus === 'NOT_QUALIFIED' && (
        <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="glass-card" style={{ padding: '24px', borderLeft: '4px solid #ef4444' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(239,68,68,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#f87171' }}>
                <Target size={20} />
              </div>
              <h4 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'white', margin: 0 }}>
                Structured Diagnosis & Immediate Comeback Pathway
              </h4>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0, lineHeight: 1.5 }}>
              Missing the cutoff in a single examination cycle is normal in high-competition exams. The knowledge you built in Quantitative Aptitude, Reasoning, English, and General Awareness is <strong>100% transferable</strong> to upcoming major recruitment cycles.
            </p>
          </div>

          {/* Diagnosis Matrix */}
          <div className="glass-card" style={{ padding: '24px' }}>
            <h5 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white', marginBottom: '14px' }}>
              3-Step Post-Exam Diagnostic Audit
            </h5>

            <div className="grid-3" style={{ gap: '14px' }}>
              <div style={{ padding: '16px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)' }}>
                <span className="badge badge-demo" style={{ fontSize: '0.7rem' }}>STEP 1</span>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'white', margin: '8px 0 4px' }}>Inspect Raw vs Normalised Score</div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
                  Compare your response sheet marks with the shift difficulty multiplier. Hard shifts often receive substantial upward normalization (+8 to +15 marks).
                </p>
              </div>

              <div style={{ padding: '16px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)' }}>
                <span className="badge badge-demo" style={{ fontSize: '0.7rem' }}>STEP 2</span>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'white', margin: '8px 0 4px' }}>Negative Marking Audit</div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
                  Did blind guessing pull you down? In Tier-1, every 4 wrong answers forfeit 2 marks (-0.50 per error). Calculate net loss from unforced errors.
                </p>
              </div>

              <div style={{ padding: '16px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)' }}>
                <span className="badge badge-demo" style={{ fontSize: '0.7rem' }}>STEP 3</span>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'white', margin: '8px 0 4px' }}>Sectional Weak-Link Isolation</div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
                  Is Static GK scoring below 15 marks? Or did Arithmetic calculation speed cause time crunch? Target your singular bottleneck topic.
                </p>
              </div>
            </div>
          </div>

          {/* Alternative Overlapping Recruitment Exams */}
          <div className="glass-card" style={{ padding: '24px' }}>
            <h5 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white', marginBottom: '8px' }}>
              Immediate High-Synergy Target Exams (Overlapping Syllabus)
            </h5>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              These verified national recruitment cycles share 70% to 90% of your current preparation syllabus:
            </p>

            <div className="grid-2" style={{ gap: '14px' }}>
              <div style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '12px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <h6 style={{ fontSize: '1rem', fontWeight: 700, color: 'white', margin: 0 }}>IBPS PO & Banking CRP PO/MT-XVI</h6>
                    <span className="badge badge-verified" style={{ fontSize: '0.68rem' }}>80% OVERLAP</span>
                  </div>
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.45 }}>
                    High synergy in Quantitative Aptitude, Data Interpretation, and English. Faster selection timeline (joining in April 2027).
                  </p>
                </div>
                {onSelectAlternativeExam && (
                  <button 
                    className="btn btn-secondary"
                    onClick={() => onSelectAlternativeExam('IBPS_PO_2026')}
                    style={{ fontSize: '0.78rem', padding: '6px 14px', alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    View IBPS PO Roadmap <ArrowRight size={12} />
                  </button>
                )}
              </div>

              <div style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '12px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <h6 style={{ fontSize: '1rem', fontWeight: 700, color: 'white', margin: 0 }}>Railway Recruitment Board (RRB NTPC)</h6>
                    <span className="badge badge-verified" style={{ fontSize: '0.68rem' }}>90% OVERLAP</span>
                  </div>
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.45 }}>
                    Zero English required in CBT 1 & 2. High weightage on General Awareness, Science, Reasoning, and Basic Arithmetic.
                  </p>
                </div>
                <div style={{ fontSize: '0.75rem', color: '#93c5fd' }}>
                  Next Cycle Notification Opening Soon
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
