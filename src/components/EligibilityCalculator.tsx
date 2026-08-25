import React, { useState } from 'react';
import { 
  ShieldCheck, CheckCircle2, XCircle, FileText, UserCheck, ChevronRight, 
  HelpCircle, AlertTriangle, Filter, Award, Sparkles, Building, Briefcase
} from 'lucide-react';
import { ALL_EXAMS, SSC_CGL_EXAM } from '../data/examsData';
import { evaluateEligibility } from '../services/eligibilityEngine';
import { calculateDetailedAge, getCategoryAgeRelaxation } from '../services/profileUtils';
import { UserProfile, Exam, EligibilityDiagnostic, DataProvenance } from '../types/exam';

interface EligibilityCalculatorProps {
  onSelectExam?: (exam: Exam) => void;
  onOpenProvenanceModal: (provenance: DataProvenance) => void;
}

export const EligibilityCalculator: React.FC<EligibilityCalculatorProps> = ({ 
  onSelectExam, 
  onOpenProvenanceModal 
}) => {
  const [profile, setProfile] = useState<UserProfile>({
    dateOfBirth: '2001-05-15',
    degree: 'B.Tech',
    branch: 'Computer Science',
    percentage: 75,
    category: 'GENERAL',
    gender: 'Male',
    domicileState: 'Telangana',
    nationality: 'INDIAN',
    mathsIn12thWith60Percent: true,
    statisticsInDegree: false,
    physicalFitnessDeclared: true,
    colorBlind: false
  });

  const [postFilter, setPostFilter] = useState<'ALL' | 'ELIGIBLE' | 'INELIGIBLE' | 'PHYSICAL'>('ALL');

  const selectedExam = SSC_CGL_EXAM;
  const diagnostic: EligibilityDiagnostic = evaluateEligibility(selectedExam, profile);
  const detailedAge = calculateDetailedAge(profile.dateOfBirth, selectedExam.crucialEligibilityDate || '2026-08-01');
  const relaxation = getCategoryAgeRelaxation(profile.category);

  const filteredPosts = diagnostic.postVerdicts.filter(post => {
    if (postFilter === 'ELIGIBLE') return post.eligible;
    if (postFilter === 'INELIGIBLE') return !post.eligible;
    if (postFilter === 'PHYSICAL') {
      const pReq = selectedExam.posts.find(p => p.id === post.postId);
      return pReq?.physicalRequired;
    }
    return true;
  });

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* Header Banner */}
      <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(17, 24, 39, 0.95) 100%)', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{ width: '42px', height: '42px', borderRadius: '10px', background: 'var(--emerald)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
              <UserCheck size={24} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <span className="badge badge-verified">
                  <ShieldCheck size={14} /> 100% DETERMINISTIC POST-BY-POST ENGINE
                </span>
                <span className="badge badge-demo" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa' }}>
                  Crucial Cutoff: {selectedExam.crucialEligibilityDate}
                </span>
              </div>
              <h2 style={{ fontSize: '1.6rem', fontWeight: 800, color: 'white', margin: 0 }}>
                SSC CGL Deterministic Eligibility & Post Allocation Engine
              </h2>
            </div>
          </div>

          <div style={{ padding: '12px 20px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', textAlign: 'right' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ELIGIBLE POSTS</span>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: diagnostic.totalEligiblePosts > 0 ? 'var(--emerald)' : 'var(--rose)' }}>
              {diagnostic.totalEligiblePosts} / {diagnostic.totalAvailablePosts}
            </div>
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ alignItems: 'start' }}>
        
        {/* Left Column: Candidate Profile Input Form */}
        <div className="glass-card" style={{ padding: '28px' }}>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck size={20} color="var(--primary)" /> Candidate Profile Form
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            
            {/* Date of Birth & Category */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Date of Birth (DOB)
                </label>
                <input 
                  type="date"
                  value={profile.dateOfBirth}
                  onChange={(e) => setProfile({ ...profile, dateOfBirth: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    color: 'white',
                    fontSize: '0.92rem'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Reservation Category
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
                    fontSize: '0.92rem'
                  }}
                >
                  <option value="GENERAL">General (UR) - 0 Yrs</option>
                  <option value="OBC">OBC (Non-Creamy Layer) - +3 Yrs</option>
                  <option value="SC">SC (Scheduled Caste) - +5 Yrs</option>
                  <option value="ST">ST (Scheduled Tribe) - +5 Yrs</option>
                  <option value="EWS">EWS (Economically Weaker) - 0 Yrs</option>
                  <option value="PwBD">PwBD (Persons with Disability) - +10 Yrs</option>
                </select>
              </div>
            </div>

            {/* Calculated Age Card */}
            <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: '#93c5fd', textTransform: 'uppercase', fontWeight: 700 }}>
                  Calculated Age on 01-08-2026 (Crucial Date)
                </span>
                <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'white', marginTop: '2px' }}>
                  {detailedAge.years} Years, {detailedAge.months} Months, {detailedAge.days} Days
                </div>
              </div>
              <span className="badge badge-verified" style={{ fontSize: '0.75rem' }}>
                {profile.category} (+{relaxation} Yrs)
              </span>
            </div>

            {/* Degree & Branch */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Graduation Degree
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
                    fontSize: '0.92rem'
                  }}
                >
                  <option value="B.Tech">B.Tech / B.E (Engineering)</option>
                  <option value="B.Sc">B.Sc (Science / Stats / Maths)</option>
                  <option value="B.Com">B.Com (Commerce)</option>
                  <option value="B.A">B.A (Arts / Humanities)</option>
                  <option value="BBA">BBA / Management</option>
                  <option value="BCA">BCA (Computer Applications)</option>
                  <option value="Final Year">Final Year Degree (Appearing)</option>
                  <option value="12th Pass">12th Pass Only (Ineligible)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Degree Specialization / Branch
                </label>
                <input 
                  type="text"
                  value={profile.branch}
                  onChange={(e) => setProfile({ ...profile, branch: e.target.value })}
                  placeholder="e.g. Computer Science, Statistics"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    color: 'white',
                    fontSize: '0.92rem'
                  }}
                />
              </div>
            </div>

            {/* Special Academic Criteria (JSO & Statistical Investigator) */}
            <div style={{ padding: '16px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#93c5fd', textTransform: 'uppercase' }}>
                Specialized Academic Criteria Checks
              </span>

              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.88rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={profile.mathsIn12thWith60Percent}
                  onChange={(e) => setProfile({ ...profile, mathsIn12thWith60Percent: e.target.checked })}
                  style={{ width: '16px', height: '16px' }}
                />
                <span>Secured <strong>60%+ in Mathematics</strong> in 12th standard (JSO eligibility)</span>
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.88rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={profile.statisticsInDegree}
                  onChange={(e) => setProfile({ ...profile, statisticsInDegree: e.target.checked })}
                  style={{ width: '16px', height: '16px' }}
                />
                <span>Studied <strong>Statistics</strong> in all 3 years / semesters of Degree (Statistical Investigator Gr II)</span>
              </label>
            </div>

            {/* Physical Standards & Medical Check */}
            <div style={{ padding: '16px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#93c5fd', textTransform: 'uppercase' }}>
                Uniformed Posts Physical & Vision Criteria (CBIC / CBI / NIA)
              </span>

              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.88rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={profile.physicalFitnessDeclared}
                  onChange={(e) => setProfile({ ...profile, physicalFitnessDeclared: e.target.checked })}
                  style={{ width: '16px', height: '16px' }}
                />
                <span>I meet the physical height, chest & endurance standards (Walking/Cycling)</span>
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.88rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={profile.colorBlind}
                  onChange={(e) => setProfile({ ...profile, colorBlind: e.target.checked })}
                  style={{ width: '16px', height: '16px' }}
                />
                <span>I have <strong>Color Blindness</strong> (Restricts Excise / Customs / Narcotics Inspector)</span>
              </label>
            </div>

          </div>
        </div>

        {/* Right Column: Diagnostic Summary & Post Verdicts */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Main Verdict Card */}
          <div className="glass-card" style={{ padding: '24px', border: diagnostic.isEligible ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid rgba(239, 68, 68, 0.4)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              {diagnostic.isEligible ? (
                <div style={{ width: '38px', height: '38px', borderRadius: '50%', background: 'rgba(16, 185, 129, 0.2)', color: 'var(--emerald)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <CheckCircle2 size={22} />
                </div>
              ) : (
                <div style={{ width: '38px', height: '38px', borderRadius: '50%', background: 'rgba(239, 68, 68, 0.2)', color: 'var(--rose)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <XCircle size={22} />
                </div>
              )}
              <div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'white', margin: 0 }}>
                  {diagnostic.status === 'ELIGIBLE' && 'Fully Eligible for SSC CGL'}
                  {diagnostic.status === 'CONDITIONAL' && 'Partially Eligible (Post-Specific Constraints)'}
                  {diagnostic.status === 'INELIGIBLE' && 'Ineligible for SSC CGL 2026'}
                </h3>
                <span className="badge badge-verified" style={{ fontSize: '0.75rem', marginTop: '3px' }}>
                  {diagnostic.categoryRelaxationApplied}
                </span>
              </div>
            </div>

            <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '16px' }}>
              {diagnostic.plainEnglishExplanation}
            </p>

            <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.3)', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              <strong>Official Sourced Clauses:</strong>
              <ul style={{ margin: '4px 0 0 0', paddingLeft: '16px' }}>
                {diagnostic.legalClauses.map((cl, cIdx) => (
                  <li key={cIdx}>{cl}</li>
                ))}
              </ul>
            </div>
          </div>

          {/* Post Filter Bar */}
          <div style={{ display: 'flex', gap: '8px', overflowX: 'auto' }}>
            <button
              onClick={() => setPostFilter('ALL')}
              className={`btn ${postFilter === 'ALL' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.82rem', padding: '6px 12px' }}
            >
              All Posts ({diagnostic.totalAvailablePosts})
            </button>
            <button
              onClick={() => setPostFilter('ELIGIBLE')}
              className={`btn ${postFilter === 'ELIGIBLE' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.82rem', padding: '6px 12px' }}
            >
              Eligible ({diagnostic.totalEligiblePosts})
            </button>
            <button
              onClick={() => setPostFilter('INELIGIBLE')}
              className={`btn ${postFilter === 'INELIGIBLE' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.82rem', padding: '6px 12px' }}
            >
              Ineligible ({diagnostic.totalAvailablePosts - diagnostic.totalEligiblePosts})
            </button>
            <button
              onClick={() => setPostFilter('PHYSICAL')}
              className={`btn ${postFilter === 'PHYSICAL' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.82rem', padding: '6px 12px' }}
            >
              Uniformed / Physical Posts
            </button>
          </div>

          {/* Post-by-Post Cards List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '550px', overflowY: 'auto', paddingRight: '4px' }}>
            {filteredPosts.map(post => {
              const pReq = selectedExam.posts.find(p => p.id === post.postId);
              return (
                <div
                  key={post.postId}
                  className="glass-card"
                  style={{
                    padding: '16px 20px',
                    borderLeft: post.eligible ? '4px solid var(--emerald)' : '4px solid var(--rose)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                    <div>
                      <h4 style={{ fontSize: '1rem', fontWeight: 800, color: 'white', margin: 0 }}>
                        {post.postName}
                      </h4>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                        {post.department} • <strong style={{ color: '#93c5fd' }}>{post.payLevel}</strong> ({pReq?.payScale})
                      </div>
                    </div>

                    <span className={post.eligible ? 'badge badge-verified' : 'badge badge-superseded'} style={{ fontSize: '0.75rem' }}>
                      {post.eligible ? 'ELIGIBLE' : 'DISQUALIFIED'}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.85rem', color: post.eligible ? 'var(--text-secondary)' : '#fca5a5', lineHeight: 1.4 }}>
                    {post.reason}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '8px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <span>Age Rule: {pReq?.minAge}–{post.maxPermissibleAge} Yrs (with +{relaxation} yrs {profile.category})</span>
                    {pReq?.provenance && (
                      <button 
                        onClick={() => onOpenProvenanceModal(pReq.provenance)}
                        className="btn btn-outline" 
                        style={{ fontSize: '0.7rem', padding: '2px 6px' }}
                      >
                        <ShieldCheck size={11} /> {post.officialClause}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

        </div>

      </div>

    </div>
  );
};
