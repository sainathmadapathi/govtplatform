import React, { useState } from 'react';
import { 
  FileText, CheckCircle2, AlertTriangle, ShieldCheck, ExternalLink, Camera, 
  PenTool, Award, HelpCircle, ChevronRight, ChevronDown, Clock, Info, XCircle,
  FileEdit, CheckSquare
} from 'lucide-react';
import { ApplicationGuideData, DataProvenance } from '../types/exam';
import { PracticeApplicationSimulator } from './PracticeApplicationSimulator';

interface ApplicationGuideProps {
  guide: ApplicationGuideData;
  onOpenProvenanceModal: (provenance: DataProvenance) => void;
}

export const ApplicationGuide: React.FC<ApplicationGuideProps> = ({
  guide,
  onOpenProvenanceModal
}) => {
  const [applicationMode, setApplicationMode] = useState<'PRACTICE_SIMULATOR' | 'INSTRUCTIONS'>('PRACTICE_SIMULATOR');
  const [activeTab, setActiveTab] = useState<'OTR_STEPS' | 'PHOTO_SIGNATURE' | 'CERTIFICATES' | 'PITFALLS'>('OTR_STEPS');
  const [expandedStep, setExpandedStep] = useState<number>(1);
  const [selectedCertCategory, setSelectedCertCategory] = useState<string>('OBC_NCL');
  const [certificateIssueDate, setCertificateIssueDate] = useState<string>('2025-06-15');
  const [certValidityResult, setCertValidityResult] = useState<{ valid: boolean; message: string } | null>(null);

  const handleCheckCertificate = () => {
    if (!certificateIssueDate) {
      setCertValidityResult({ valid: false, message: 'Please select a valid certificate issue date.' });
      return;
    }
    const issueDate = new Date(certificateIssueDate);
    const closingDate = new Date('2026-09-27');
    const threeYearsPrior = new Date('2023-09-27');

    if (selectedCertCategory === 'OBC_NCL') {
      if (issueDate >= threeYearsPrior && issueDate <= closingDate) {
        setCertValidityResult({
          valid: true,
          message: `✅ Certificate Issued on ${certificateIssueDate} is VALID! It falls within the 3-year crucial window prior to closing date (27-09-2023 to 27-09-2026) in compliance with Section 6.3.`
        });
      } else if (issueDate > closingDate) {
        setCertValidityResult({
          valid: false,
          message: `⚠️ Certificate Date (${certificateIssueDate}) is AFTER the application closing date (27-09-2026). SSC rules require the OBC-NCL certificate to be issued on or before 27-09-2026.`
        });
      } else {
        setCertValidityResult({
          valid: false,
          message: `❌ Certificate Date (${certificateIssueDate}) is older than 3 years (issued before 27-09-2023). You must obtain a renewed OBC-NCL certificate for the financial year 2025-26.`
        });
      }
    } else if (selectedCertCategory === 'EWS') {
      const ewsStart = new Date('2026-04-01');
      if (issueDate >= ewsStart && issueDate <= closingDate) {
        setCertValidityResult({
          valid: true,
          message: `✅ EWS Certificate Issued on ${certificateIssueDate} is VALID for Recruitment Year 2026-27 (evaluating FY 2025-26 income) under Annexure-VII.`
        });
      } else if (issueDate < ewsStart) {
        setCertValidityResult({
          valid: false,
          message: `⚠️ EWS Certificates issued prior to 01-04-2026 belong to the previous financial year. SSC requires an Income & Asset certificate issued in the current financial year (FY 2026-27).`
        });
      } else {
        setCertValidityResult({
          valid: false,
          message: `⚠️ Certificate issued after closing date (27-09-2026) may not be accepted during Document Verification.`
        });
      }
    } else {
      setCertValidityResult({
        valid: true,
        message: `✅ SC/ST certificates have permanent validity provided they are issued in the standard Central Government format (Annexure-V) by an authorized Tehsildar/DM.`
      });
    }
  };

  const selectedCert = guide.certificateRules.find(c => c.category === selectedCertCategory) || guide.certificateRules[0];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Header Banner */}
      <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span className="badge badge-verified">
                <ShieldCheck size={14} /> 100% OFFICIAL SSC APPLICATION PROTOCOL
              </span>
              <span className="badge badge-demo" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa' }}>
                ssc.gov.in (New Portal)
              </span>
            </div>
            <h2 style={{ fontSize: '1.75rem', fontWeight: 800, color: 'white', marginBottom: '6px' }}>
              Interactive Application & Document Compliance Assistant
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
              Complete step-by-step guidance on One-Time Registration (OTR), live camera photo framing, signature uploads, and certificate validity checking to ensure zero application rejection risk.
            </p>
          </div>

          <a 
            href={guide.officialPortal} 
            target="_blank" 
            rel="noreferrer" 
            className="btn btn-primary"
            style={{ padding: '12px 20px', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            Open Official SSC Portal <ExternalLink size={16} />
          </a>
        </div>
      </div>

      {/* Top Mode Switcher: Practice Simulator vs Step-by-Step Instructions */}
      <div style={{ display: 'flex', gap: '8px', background: 'rgba(255, 255, 255, 0.04)', padding: '6px', borderRadius: 'var(--radius-md)' }}>
        <button
          onClick={() => setApplicationMode('PRACTICE_SIMULATOR')}
          className={`btn ${applicationMode === 'PRACTICE_SIMULATOR' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ fontSize: '0.9rem', padding: '10px 18px', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
        >
          <FileEdit size={16} /> 📝 Practice Mock Application Simulator (Fill → Submit → Spot Mistakes)
        </button>
        <button
          onClick={() => setApplicationMode('INSTRUCTIONS')}
          className={`btn ${applicationMode === 'INSTRUCTIONS' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ fontSize: '0.9rem', padding: '10px 18px', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
        >
          <FileText size={16} /> 📖 Step-by-Step Instructions & Rules
        </button>
      </div>

      {/* VIEW 1: INTERACTIVE PRACTICE APPLICATION SIMULATOR */}
      {applicationMode === 'PRACTICE_SIMULATOR' && (
        <PracticeApplicationSimulator onOpenProvenanceModal={onOpenProvenanceModal} />
      )}

      {/* VIEW 2: STEP-BY-STEP INSTRUCTIONS & SPECIFICATIONS */}
      {applicationMode === 'INSTRUCTIONS' && (
        <>
          {/* Navigation Sub-Tabs */}
          <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px', overflowX: 'auto' }}>
            <button
              onClick={() => setActiveTab('OTR_STEPS')}
              className={`btn ${activeTab === 'OTR_STEPS' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <FileText size={16} /> 1. OTR & Registration Steps ({guide.otrSteps.length})
            </button>

            <button
              onClick={() => setActiveTab('PHOTO_SIGNATURE')}
              className={`btn ${activeTab === 'PHOTO_SIGNATURE' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <Camera size={16} /> 2. Live Photo & Signature Specs
            </button>

            <button
              onClick={() => setActiveTab('CERTIFICATES')}
              className={`btn ${activeTab === 'CERTIFICATES' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <Award size={16} /> 3. Category Certificate Validity Tool
            </button>

            <button
              onClick={() => setActiveTab('PITFALLS')}
              className={`btn ${activeTab === 'PITFALLS' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <AlertTriangle size={16} /> 4. Top 10 Rejection Pitfalls
            </button>
          </div>

      {/* Tab Content 1: OTR Steps */}
      {activeTab === 'OTR_STEPS' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ padding: '14px 18px', background: 'rgba(59, 130, 246, 0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(59, 130, 246, 0.3)', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Info size={22} color="#60a5fa" />
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'white' }}>Important Notice:</strong> SSC has permanently discontinued the old portal (<code style={{ color: '#93c5fd' }}>ssc.nic.in</code>). All aspirants must create a fresh <strong>One-Time Registration (OTR)</strong> on <code style={{ color: '#93c5fd' }}>ssc.gov.in</code>.
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {guide.otrSteps.map((step) => {
              const isExpanded = expandedStep === step.stepNumber;
              return (
                <div key={step.stepNumber} className="glass-card" style={{ padding: '0', overflow: 'hidden', border: isExpanded ? '1px solid var(--primary)' : '1px solid var(--border-color)' }}>
                  <div 
                    onClick={() => setExpandedStep(isExpanded ? 0 : step.stepNumber)}
                    style={{
                      padding: '18px 24px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      background: isExpanded ? 'rgba(59, 130, 246, 0.06)' : 'transparent'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <div style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: '50%',
                        background: isExpanded ? 'var(--primary)' : 'rgba(255, 255, 255, 0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 800,
                        fontSize: '0.95rem',
                        color: 'white'
                      }}>
                        {step.stepNumber}
                      </div>
                      <span style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white' }}>
                        {step.title}
                      </span>
                    </div>
                    {isExpanded ? <ChevronDown size={20} color="var(--text-secondary)" /> : <ChevronRight size={20} color="var(--text-secondary)" />}
                  </div>

                  {isExpanded && (
                    <div style={{ padding: '0 24px 24px 24px', borderTop: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '16px', paddingTop: '16px' }}>
                      <div>
                        <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#93c5fd', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '10px' }}>
                          Step-by-Step Action Items
                        </h4>
                        <ul style={{ listStyleType: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {step.instructions.map((inst, idx) => (
                            <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
                              <CheckCircle2 size={16} color="var(--emerald)" style={{ flexShrink: 0, marginTop: '3px' }} />
                              <span>{inst}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginTop: '8px' }}>
                        <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(16, 185, 129, 0.05)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#34d399', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                            <CheckCircle2 size={15} /> Mandatory Required Documents / Details
                          </span>
                          <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                            {step.mandatoryFields.map((field, fIdx) => (
                              <li key={fIdx} style={{ marginBottom: '4px' }}>{field}</li>
                            ))}
                          </ul>
                        </div>

                        <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(239, 68, 68, 0.05)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f87171', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                            <AlertTriangle size={15} /> Common Mistakes to Avoid
                          </span>
                          <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                            {step.commonMistakesToAvoid.map((mistake, mIdx) => (
                              <li key={mIdx} style={{ marginBottom: '4px' }}>{mistake}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab Content 2: Photo & Signature */}
      {activeTab === 'PHOTO_SIGNATURE' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          
          {/* Live Photo Box */}
          <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ padding: '10px', borderRadius: 'var(--radius-md)', background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa' }}>
                <Camera size={24} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white' }}>Live Webcam Photo Capture</h3>
                <span className="badge badge-verified" style={{ fontSize: '0.75rem', marginTop: '2px' }}>
                  SSC MANDATORY RULE
                </span>
              </div>
            </div>

            <div style={{ padding: '14px', background: 'rgba(0,0,0,0.3)', borderRadius: 'var(--radius-md)', border: '1px dashed var(--border-color)', textAlign: 'center' }}>
              <div style={{ fontSize: '0.85rem', color: '#93c5fd', fontWeight: 600 }}>Format: Live WebRTC / SSC App Stream</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>Upload of pre-saved passport photos is completely disabled.</div>
            </div>

            <div>
              <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '8px' }}>
                Official Photo Compliance Rules:
              </h4>
              <ul style={{ padding: 0, margin: 0, listStyleType: 'none', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {guide.photoRules.rules.map((rule, rIdx) => (
                  <li key={rIdx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                    <CheckCircle2 size={15} color="var(--emerald)" style={{ flexShrink: 0, marginTop: '3px' }} />
                    <span>{rule}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Scanned Signature Box */}
          <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ padding: '10px', borderRadius: 'var(--radius-md)', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>
                <PenTool size={24} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white' }}>Scanned Signature Specimen</h3>
                <span className="badge badge-verified" style={{ fontSize: '0.75rem', marginTop: '2px' }}>
                  DIMENSION: 4.0 cm × 2.0 cm
                </span>
              </div>
            </div>

            <div style={{ padding: '14px', background: 'rgba(0,0,0,0.3)', borderRadius: 'var(--radius-md)', border: '1px dashed var(--border-color)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', textAlign: 'center' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>FILE SIZE</span>
                <div style={{ fontWeight: 700, color: 'white' }}>10 KB to 20 KB</div>
              </div>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>FILE FORMAT</span>
                <div style={{ fontWeight: 700, color: 'white' }}>JPEG / JPG only</div>
              </div>
            </div>

            <div>
              <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '8px' }}>
                Official Signature Rules:
              </h4>
              <ul style={{ padding: 0, margin: 0, listStyleType: 'none', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {guide.signatureRules.rules.map((rule, rIdx) => (
                  <li key={rIdx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                    <CheckCircle2 size={15} color="var(--emerald)" style={{ flexShrink: 0, marginTop: '3px' }} />
                    <span>{rule}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Tab Content 3: Certificate Validity Checker */}
      {activeTab === 'CERTIFICATES' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="glass-card" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '6px' }}>
              Official Reservation Certificate Financial Year & Crucial Date Validator
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '20px' }}>
              Verify whether your category certificate meets the strict Central Government cutoff dates and DoP&T format guidelines.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '20px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Select Reservation Category
                </label>
                <select
                  value={selectedCertCategory}
                  onChange={(e) => {
                    setSelectedCertCategory(e.target.value);
                    setCertValidityResult(null);
                  }}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    color: 'white',
                    fontSize: '0.95rem'
                  }}
                >
                  <option value="OBC_NCL">OBC (Non-Creamy Layer)</option>
                  <option value="EWS">Economically Weaker Section (EWS)</option>
                  <option value="SC_ST">SC / ST (Scheduled Caste / Tribe)</option>
                  <option value="PwBD">PwBD (Persons with Benchmark Disabilities)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Certificate Issue Date
                </label>
                <input
                  type="date"
                  value={certificateIssueDate}
                  onChange={(e) => {
                    setCertificateIssueDate(e.target.value);
                    setCertValidityResult(null);
                  }}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    color: 'white',
                    fontSize: '0.95rem'
                  }}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                <button 
                  onClick={handleCheckCertificate}
                  className="btn btn-emerald"
                  style={{ width: '100%', padding: '11px', fontSize: '0.95rem' }}
                >
                  Validate Certificate Date
                </button>
              </div>
            </div>

            {certValidityResult && (
              <div style={{
                padding: '16px',
                borderRadius: 'var(--radius-md)',
                background: certValidityResult.valid ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                border: certValidityResult.valid ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid rgba(239, 68, 68, 0.4)',
                fontSize: '0.95rem',
                color: certValidityResult.valid ? '#34d399' : '#f87171',
                marginBottom: '20px'
              }}>
                {certValidityResult.message}
              </div>
            )}

            {/* Selected Certificate Official Specs */}
            <div style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white' }}>{selectedCert.title}</h4>
                <span className="badge badge-verified">{selectedCert.officialAnnexure}</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px', fontSize: '0.88rem' }}>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Financial Year / Validity:</span>
                  <div style={{ fontWeight: 600, color: 'white' }}>{selectedCert.financialYearValidity}</div>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Crucial Date Window:</span>
                  <div style={{ fontWeight: 600, color: '#93c5fd' }}>{selectedCert.crucialDate}</div>
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Competent Issuing Authorities:</span>
                <div style={{ fontSize: '0.9rem', color: 'white', marginTop: '2px' }}>
                  {selectedCert.issuingAuthority.join(' • ')}
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Key Legal Conditions:</span>
                <ul style={{ margin: '4px 0 0 0', paddingLeft: '18px', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                  {selectedCert.keyConditions.map((cond, cIdx) => (
                    <li key={cIdx} style={{ marginBottom: '3px' }}>{cond}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab Content 4: Top 10 Pitfalls */}
      {activeTab === 'PITFALLS' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ padding: '14px 18px', background: 'rgba(239, 68, 68, 0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(239, 68, 68, 0.3)', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <AlertTriangle size={22} color="#f87171" />
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Over <strong>2.5 Lakh applications</strong> are cancelled each year in SSC examinations due to preventable administrative and photo errors. Review these 10 pitfalls carefully.
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
            {guide.rejectionPitfalls.map((pitfall, pIdx) => (
              <div key={pIdx} className="glass-card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{
                    width: '26px',
                    height: '26px',
                    borderRadius: '50%',
                    background: 'rgba(239, 68, 68, 0.2)',
                    color: '#f87171',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 800,
                    fontSize: '0.85rem'
                  }}>
                    {pIdx + 1}
                  </div>
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'white' }}>
                    {pitfall.pitfall}
                  </h4>
                </div>

                <div style={{ padding: '10px', borderRadius: 'var(--radius-sm)', background: 'rgba(239, 68, 68, 0.05)', fontSize: '0.85rem', color: '#fca5a5' }}>
                  <strong>Consequence:</strong> {pitfall.consequence}
                </div>

                <div style={{ padding: '10px', borderRadius: 'var(--radius-sm)', background: 'rgba(16, 185, 129, 0.05)', fontSize: '0.85rem', color: '#86efac' }}>
                  <strong>How to Prevent:</strong> {pitfall.prevention}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      </>
      )}

    </div>
  );
};
