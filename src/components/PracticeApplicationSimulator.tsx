import React, { useState } from 'react';
import { 
  FileText, CheckCircle2, XCircle, AlertTriangle, ShieldCheck, 
  HelpCircle, ChevronRight, ChevronLeft, RotateCcw, Camera, 
  PenTool, Eye, Database, Info, Award, CheckSquare, Square,
  Upload, Image as ImageIcon, FileCheck, Sparkles, Check
} from 'lucide-react';
import { storageService } from '../services/storageService';

interface PracticeApplicationSimulatorProps {
  onOpenProvenanceModal?: (prov: any) => void;
}

interface UploadedFileMeta {
  file: File | null;
  previewUrl: string;
  name: string;
  sizeKb: number;
  width?: number;
  height?: number;
  aspectRatio?: number;
  isSizeValid: boolean;
  isDimensionValid: boolean;
  validationMessage: string;
}

interface FormState {
  // Step 1: Personal Details
  candidateName: string;
  fatherName: string;
  motherName: string;
  dob: string;
  gender: 'Male' | 'Female' | 'Transgender';
  aadhaarNumber: string;
  nationality: string;

  // Step 2: Education Details
  highestQualification: string;
  graduationStatus: string;
  graduationStream: string;
  mathTwelfthPercentage: number;
  hasStatisticsInDegree: boolean;
  marksheetUpload: UploadedFileMeta | null;

  // Step 3: Category & Relaxation
  category: 'UR' | 'OBC_NCL' | 'EWS' | 'SC' | 'ST';
  seekingAgeRelaxation: boolean;
  isPwBD: boolean;
  isExServiceman: boolean;
  certUpload: UploadedFileMeta | null;

  // Step 4: Post Preferences
  pref1: string;
  pref2: string;
  pref3: string;
  pref4: string;

  // Step 5: Photo & Signature
  uploadMode: 'REAL_UPLOAD' | 'PRESET_TRAPS';
  photoType: 'CLEAN_WHITE_BG' | 'WITH_GLASSES' | 'WITH_CAP' | 'BLURRY_SELFIE';
  signType: 'VALID_RUNNING_HAND' | 'CAPITAL_LETTERS' | 'BLURRY_SIGN';
  photoUpload: UploadedFileMeta | null;
  signUpload: UploadedFileMeta | null;
  declarationAgreed: boolean;
}

interface ErrorItem {
  id: string;
  title: string;
  severity: 'CRITICAL' | 'WARNING';
  problem: string;
  whyItMatters: string;
  rememberRule: string;
  officialClause: string;
}

export const PracticeApplicationSimulator: React.FC<PracticeApplicationSimulatorProps> = () => {
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [isSubmitted, setIsSubmitted] = useState<boolean>(false);

  const initialFormState: FormState = {
    candidateName: 'Rahul Sharma',
    fatherName: 'Suresh Sharma',
    motherName: 'Sunita Sharma',
    dob: '1998-05-14',
    gender: 'Male',
    aadhaarNumber: 'XXXX-XXXX-1234',
    nationality: 'Citizen of India',

    highestQualification: 'Bachelor Degree (Graduation)',
    graduationStatus: 'Passed on or before 01-08-2026',
    graduationStream: 'Commerce / General',
    mathTwelfthPercentage: 54,
    hasStatisticsInDegree: false,
    marksheetUpload: null,

    category: 'UR',
    seekingAgeRelaxation: false,
    isPwBD: false,
    isExServiceman: false,
    certUpload: null,

    pref1: 'post-jso',
    pref2: 'post-aso-css',
    pref3: 'post-iti',
    pref4: 'post-excise',

    uploadMode: 'REAL_UPLOAD',
    photoType: 'WITH_GLASSES',
    signType: 'VALID_RUNNING_HAND',
    photoUpload: null,
    signUpload: null,
    declarationAgreed: true
  };

  const [form, setForm] = useState<FormState>(initialFormState);

  const postsList = [
    { id: 'post-aso-css', name: 'Assistant Section Officer (Central Secretariat Service - CSS)' },
    { id: 'post-iti', name: 'Inspector of Income Tax (CBDT)' },
    { id: 'post-excise', name: 'Inspector (Central Excise & GST - CBIC)' },
    { id: 'post-jso', name: 'Junior Statistical Officer (JSO - MoSPI)' },
    { id: 'post-cbi-si', name: 'Sub-Inspector (Central Bureau of Investigation - CBI)' },
    { id: 'post-tax-asst', name: 'Tax Assistant (CBDT / CBIC)' },
    { id: 'post-auditor', name: 'Auditor (Office of C&AG / CGA)' }
  ];

  // Helper: Live Photo File Inspector (Official SSC Gazette Section 7.2)
  const handlePhotoFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const isJpg = file.type === 'image/jpeg' || file.name.toLowerCase().endsWith('.jpg') || file.name.toLowerCase().endsWith('.jpeg');
    const sizeKb = Number((file.size / 1024).toFixed(2));
    const isSizeValid = sizeKb >= 20 && sizeKb <= 50;

    const previewUrl = URL.createObjectURL(file);
    const img = new Image();
    img.src = previewUrl;
    img.onload = () => {
      const width = img.naturalWidth;
      const height = img.naturalHeight;
      const aspectRatio = Number((width / height).toFixed(2));
      // Official SSC standard: 3.5cm x 4.5cm (~0.77 aspect ratio)
      const isDimensionValid = aspectRatio >= 0.65 && aspectRatio <= 0.90 && height >= 250;

      let msg = '';
      if (!isJpg) {
        msg = `❌ Invalid File Format (${file.name.split('.').pop()?.toUpperCase()}). Official SSC Notice Section 7.2 strictly mandates JPEG / JPG format only.`;
      } else if (!isSizeValid) {
        msg = `❌ File size is ${sizeKb} KB (Official limit: 20.0 KB to 50.0 KB).`;
      } else if (!isDimensionValid) {
        msg = `⚠️ Dimensions are ${width}×${height}px (Aspect ratio ${aspectRatio}). Official requirement: 3.5cm × 4.5cm vertical portrait.`;
      } else {
        msg = `✅ 100% Official Match! Format: JPEG, Size: ${sizeKb} KB, Dimensions: ${width}×${height}px. Complies with Section 7.2.`;
      }

      setForm(prev => ({
        ...prev,
        photoUpload: {
          file,
          previewUrl,
          name: file.name,
          sizeKb,
          width,
          height,
          aspectRatio,
          isSizeValid: isSizeValid && isJpg,
          isDimensionValid,
          validationMessage: msg
        }
      }));
    };
  };

  // Helper: Live Signature File Inspector (Official SSC Gazette Section 7.3)
  const handleSignFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const isJpg = file.type === 'image/jpeg' || file.name.toLowerCase().endsWith('.jpg') || file.name.toLowerCase().endsWith('.jpeg');
    const sizeKb = Number((file.size / 1024).toFixed(2));
    const isSizeValid = sizeKb >= 10 && sizeKb <= 20;

    const previewUrl = URL.createObjectURL(file);
    const img = new Image();
    img.src = previewUrl;
    img.onload = () => {
      const width = img.naturalWidth;
      const height = img.naturalHeight;
      const aspectRatio = Number((width / height).toFixed(2));
      // Official SSC standard: 4.0cm x 2.0cm landscape (~2.0 - 2.5 aspect ratio)
      const isDimensionValid = aspectRatio >= 1.4 && width >= 80;

      let msg = '';
      if (!isJpg) {
        msg = `❌ Invalid File Format (${file.name.split('.').pop()?.toUpperCase()}). Official SSC Notice Section 7.3 strictly mandates JPEG / JPG format only.`;
      } else if (!isSizeValid) {
        msg = `❌ File size is ${sizeKb} KB (Official limit: 10.0 KB to 20.0 KB).`;
      } else if (!isDimensionValid) {
        msg = `⚠️ Dimensions are ${width}×${height}px. Official requirement: 4.0cm × 2.0cm horizontal format.`;
      } else {
        msg = `✅ 100% Official Match! Format: JPEG, Size: ${sizeKb} KB, Dimensions: ${width}×${height}px. Complies with Section 7.3.`;
      }

      setForm(prev => ({
        ...prev,
        signUpload: {
          file,
          previewUrl,
          name: file.name,
          sizeKb,
          width,
          height,
          aspectRatio,
          isSizeValid: isSizeValid && isJpg,
          isDimensionValid,
          validationMessage: msg
        }
      }));
    };
  };

  // Helper: Marksheet / Certificate Upload Inspector
  const handleDocFileChange = (e: React.ChangeEvent<HTMLInputElement>, type: 'marksheet' | 'certificate') => {
    const file = e.target.files?.[0];
    if (!file) return;

    const sizeKb = Number((file.size / 1024).toFixed(2));
    const isSizeValid = sizeKb <= 500;
    const previewUrl = URL.createObjectURL(file);
    const msg = isSizeValid 
      ? `✅ File uploaded: ${file.name} (${sizeKb} KB). Meets PDF/Image upload size limit (< 500 KB).`
      : `⚠️ File size is ${sizeKb} KB (Exceeds maximum allowable 500 KB limit).`;

    const meta: UploadedFileMeta = {
      file,
      previewUrl,
      name: file.name,
      sizeKb,
      isSizeValid,
      isDimensionValid: true,
      validationMessage: msg
    };

    if (type === 'marksheet') {
      setForm(prev => ({ ...prev, marksheetUpload: meta }));
    } else {
      setForm(prev => ({ ...prev, certUpload: meta }));
    }
  };

  // Intelligent Rules Engine calculating exact mistakes
  const evaluateApplication = (): { mistakes: ErrorItem[]; passedChecks: string[] } => {
    const mistakes: ErrorItem[] = [];
    const passedChecks: string[] = [];

    // Check 0: Percentage Number Range Validation
    if (form.mathTwelfthPercentage > 100 || form.mathTwelfthPercentage < 0) {
      mistakes.push({
        id: 'err-percentage-invalid',
        title: 'Impossible Percentage Value Entered',
        severity: 'CRITICAL',
        problem: `You entered ${form.mathTwelfthPercentage}% in 12th Mathematics. Percentage values cannot exceed 100% or fall below 0%.`,
        whyItMatters: 'Submitting impossible numerical values leads to immediate application rejection during data verification scrutiny.',
        rememberRule: 'Enter your exact aggregate percentage between 0.00% and 100.00% as stated on your official marksheet.',
        officialClause: 'SSC Gazette Section 8.1 & Form Validation Rules'
      });
    }

    // Check 1: JSO Post Preference vs Educational Qualification
    const selectedJSO = [form.pref1, form.pref2, form.pref3, form.pref4].includes('post-jso');
    if (selectedJSO) {
      const meetsMath = form.mathTwelfthPercentage >= 60 && form.mathTwelfthPercentage <= 100;
      const meetsStats = form.hasStatisticsInDegree;
      if (!meetsMath && !meetsStats) {
        mistakes.push({
          id: 'err-jso-qualification',
          title: 'Post Preference vs Educational Qualification Mismatch',
          severity: 'CRITICAL',
          problem: `You selected Junior Statistical Officer (JSO) as a top preference, but entered ${form.mathTwelfthPercentage}% in 12th Mathematics and no Statistics degree subject.`,
          whyItMatters: 'Section 8.1 mandates at least 60% in 12th Mathematics OR Statistics at degree level for JSO. Non-eligible candidates fail document verification.',
          rememberRule: 'Always verify post-specific educational criteria before submitting preference codes.',
          officialClause: 'SSC Gazette Section 8.1 & Clause 13.3'
        });
      } else if (form.mathTwelfthPercentage <= 100) {
        passedChecks.push('Educational qualification strictly satisfies Junior Statistical Officer (JSO) statutory criteria.');
      }
    } else {
      passedChecks.push('Post preferences match standard graduation degree requirements.');
    }

    // Check 2: Photograph Verification (Real Upload OR Preset Traps)
    if (form.uploadMode === 'REAL_UPLOAD') {
      if (!form.photoUpload) {
        mistakes.push({
          id: 'err-photo-missing',
          title: 'Photograph Not Uploaded',
          severity: 'CRITICAL',
          problem: 'No candidate photograph was uploaded.',
          whyItMatters: 'Application cannot be submitted without a valid compliant live photograph.',
          rememberRule: 'Upload a 20 KB - 50 KB vertical passport photograph.',
          officialClause: 'SSC Gazette Section 7.2'
        });
      } else {
        if (!form.photoUpload.isSizeValid) {
          mistakes.push({
            id: 'err-photo-size',
            title: `Uploaded Photo Size Violation (${form.photoUpload.sizeKb} KB)`,
            severity: 'CRITICAL',
            problem: `Uploaded photo is ${form.photoUpload.sizeKb} KB. Official SSC portal strictly enforces 20 KB to 50 KB.`,
            whyItMatters: 'Files larger than 50 KB or smaller than 20 KB are blocked by the SSC portal server.',
            rememberRule: 'Compress your photograph to 25-45 KB before uploading.',
            officialClause: 'SSC Gazette Section 7.2'
          });
        }
        if (!form.photoUpload.isDimensionValid) {
          mistakes.push({
            id: 'err-photo-dimensions',
            title: `Uploaded Photo Aspect Ratio Error (${form.photoUpload.width}×${form.photoUpload.height}px)`,
            severity: 'WARNING',
            problem: `Uploaded photo aspect ratio (${form.photoUpload.aspectRatio}) is not standard passport portrait (3.5cm × 4.5cm).`,
            whyItMatters: 'Distorted or horizontal landscape photos result in stretched facial biometrics.',
            rememberRule: 'Ensure image width is ~350px and height is ~450px.',
            officialClause: 'SSC Gazette Section 7.2'
          });
        }
        if (form.photoUpload.isSizeValid && form.photoUpload.isDimensionValid) {
          passedChecks.push(`Uploaded photograph (${form.photoUpload.sizeKb} KB, ${form.photoUpload.width}×${form.photoUpload.height}px) strictly complies with Section 7.2.`);
        }
      }
    } else {
      // Preset Traps Check
      if (form.photoType === 'WITH_GLASSES') {
        mistakes.push({
          id: 'err-photo-glasses',
          title: 'Photograph Non-Compliance (Wearing Spectacles / Sunglasses)',
          severity: 'CRITICAL',
          problem: 'Photograph uploaded shows the candidate wearing spectacles/glasses.',
          whyItMatters: 'SSC Notice Section 7.2 strictly forbids spectacles or tinted glasses in live/uploaded photos due to glare causing automated facial recognition rejection.',
          rememberRule: 'Always remove spectacles, tinted glasses, and caps before capturing live application photos.',
          officialClause: 'SSC Gazette Section 7.2 (Sample Photo Annexure)'
        });
      } else if (form.photoType === 'WITH_CAP') {
        mistakes.push({
          id: 'err-photo-cap',
          title: 'Photograph Non-Compliance (Wearing Cap / Hat)',
          severity: 'CRITICAL',
          problem: 'Photograph shows headwear/cap covering the forehead.',
          whyItMatters: 'Cap or hats obstruct facial biometrics, leading to automatic computer vision disqualification.',
          rememberRule: 'Both ears and full forehead must be completely visible under clear lighting.',
          officialClause: 'SSC Gazette Section 7.2'
        });
      } else {
        passedChecks.push('Photograph adheres 100% to plain background, zero-spectacles, and clear biometrics rules.');
      }
    }

    // Check 3: Signature Verification (Real Upload OR Preset Traps)
    if (form.uploadMode === 'REAL_UPLOAD') {
      if (!form.signUpload) {
        mistakes.push({
          id: 'err-sign-missing',
          title: 'Signature Not Uploaded',
          severity: 'CRITICAL',
          problem: 'No signature file was uploaded.',
          whyItMatters: 'Application cannot be submitted without a valid signature image.',
          rememberRule: 'Upload a 10 KB - 20 KB running handwriting signature.',
          officialClause: 'SSC Gazette Section 7.3'
        });
      } else {
        if (!form.signUpload.isSizeValid) {
          mistakes.push({
            id: 'err-sign-size',
            title: `Uploaded Signature Size Violation (${form.signUpload.sizeKb} KB)`,
            severity: 'CRITICAL',
            problem: `Uploaded signature is ${form.signUpload.sizeKb} KB. Official SSC portal strictly enforces 10 KB to 20 KB.`,
            whyItMatters: 'Server rejects uploads outside the 10-20 KB range.',
            rememberRule: 'Crop and compress signature to ~15 KB on plain white paper.',
            officialClause: 'SSC Gazette Section 7.3'
          });
        } else {
          passedChecks.push(`Uploaded signature (${form.signUpload.sizeKb} KB) meets the mandatory 10-20 KB specification.`);
        }
      }
    } else {
      if (form.signType === 'CAPITAL_LETTERS') {
        mistakes.push({
          id: 'err-sign-capital',
          title: 'Signature in Block / Capital Letters',
          severity: 'CRITICAL',
          problem: 'Signature was entered in full capital/block letters rather than running handwriting.',
          whyItMatters: 'Section 7.3 explicitly notes that signatures in CAPITAL letters will NOT be accepted.',
          rememberRule: 'Sign naturally in running handwriting with blue/black ink on plain white paper.',
          officialClause: 'SSC Gazette Section 7.3'
        });
      } else {
        passedChecks.push('Signature complies with running handwriting and dimension parameters.');
      }
    }

    // Check 4: Date of Birth & Graduation Crucial Date
    if (form.graduationStatus !== 'Passed on or before 01-08-2026') {
      mistakes.push({
        id: 'err-grad-crucial',
        title: 'Crucial Date Qualification Disqualification',
        severity: 'CRITICAL',
        problem: 'Candidate degree completion date falls after the statutory crucial date of 01-08-2026.',
        whyItMatters: 'Section 8.2 states candidates must possess the essential qualification ON or BEFORE 01-08-2026.',
        rememberRule: 'Ensure final degree or provisional certificate issue date is before 01-08-2026.',
        officialClause: 'SSC Gazette Section 8.2'
      });
    } else {
      passedChecks.push('Degree completion satisfies the official 01-08-2026 crucial cut-off timeline.');
    }

    return { mistakes, passedChecks };
  };

  const { mistakes, passedChecks } = evaluateApplication();

  const handleNext = () => {
    if (currentStep < 6) {
      setCurrentStep(prev => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const handleSubmit = () => {
    setIsSubmitted(true);
    storageService.saveMockAttempt({
      id: `app-practice-${Date.now()}`,
      exam_id: 'ssc-cgl-2026',
      subject: 'Application Practice Simulator',
      score: mistakes.length === 0 ? 100 : Math.max(0, 100 - mistakes.length * 25),
      total_marks: 100,
      correct_count: passedChecks.length,
      incorrect_count: mistakes.length,
      unattempted_count: 0,
      time_taken_seconds: 120
    });
  };

  const handleReset = () => {
    setForm(initialFormState);
    setCurrentStep(1);
    setIsSubmitted(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Top Simulator Banner */}
      <div className="glass-card" style={{ padding: '20px', background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className="badge badge-demo" style={{ background: 'rgba(59, 130, 246, 0.2)', color: '#93c5fd', border: '1px solid rgba(59, 130, 246, 0.4)' }}>
                📝 REAL SSC APPLICATION SIMULATOR + FILE VERIFIER
              </span>
              <span style={{ fontSize: '0.8rem', color: '#86efac', fontWeight: 700 }}>
                • Live File Analysis & Diagnostics
              </span>
            </div>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'white', margin: 0 }}>
              Practice Mock Application & Document Verifier
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', margin: '4px 0 0 0' }}>
              Upload your real photo & signature or test preset traps. Platform automatically inspects KB file sizes, aspect ratios, and numerical inputs.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={handleReset} className="btn btn-secondary" style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <RotateCcw size={14} /> Reset Form
            </button>
          </div>
        </div>

        {/* 6-Step Navigation Tabs */}
        {!isSubmitted && (
          <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', marginTop: '16px', paddingBottom: '4px' }}>
            {[
              { num: 1, label: '1. Personal Details' },
              { num: 2, label: '2. Education Details' },
              { num: 3, label: '3. Category & Rules' },
              { num: 4, label: '4. Post Preferences' },
              { num: 5, label: '5. Upload Files & Biometrics' },
              { num: 6, label: '6. Review & Submit' }
            ].map(st => (
              <button
                key={st.num}
                onClick={() => setCurrentStep(st.num)}
                style={{
                  padding: '8px 14px',
                  borderRadius: 'var(--radius-md)',
                  background: currentStep === st.num ? 'var(--primary)' : 'rgba(255, 255, 255, 0.04)',
                  border: currentStep === st.num ? '1px solid #60a5fa' : '1px solid var(--border-color)',
                  color: currentStep === st.num ? 'white' : 'var(--text-secondary)',
                  fontSize: '0.82rem',
                  fontWeight: currentStep === st.num ? 700 : 500,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.15s ease'
                }}
              >
                {st.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* FORM BODY OR POST-SUBMISSION RESULTS */}
      {!isSubmitted ? (
        <div className="glass-card" style={{ padding: '24px', background: 'rgba(15, 23, 42, 0.95)', border: '1px solid var(--border-color)' }}>

          {/* STEP 1: PERSONAL DETAILS */}
          {currentStep === 1 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white', margin: 0 }}>
                  1. Candidate's Personal Details
                </h4>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                  Fields must strictly match your Class 10 (Matriculation) Certificate.
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
                <div>
                  <label style={{ fontSize: '0.82rem', color: '#cbd5e1', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                    Candidate's Full Name *
                  </label>
                  <input
                    type="text"
                    value={form.candidateName}
                    onChange={e => setForm({ ...form, candidateName: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.9rem' }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.82rem', color: '#cbd5e1', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                    Father's Name *
                  </label>
                  <input
                    type="text"
                    value={form.fatherName}
                    onChange={e => setForm({ ...form, fatherName: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.9rem' }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.82rem', color: '#cbd5e1', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                    Date of Birth (DD/MM/YYYY) *
                  </label>
                  <input
                    type="date"
                    value={form.dob}
                    onChange={e => setForm({ ...form, dob: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.9rem' }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.82rem', color: '#cbd5e1', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                    Gender *
                  </label>
                  <select
                    value={form.gender}
                    onChange={e => setForm({ ...form, gender: e.target.value as any })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: '#1e293b', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.9rem' }}
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Transgender">Transgender</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: EDUCATION DETAILS */}
          {currentStep === 2 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white', margin: 0 }}>
                  2. Essential Educational Qualification (Clause 8.1)
                </h4>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                  Must be completed on or before the crucial date (01-08-2026).
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
                <div>
                  <label style={{ fontSize: '0.82rem', color: '#cbd5e1', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                    Highest Educational Qualification *
                  </label>
                  <select
                    value={form.highestQualification}
                    onChange={e => setForm({ ...form, highestQualification: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: '#1e293b', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.9rem' }}
                  >
                    <option value="Bachelor Degree (Graduation)">Bachelor's Degree (Graduation)</option>
                    <option value="Post Graduation (Master's)">Post Graduation (Master's Degree)</option>
                    <option value="Higher Secondary (12th)">Higher Secondary (12th Standard Only)</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.82rem', color: '#cbd5e1', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                    Degree Passing Status (Crucial Date 01-08-2026) *
                  </label>
                  <select
                    value={form.graduationStatus}
                    onChange={e => setForm({ ...form, graduationStatus: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: '#1e293b', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.9rem' }}
                  >
                    <option value="Passed on or before 01-08-2026">Passed on or before 01-08-2026 (Eligible)</option>
                    <option value="Result Awaited after 01-08-2026">Result expected AFTER 01-08-2026 (Disqualified)</option>
                  </select>
                </div>

                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <label style={{ fontSize: '0.82rem', color: '#cbd5e1', fontWeight: 600 }}>
                      Percentage Scored in Mathematics at 12th Standard *
                    </label>
                    {form.mathTwelfthPercentage > 100 && (
                      <span style={{ fontSize: '0.72rem', color: '#f87171', fontWeight: 700 }}>
                        ⚠️ Invalid &gt; 100%
                      </span>
                    )}
                  </div>
                  <input
                    type="number"
                    max="100"
                    min="0"
                    value={form.mathTwelfthPercentage}
                    onChange={e => setForm({ ...form, mathTwelfthPercentage: Number(e.target.value) })}
                    placeholder="e.g. 65"
                    style={{ 
                      width: '100%', 
                      padding: '10px 12px', 
                      borderRadius: 'var(--radius-sm)', 
                      background: form.mathTwelfthPercentage > 100 ? 'rgba(239, 68, 68, 0.15)' : 'rgba(255,255,255,0.05)', 
                      border: form.mathTwelfthPercentage > 100 ? '1px solid #ef4444' : '1px solid var(--border-color)', 
                      color: 'white', 
                      fontSize: '0.9rem' 
                    }}
                  />
                  {form.mathTwelfthPercentage > 100 ? (
                    <span style={{ fontSize: '0.72rem', color: '#fca5a5' }}>
                      ❌ Percentage cannot exceed 100%. Please enter a valid number (e.g. 65).
                    </span>
                  ) : (
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Note: JSO post requires ≥ 60% in 12th Mathematics.</span>
                  )}
                </div>

                <div>
                  <label style={{ fontSize: '0.82rem', color: '#cbd5e1', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                    Did you study Statistics in all 3 years of Graduation?
                  </label>
                  <select
                    value={form.hasStatisticsInDegree ? 'YES' : 'NO'}
                    onChange={e => setForm({ ...form, hasStatisticsInDegree: e.target.value === 'YES' })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: '#1e293b', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.9rem' }}
                  >
                    <option value="NO">No, did not have Statistics as a subject</option>
                    <option value="YES">Yes, had Statistics in Graduation Degree</option>
                  </select>
                </div>
              </div>

              {/* Optional Marksheet File Upload Verification */}
              <div style={{ marginTop: '10px', padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px dashed var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '8px' }}>
                  <span style={{ fontSize: '0.82rem', color: '#93c5fd', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Upload size={14} /> Optional: Test Uploading 12th Marksheet / Degree Certificate
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Supported: PDF, JPG, PNG (Max 500 KB)</span>
                </div>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={e => handleDocFileChange(e, 'marksheet')}
                  style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}
                />
                {form.marksheetUpload && (
                  <div style={{ marginTop: '8px', fontSize: '0.8rem', color: form.marksheetUpload.isSizeValid ? '#86efac' : '#f87171' }}>
                    {form.marksheetUpload.validationMessage}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* STEP 3: CATEGORY & RESERVATION */}
          {currentStep === 3 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white', margin: 0 }}>
                  3. Category & Age Relaxation Rules
                </h4>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                  Category certificates must be valid for the recruitment year.
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
                <div>
                  <label style={{ fontSize: '0.82rem', color: '#cbd5e1', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                    Candidate Category *
                  </label>
                  <select
                    value={form.category}
                    onChange={e => setForm({ ...form, category: e.target.value as any })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: '#1e293b', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.9rem' }}
                  >
                    <option value="UR">UR (Unreserved / General)</option>
                    <option value="OBC_NCL">OBC (Non-Creamy Layer) — Annexure-VI</option>
                    <option value="EWS">EWS (Economically Weaker Section) — Annexure-VII</option>
                    <option value="SC">SC (Scheduled Caste) — Annexure-V</option>
                    <option value="ST">ST (Scheduled Tribe) — Annexure-V</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.82rem', color: '#cbd5e1', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                    Seeking Age Relaxation? *
                  </label>
                  <select
                    value={form.seekingAgeRelaxation ? 'YES' : 'NO'}
                    onChange={e => setForm({ ...form, seekingAgeRelaxation: e.target.value === 'YES' })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: '#1e293b', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.9rem' }}
                  >
                    <option value="NO">No (Age is within standard 18-30/32 limit)</option>
                    <option value="YES">Yes (Claiming OBC +3 yrs / SC-ST +5 yrs / PwBD +10 yrs)</option>
                  </select>
                </div>
              </div>

              {/* Optional Category Certificate Upload */}
              {form.category !== 'UR' && (
                <div style={{ marginTop: '10px', padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px dashed var(--border-color)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '8px' }}>
                    <span style={{ fontSize: '0.82rem', color: '#93c5fd', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Upload size={14} /> Test Uploading {form.category} Certificate Document
                    </span>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Supported: PDF, JPG (Max 500 KB)</span>
                  </div>
                  <input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={e => handleDocFileChange(e, 'certificate')}
                    style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}
                  />
                  {form.certUpload && (
                    <div style={{ marginTop: '8px', fontSize: '0.8rem', color: form.certUpload.isSizeValid ? '#86efac' : '#f87171' }}>
                      {form.certUpload.validationMessage}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* STEP 4: POST PREFERENCES */}
          {currentStep === 4 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white', margin: 0 }}>
                  4. Preference of Posts (Order of Merit Allocation)
                </h4>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                  Give your top choices in order. (Common trap: Choosing JSO without meeting the math criteria).
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
                <div>
                  <label style={{ fontSize: '0.82rem', color: '#93c5fd', fontWeight: 700, display: 'block', marginBottom: '6px' }}>
                    1st Preference (Top Priority) *
                  </label>
                  <select
                    value={form.pref1}
                    onChange={e => setForm({ ...form, pref1: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: '#1e293b', border: '1px solid var(--primary)', color: 'white', fontSize: '0.9rem' }}
                  >
                    {postsList.map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.82rem', color: '#cbd5e1', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                    2nd Preference *
                  </label>
                  <select
                    value={form.pref2}
                    onChange={e => setForm({ ...form, pref2: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: '#1e293b', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.9rem' }}
                  >
                    {postsList.map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.82rem', color: '#cbd5e1', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                    3rd Preference *
                  </label>
                  <select
                    value={form.pref3}
                    onChange={e => setForm({ ...form, pref3: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: '#1e293b', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.9rem' }}
                  >
                    {postsList.map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.82rem', color: '#cbd5e1', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                    4th Preference *
                  </label>
                  <select
                    value={form.pref4}
                    onChange={e => setForm({ ...form, pref4: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: '#1e293b', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.9rem' }}
                  >
                    {postsList.map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* STEP 5: PHOTO & SIGNATURE (REAL FILE UPLOAD + PRESET TRAPS) */}
          {currentStep === 5 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                <div>
                  <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white', margin: 0 }}>
                    5. Upload Photograph & Signature Verification
                  </h4>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    Choose to upload your real files for live byte & dimension analysis, or test simulated mistake presets.
                  </span>
                </div>

                {/* Switcher: Real File Upload vs Preset Traps */}
                <div style={{ display: 'flex', gap: '6px', background: 'rgba(255,255,255,0.06)', padding: '3px', borderRadius: 'var(--radius-sm)' }}>
                  <button
                    onClick={() => setForm({ ...form, uploadMode: 'REAL_UPLOAD' })}
                    className={`btn ${form.uploadMode === 'REAL_UPLOAD' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ fontSize: '0.78rem', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                  >
                    <Upload size={13} /> Upload My Own Files (Live Check)
                  </button>
                  <button
                    onClick={() => setForm({ ...form, uploadMode: 'PRESET_TRAPS' })}
                    className={`btn ${form.uploadMode === 'PRESET_TRAPS' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ fontSize: '0.78rem', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                  >
                    <Sparkles size={13} /> Test Simulated Traps
                  </button>
                </div>
              </div>

              {/* MODE A: REAL FILE UPLOAD WITH LIVE CANVAS INSPECTOR */}
              {form.uploadMode === 'REAL_UPLOAD' ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
                  
                  {/* Photo Real Upload Card */}
                  <div style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#93c5fd', fontWeight: 800, fontSize: '0.95rem' }}>
                        <Camera size={18} /> Candidate Live Photograph *
                      </div>
                      <span className="badge badge-verified" style={{ fontSize: '0.7rem' }}>20 KB – 50 KB</span>
                    </div>

                    <div style={{ padding: '16px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.2)', border: '1px dashed #3b82f6', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                      <input
                        type="file"
                        accept="image/jpeg,image/png,image/jpg"
                        onChange={handlePhotoFileChange}
                        style={{ display: 'none' }}
                        id="real-photo-input"
                      />
                      <label htmlFor="real-photo-input" className="btn btn-primary" style={{ fontSize: '0.82rem', padding: '7px 16px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Upload size={15} /> Select Photo File (.jpg / .png)
                      </label>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Target: ~3.5cm × 4.5cm vertical portrait, white background, no glasses.
                      </span>
                    </div>

                    {form.photoUpload ? (
                      <div style={{ display: 'flex', gap: '14px', alignItems: 'center', background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                        <img 
                          src={form.photoUpload.previewUrl} 
                          alt="Photo Preview" 
                          style={{ width: '70px', height: '90px', objectFit: 'cover', borderRadius: '4px', border: form.photoUpload.isSizeValid && form.photoUpload.isDimensionValid ? '2px solid #10b981' : '2px solid #ef4444' }} 
                        />
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '0.8rem' }}>
                          <div style={{ fontWeight: 700, color: 'white' }}>{form.photoUpload.name}</div>
                          <div style={{ color: form.photoUpload.isSizeValid ? '#86efac' : '#f87171' }}>
                            Size: <strong>{form.photoUpload.sizeKb} KB</strong> {form.photoUpload.isSizeValid ? '✅ (Valid 20-50 KB)' : '❌ (Must be 20-50 KB)'}
                          </div>
                          <div style={{ color: form.photoUpload.isDimensionValid ? '#86efac' : '#fbbf24' }}>
                            Resolution: <strong>{form.photoUpload.width} × {form.photoUpload.height} px</strong>
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                            {form.photoUpload.validationMessage}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                        No photo uploaded yet. (Upload your photo to check real-time compliance).
                      </div>
                    )}
                  </div>

                  {/* Signature Real Upload Card */}
                  <div style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#93c5fd', fontWeight: 800, fontSize: '0.95rem' }}>
                        <PenTool size={18} /> Candidate Signature Image *
                      </div>
                      <span className="badge badge-verified" style={{ fontSize: '0.7rem' }}>10 KB – 20 KB</span>
                    </div>

                    <div style={{ padding: '16px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.2)', border: '1px dashed #3b82f6', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                      <input
                        type="file"
                        accept="image/jpeg,image/png,image/jpg"
                        onChange={handleSignFileChange}
                        style={{ display: 'none' }}
                        id="real-sign-input"
                      />
                      <label htmlFor="real-sign-input" className="btn btn-primary" style={{ fontSize: '0.82rem', padding: '7px 16px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Upload size={15} /> Select Signature File (.jpg / .png)
                      </label>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Target: ~4.0cm × 2.0cm horizontal format in running handwriting.
                      </span>
                    </div>

                    {form.signUpload ? (
                      <div style={{ display: 'flex', gap: '14px', alignItems: 'center', background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                        <img 
                          src={form.signUpload.previewUrl} 
                          alt="Signature Preview" 
                          style={{ width: '100px', height: '50px', objectFit: 'contain', background: 'white', borderRadius: '4px', border: form.signUpload.isSizeValid ? '2px solid #10b981' : '2px solid #ef4444' }} 
                        />
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '0.8rem' }}>
                          <div style={{ fontWeight: 700, color: 'white' }}>{form.signUpload.name}</div>
                          <div style={{ color: form.signUpload.isSizeValid ? '#86efac' : '#f87171' }}>
                            Size: <strong>{form.signUpload.sizeKb} KB</strong> {form.signUpload.isSizeValid ? '✅ (Valid 10-20 KB)' : '❌ (Must be 10-20 KB)'}
                          </div>
                          <div style={{ color: form.signUpload.isDimensionValid ? '#86efac' : '#fbbf24' }}>
                            Dimensions: <strong>{form.signUpload.width} × {form.signUpload.height} px</strong>
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                            {form.signUpload.validationMessage}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                        No signature uploaded yet.
                      </div>
                    )}
                  </div>

                </div>
              ) : (

                /* MODE B: SIMULATED PRESET TRAPS */
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '18px' }}>
                  <div style={{ padding: '16px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#93c5fd', fontWeight: 700, fontSize: '0.9rem' }}>
                      <Camera size={18} /> Simulated Photograph Framing Trap
                    </div>
                    <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                      Select test framing:
                    </label>
                    <select
                      value={form.photoType}
                      onChange={e => setForm({ ...form, photoType: e.target.value as any })}
                      style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: '#1e293b', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.88rem' }}
                    >
                      <option value="CLEAN_WHITE_BG">✅ Clean, front-facing, white background, no glasses (Valid)</option>
                      <option value="WITH_GLASSES">⚠️ Wearing Spectacles / Reading Glasses (Common Trap!)</option>
                      <option value="WITH_CAP">⚠️ Wearing Cap / Hat / Forehead Covered (Trap!)</option>
                      <option value="BLURRY_SELFIE">⚠️ Blurry / Side Angle / Dark Background (Trap!)</option>
                    </select>
                  </div>

                  <div style={{ padding: '16px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#93c5fd', fontWeight: 700, fontSize: '0.9rem' }}>
                      <PenTool size={18} /> Simulated Signature Formatting Trap
                    </div>
                    <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                      Select test signature style:
                    </label>
                    <select
                      value={form.signType}
                      onChange={e => setForm({ ...form, signType: e.target.value as any })}
                      style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: '#1e293b', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.88rem' }}
                    >
                      <option value="VALID_RUNNING_HAND">✅ Running Handwriting on White Paper, 10-20 KB (Valid)</option>
                      <option value="CAPITAL_LETTERS">⚠️ Signature in FULL CAPITAL LETTERS (Common Trap!)</option>
                      <option value="BLURRY_SIGN">⚠️ Low resolution / blurry signature image (Trap!)</option>
                    </select>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 6: APPLICATION PREVIEW */}
          {currentStep === 6 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white', margin: 0 }}>
                  6. Final Application Form Preview
                </h4>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                  Review your responses and file verification results before clicking "Submit Practice Application".
                </span>
              </div>

              <div style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px', fontSize: '0.85rem' }}>
                <div><strong style={{ color: '#93c5fd' }}>Candidate Name:</strong> <div style={{ color: 'white' }}>{form.candidateName}</div></div>
                <div><strong style={{ color: '#93c5fd' }}>Father's Name:</strong> <div style={{ color: 'white' }}>{form.fatherName}</div></div>
                <div><strong style={{ color: '#93c5fd' }}>Date of Birth:</strong> <div style={{ color: 'white' }}>{form.dob}</div></div>
                <div><strong style={{ color: '#93c5fd' }}>Category:</strong> <div style={{ color: 'white' }}>{form.category}</div></div>
                <div><strong style={{ color: '#93c5fd' }}>Highest Qualification:</strong> <div style={{ color: 'white' }}>{form.highestQualification}</div></div>
                <div>
                  <strong style={{ color: '#93c5fd' }}>12th Math %:</strong> 
                  <div style={{ color: form.mathTwelfthPercentage > 100 ? '#f87171' : 'white', fontWeight: form.mathTwelfthPercentage > 100 ? 800 : 400 }}>
                    {form.mathTwelfthPercentage}% {form.mathTwelfthPercentage > 100 && '(⚠️ Invalid > 100%)'}
                  </div>
                </div>
                <div><strong style={{ color: '#93c5fd' }}>1st Post Preference:</strong> <div style={{ color: 'white' }}>{postsList.find(p => p.id === form.pref1)?.name}</div></div>
                
                {form.uploadMode === 'REAL_UPLOAD' ? (
                  <>
                    <div>
                      <strong style={{ color: '#93c5fd' }}>Photo Upload:</strong> 
                      <div style={{ color: form.photoUpload?.isSizeValid ? '#86efac' : '#f87171' }}>
                        {form.photoUpload ? `${form.photoUpload.name} (${form.photoUpload.sizeKb} KB)` : 'Not Uploaded'}
                      </div>
                    </div>
                    <div>
                      <strong style={{ color: '#93c5fd' }}>Signature Upload:</strong> 
                      <div style={{ color: form.signUpload?.isSizeValid ? '#86efac' : '#f87171' }}>
                        {form.signUpload ? `${form.signUpload.name} (${form.signUpload.sizeKb} KB)` : 'Not Uploaded'}
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <div><strong style={{ color: '#93c5fd' }}>Photo Status:</strong> <div style={{ color: form.photoType === 'CLEAN_WHITE_BG' ? '#86efac' : '#f87171' }}>{form.photoType}</div></div>
                    <div><strong style={{ color: '#93c5fd' }}>Signature Status:</strong> <div style={{ color: form.signType === 'VALID_RUNNING_HAND' ? '#86efac' : '#f87171' }}>{form.signType}</div></div>
                  </>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '6px' }}>
                <input
                  type="checkbox"
                  id="dec"
                  checked={form.declarationAgreed}
                  onChange={e => setForm({ ...form, declarationAgreed: e.target.checked })}
                  style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                />
                <label htmlFor="dec" style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                  I hereby declare that all statements made in this practice application are true, complete and correct to the best of my knowledge.
                </label>
              </div>
            </div>
          )}

          {/* Navigation Controls */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '16px', marginTop: '10px' }}>
            <button
              onClick={handlePrev}
              disabled={currentStep === 1}
              className="btn btn-secondary"
              style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <ChevronLeft size={16} /> Back
            </button>

            {currentStep < 6 ? (
              <button
                onClick={handleNext}
                className="btn btn-primary"
                style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                Save & Next <ChevronRight size={16} />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={!form.declarationAgreed}
                className="btn btn-emerald"
                style={{ fontSize: '0.9rem', padding: '8px 24px', display: 'flex', alignItems: 'center', gap: '8px', boxShadow: '0 4px 14px rgba(16, 185, 129, 0.4)' }}
              >
                <CheckCircle2 size={18} /> Submit Practice Application & Check Files
              </button>
            )}
          </div>

        </div>
      ) : (

        /* POST-SUBMISSION ERROR & PITFALL DIAGNOSTIC */
        <div className="glass-card animate-fade-in" style={{ padding: '28px', border: mistakes.length > 0 ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(16, 185, 129, 0.4)', background: 'rgba(15, 23, 42, 0.98)', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <span className="badge" style={{ background: mistakes.length > 0 ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)', color: mistakes.length > 0 ? '#fca5a5' : '#86efac', fontSize: '0.8rem' }}>
                {mistakes.length > 0 ? `🎯 PRACTICE COMPLETE — ${mistakes.length} MISTAKES DETECTED` : '🌟 100% PERFECT APPLICATION & FILES VERIFIED'}
              </span>
              <h3 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'white', margin: '6px 0 0 0' }}>
                Application Diagnostic & Document Verification Report
              </h3>
            </div>

            <button onClick={handleReset} className="btn btn-secondary" style={{ fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <RotateCcw size={14} /> Try Practice Form Again
            </button>
          </div>

          {/* Mistakes Breakdown */}
          {mistakes.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <p style={{ color: '#fca5a5', fontSize: '0.92rem', margin: 0, fontWeight: 600 }}>
                You made {mistakes.length} mistake{mistakes.length > 1 ? 's' : ''} that would cause rejection or disqualification in the actual SSC portal:
              </p>

              {mistakes.map((err, idx) => (
                <div 
                  key={err.id}
                  style={{
                    padding: '18px 20px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(239, 68, 68, 0.05)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f87171', fontWeight: 800, fontSize: '1.05rem' }}>
                      <XCircle size={18} /> 🔴 {idx + 1}. {err.title}
                    </div>
                    <span className="badge badge-verified" style={{ fontSize: '0.72rem' }}>
                      {err.officialClause}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.88rem', color: '#fecaca', lineHeight: 1.5 }}>
                    <strong>Problem:</strong> {err.problem}
                  </div>

                  <div style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                    <strong>Why it matters:</strong> {err.whyItMatters}
                  </div>

                  <div style={{ padding: '8px 12px', borderRadius: 'var(--radius-sm)', background: 'rgba(239, 68, 68, 0.1)', fontSize: '0.82rem', color: '#fed7d7' }}>
                    💡 <strong>Remember:</strong> {err.rememberRule}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.3)', color: '#86efac', fontSize: '0.95rem', lineHeight: 1.6 }}>
              🎉 <strong>Outstanding!</strong> Your practice application meets all statutory gazette parameters with zero discrepancies in educational criteria, post preferences, photograph framing, or signature standards.
            </div>
          )}

          {/* Clean Checks Passed */}
          {passedChecks.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
              <div style={{ fontSize: '0.88rem', fontWeight: 700, color: '#86efac', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={16} /> 🟢 Everything else looks good:
              </div>
              <ul style={{ margin: '4px 0 0 0', paddingLeft: '22px', fontSize: '0.84rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {passedChecks.map((check, cIdx) => (
                  <li key={cIdx}>{check}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Action buttons */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Result logged into local SQLite progress database (govos.db).
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button onClick={handleReset} className="btn btn-primary" style={{ fontSize: '0.85rem' }}>
                <RotateCcw size={15} /> Try Again
              </button>
            </div>
          </div>

        </div>
      )}

    </div>
  );
};
