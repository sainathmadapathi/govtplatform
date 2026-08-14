import React, { useState } from 'react';
import { ShieldCheck, CheckCircle2, XCircle, AlertCircle, FileText, UserCheck, ChevronRight, HelpCircle } from 'lucide-react';
import { ALL_EXAMS, SSC_CGL_EXAM } from '../data/examsData';
import { evaluateCandidateEligibility } from '../services/eligibilityEngine';
import { UserProfile, Exam, EligibilityDiagnostic } from '../types/exam';

interface EligibilityCalculatorProps {
  onSelectExam: (exam: Exam) => void;
  onOpenProvenanceModal: (provenance: any) => void;
}

export const EligibilityCalculator: React.FC<EligibilityCalculatorProps> = ({ onSelectExam, onOpenProvenanceModal }) => {
  const [targetExamId, setTargetExamId] = useState<string>(SSC_CGL_EXAM.id);
  
  const [profile, setProfile] = useState<UserProfile>({
    age: 21,
    dateOfBirth: '2005-05-15',
    degree: 'B.Tech',
    branch: 'Computer Science & Engineering',
    percentage: 72,
    category: 'GENERAL',
    gender: 'Male',
    domicileState: 'Telangana'
  });

  const selectedExam = ALL_EXAMS.find(e => e.id === targetExamId) || SSC_CGL_EXAM;
  const diagnostic: EligibilityDiagnostic = evaluateCandidateEligibility(selectedExam, profile);

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* Header Banner */}
      <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(17, 24, 39, 0.8) 100%)', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '8px' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--emerald)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
            <UserCheck size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800 }}>
              Deterministic "Am I Eligible?" Diagnostic Engine
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              No guessing. No AI hallucinations. Evaluates profile parameters against verified official notification rules.
            </p>
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ alignItems: 'start' }}>
        
        {/* Left Column: Candidate Profile Input Form */}
        <div className="glass-card" style={{ padding: '28px' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck size={20} color="var(--primary)" /> Candidate Profile Form
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            
            {/* Target Exam Selection */}
            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Select Target Examination
              </label>
              <select 
                value={targetExamId}
                onChange={(e) => setTargetExamId(e.target.value)}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  color: 'white',
                  fontSize: '0.95rem',
                  fontWeight: 600,
                  outline: 'none'
                }}
              >
                {ALL_EXAMS.map(e => (
                  <option key={e.id} value={e.id}>{e.title}</option>
                ))}
              </select>
            </div>

            {/* Age & Date of Birth */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Current Age (Years)
                </label>
                <input 
                  type="number"
                  value={profile.age}
                  onChange={(e) => setProfile({ ...profile, age: Number(e.target.value) })}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    color: 'white',
                    outline: 'none'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Category
                </label>
                <select 
                  value={profile.category}
                  onChange={(e) => setProfile({ ...profile, category: e.target.value as any })}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    color: 'white',
                    outline: 'none'
                  }}
                >
                  <option value="GENERAL">General / UR</option>
                  <option value="OBC">OBC (Non-Creamy Layer)</option>
                  <option value="SC">Scheduled Caste (SC)</option>
                  <option value="ST">Scheduled Tribe (ST)</option>
                  <option value="EWS">EWS</option>
                  <option value="PwBD">PwBD (Disability)</option>
                </select>
              </div>
            </div>

            {/* Educational Qualification Degree & Branch */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Educational Degree
                </label>
                <select 
                  value={profile.degree}
                  onChange={(e) => setProfile({ ...profile, degree: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    color: 'white',
                    outline: 'none'
                  }}
                >
                  <option value="B.Tech">B.Tech / B.E</option>
                  <option value="Bachelor Degree">B.Sc / B.A / B.Com</option>
                  <option value="BBA">BBA / BCA</option>
                  <option value="Class 12th">Class 12th Senior Secondary</option>
                  <option value="Class 10th">Class 10th Secondary</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Specialization Branch
                </label>
                <input 
                  type="text"
                  value={profile.branch}
                  onChange={(e) => setProfile({ ...profile, branch: e.target.value })}
                  placeholder="e.g. Computer Science, Civil, Commerce..."
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    color: 'white',
                    outline: 'none'
                  }}
                />
              </div>
            </div>

            {/* Percentage & Domicile */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Degree Percentage (%)
                </label>
                <input 
                  type="number"
                  value={profile.percentage}
                  onChange={(e) => setProfile({ ...profile, percentage: Number(e.target.value) })}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    color: 'white',
                    outline: 'none'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Domicile State
                </label>
                <input 
                  type="text"
                  value={profile.domicileState}
                  onChange={(e) => setProfile({ ...profile, domicileState: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    color: 'white',
                    outline: 'none'
                  }}
                />
              </div>
            </div>

          </div>
        </div>

        {/* Right Column: Diagnostic Output Card */}
        <div className="glass-card" style={{ padding: '28px', borderLeft: diagnostic.isEligible ? '5px solid var(--emerald)' : '5px solid var(--rose)' }}>
          
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)' }}>
              ELIGIBILITY DIAGNOSTIC REPORT
            </span>
            <span className={`badge ${diagnostic.isEligible ? 'badge-verified' : 'badge-superseded'}`}>
              {diagnostic.status}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            {diagnostic.isEligible ? (
              <CheckCircle2 size={36} color="var(--emerald)" />
            ) : (
              <XCircle size={36} color="var(--rose)" />
            )}
            <div>
              <h3 style={{ fontSize: '1.4rem', fontWeight: 800 }}>
                {diagnostic.isEligible ? 'You Are Eligible!' : 'Qualification Mismatch'}
              </h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Evaluated against {selectedExam.title}
              </p>
            </div>
          </div>

          {/* AI Explanation Box */}
          <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', marginBottom: '20px', lineHeight: 1.6, fontSize: '0.9rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', fontWeight: 700, color: '#a855f7', textTransform: 'uppercase', marginBottom: '6px' }}>
              <HelpCircle size={14} /> GovOS Plain-English Explanation (Type C Taxonomy)
            </div>
            {diagnostic.plainEnglishExplanation}
          </div>

          {/* Post Cadre Breakdown */}
          <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>Post Cadre Eligibility Breakdown ({selectedExam.posts.length} Posts)</span>
            <button 
              className="btn btn-outline" 
              onClick={() => onOpenProvenanceModal(selectedExam.posts[0].provenance)}
              style={{ fontSize: '0.75rem', padding: '4px 10px' }}
            >
              <FileText size={12} /> Inspect Source Citation
            </button>
          </h4>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '24px' }}>
            {diagnostic.postVerdicts.map((pv, idx) => (
              <div 
                key={idx} 
                style={{ 
                  padding: '12px 16px', 
                  borderRadius: 'var(--radius-md)', 
                  background: pv.eligible ? 'rgba(16, 185, 129, 0.06)' : 'rgba(244, 63, 94, 0.06)',
                  border: `1px solid ${pv.eligible ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.2)'}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '12px'
                }}
              >
                <div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {pv.eligible ? <CheckCircle2 size={16} color="var(--emerald)" /> : <XCircle size={16} color="var(--rose)" />}
                    {pv.postName}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                    {pv.reason}
                  </div>
                </div>

                <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--primary)', cursor: 'pointer' }} onClick={() => onOpenProvenanceModal(selectedExam.posts[0].provenance)}>
                  [{pv.clause}]
                </span>
              </div>
            ))}
          </div>

          <button className="btn btn-emerald" onClick={() => onSelectExam(selectedExam)} style={{ width: '100%', padding: '12px' }}>
            Proceed to 14-Section Guide <ChevronRight size={18} />
          </button>

        </div>
      </div>
    </div>
  );
};
