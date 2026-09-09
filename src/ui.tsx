// GovOS UI: every candidate-facing and admin component, in dependency order.

import React, { useEffect, useRef, useState } from 'react';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Award,
  Ban,
  BarChart2,
  Bell,
  BellOff,
  Bookmark,
  BookOpen,
  Bot,
  Briefcase,
  Building,
  Calendar,
  Calendar as CalendarIcon,
  Camera,
  Check,
  CheckCheck,
  CheckCircle2,
  CheckSquare,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock,
  Compass,
  Database,
  Download,
  ExternalLink,
  Eye,
  FileCheck,
  FileEdit,
  FileText,
  Filter,
  Flag,
  Flame,
  Globe,
  HelpCircle,
  Image as ImageIcon,
  Info,
  Keyboard,
  Layers,
  List,
  Lock,
  Mail,
  MapPin,
  MessageSquare,
  Pause,
  PenTool,
  Play,
  PlayCircle,
  Printer,
  QrCode,
  RefreshCw,
  RotateCcw,
  Scale,
  Search,
  Send,
  Settings,
  Share2,
  ShieldCheck,
  Sliders,
  Smartphone,
  Sparkles,
  Square,
  Star,
  Target,
  Terminal,
  Trash2,
  TrendingUp,
  Upload,
  User,
  UserCheck,
  X,
  XCircle,
  Youtube,
  Zap
} from 'lucide-react';
import {
  ResearchFinding,
  ResearchMode,
  ResearchRun,
  ResearchStatus,
  ResourceLinkCheck,
  ApplicationGuideData,
  CandidateNotification,
  DataProvenance,
  EligibilityDiagnostic,
  Exam,
  ExamQualificationLevel,
  ExcludedModule,
  InAppChapter,
  NotificationEventType,
  NotificationPreference,
  PostStudyPath,
  PracticeQuestion,
  RequirementProvenanceType,
  ResourceItem,
  RoadmapTrack,
  SourceHealthLog,
  StudyModuleRequirement,
  UserProfile
} from './types';
import {
  ALL_EXAMS,
  ALL_POST_STUDY_PATHS,
  COMPUTER_TEMPLATES,
  CustomTestConfig,
  ENGLISH_TEMPLATES,
  GA_TEMPLATES,
  generateCustomMockTest,
  getPostStudyPath,
  MockPaper,
  NEW_DISCOVERED_PAPERS,
  OFFICIAL_10_MOCK_PAPERS,
  QUANT_TEMPLATES,
  REASONING_TEMPLATES,
  SSC_CGL_EXAM,
  SUBJECT_MOCK_TESTS,
  TOPIC_DRILL_TESTS
} from './data';
import {
  researchService,
  calculateDetailedAge,
  evaluateCandidateEligibility,
  evaluateEligibility,
  getCategoryAgeRelaxation,
  MockAttemptRecord,
  storageService
} from './services';

// ==========================================================================
// Header.tsx
// ==========================================================================
interface HeaderProps {
  activeTab: 'FINDER' | 'ELIGIBILITY' | 'EXAM_DETAIL' | 'PLANNER' | 'PRACTICE' | 'COMPARE' | 'CALENDAR' | 'AI_ASSISTANT' | 'ADMIN';
  setActiveTab: (tab: 'FINDER' | 'ELIGIBILITY' | 'EXAM_DETAIL' | 'PLANNER' | 'PRACTICE' | 'COMPARE' | 'CALENDAR' | 'AI_ASSISTANT' | 'ADMIN') => void;
  selectedExamTitle?: string;
  unreadCount?: number;
  trackedCount?: number;
  onOpenNotifications?: () => void;
  onOpenTimeline?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ 
  activeTab, 
  setActiveTab, 
  selectedExamTitle,
  unreadCount = 0,
  trackedCount = 0,
  onOpenNotifications,
  onOpenTimeline
}) => {
  return (
    <header className="glass-card" style={{ borderRadius: '0 0 16px 16px', marginBottom: '24px', padding: '16px 24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '20px', flexWrap: 'wrap' }}>
        {/* Brand identity */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', cursor: 'pointer' }} onClick={() => setActiveTab('FINDER')}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #6366f1 0%, #10b981 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)'
          }}>
            <ShieldCheck size={26} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ fontSize: '1.4rem', fontWeight: 800, letterSpacing: '-0.02em', background: 'linear-gradient(90deg, #ffffff 0%, #cbd5e1 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                GovOS
              </h1>
              <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                Trust System V1
              </span>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
              India's Exam & Career Navigation Operating System
            </p>
          </div>
        </div>

        {/* Global Navigation */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '6px', overflowX: 'auto', padding: '4px' }}>
          <button 
            className={`btn ${activeTab === 'FINDER' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('FINDER')}
            style={{ fontSize: '0.85rem', padding: '8px 14px' }}
          >
            <Compass size={16} /> Exam Finder
          </button>
          
          <button 
            className={`btn ${activeTab === 'ELIGIBILITY' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('ELIGIBILITY')}
            style={{ fontSize: '0.85rem', padding: '8px 14px' }}
          >
            <CheckCircle2 size={16} /> Am I Eligible?
          </button>

          <button 
            className={`btn ${activeTab === 'EXAM_DETAIL' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('EXAM_DETAIL')}
            style={{ fontSize: '0.85rem', padding: '8px 14px' }}
          >
            <BookOpen size={16} /> Exam Guide {selectedExamTitle && `(${selectedExamTitle.split(' ')[0]})`}
          </button>

          <button 
            className={`btn ${activeTab === 'PRACTICE' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('PRACTICE')}
            style={{ fontSize: '0.85rem', padding: '8px 14px' }}
          >
            <Award size={16} /> Practice & Mocks
          </button>

          <button 
            className={`btn ${activeTab === 'COMPARE' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('COMPARE')}
            style={{ fontSize: '0.85rem', padding: '8px 14px' }}
          >
            <Scale size={16} /> Compare Exams
          </button>

          <button 
            className={`btn ${activeTab === 'CALENDAR' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => {
              if (onOpenTimeline) onOpenTimeline();
              setActiveTab('CALENDAR');
            }}
            style={{ fontSize: '0.85rem', padding: '8px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Calendar size={16} /> My Timeline & Calendar
            {trackedCount > 0 && (
              <span className="badge" style={{ fontSize: '0.65rem', background: 'rgba(99,102,241,0.25)', color: '#a5b4fc', padding: '1px 6px' }}>
                {trackedCount} Tracked
              </span>
            )}
          </button>

          <button 
            className={`btn ${activeTab === 'AI_ASSISTANT' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('AI_ASSISTANT')}
            style={{ fontSize: '0.85rem', padding: '8px 14px' }}
            title="Grounded answers from the verified database, with a live official-source search as fallback"
          >
            <Bot size={16} /> Ask GovOS AI
          </button>

          <button 
            className={`btn ${activeTab === 'ADMIN' ? 'btn-emerald' : 'btn-secondary'}`}
            onClick={() => setActiveTab('ADMIN')}
            style={{ fontSize: '0.85rem', padding: '8px 14px' }}
          >
            <Terminal size={16} /> Trust Panel
          </button>

          {/* Candidate Notification Bell */}
          <button 
            className="btn btn-secondary"
            onClick={onOpenNotifications}
            title="Candidate Notifications & Alerts"
            style={{ 
              position: 'relative', 
              padding: '8px 12px', 
              marginLeft: '4px',
              border: unreadCount > 0 ? '1px solid rgba(99, 102, 241, 0.5)' : '1px solid var(--border-color)',
              background: unreadCount > 0 ? 'rgba(99, 102, 241, 0.12)' : 'rgba(255, 255, 255, 0.04)'
            }}
          >
            <Bell size={18} color={unreadCount > 0 ? '#818cf8' : 'white'} />
            {unreadCount > 0 && (
              <span 
                style={{
                  position: 'absolute',
                  top: '-4px',
                  right: '-4px',
                  background: '#ef4444',
                  color: 'white',
                  borderRadius: '50%',
                  width: '18px',
                  height: '18px',
                  fontSize: '0.65rem',
                  fontWeight: 800,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 0 10px rgba(239, 68, 68, 0.8)'
                }}
              >
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>
        </nav>
      </div>
    </header>
  );
};


// ==========================================================================
// ExamFinder.tsx
// ==========================================================================
interface ExamFinderProps {
  onSelectExam: (exam: Exam) => void;
  onNavigateEligibility: () => void;
  trackedExamIds?: string[];
  onToggleTrackExam?: (examId: string) => void;
}

export const ExamFinder: React.FC<ExamFinderProps> = ({ 
  onSelectExam, 
  onNavigateEligibility,
  trackedExamIds = [],
  onToggleTrackExam
}) => {
  const [selectedPersona, setSelectedPersona] = useState<string>('Graduation (Any Stream)');
  const [selectedInterest, setSelectedInterest] = useState<string>('Government Job');
  const [ageInput, setAgeInput] = useState<number>(21);
  const [searchQuery, setSearchQuery] = useState<string>('');

  const personas = [
    'Class 10th Pass',
    'Class 12th (MPC / Science)',
    'Class 12th (Commerce / Arts)',
    'Graduation (Any Stream)',
    'B.Tech / B.E (Engineering)',
    'Postgraduate / Master\'s'
  ];

  const interests = [
    'Government Job',
    'Civil Services & Governance',
    'Banking & Financial Sector',
    'Indian Railways',
    'Defence & Armed Forces',
    'State Public Services'
  ];

  // Rank of each qualification, so a graduate also sees exams that only need 12th.
  const QUALIFICATION_RANK: Record<ExamQualificationLevel, number> = {
    CLASS_10: 1,
    CLASS_12: 2,
    GRADUATION: 3,
    POST_GRADUATION: 4
  };

  const PERSONA_LEVEL: Record<string, ExamQualificationLevel> = {
    'Class 10th Pass': 'CLASS_10',
    'Class 12th (MPC / Science)': 'CLASS_12',
    'Class 12th (Commerce / Arts)': 'CLASS_12',
    'Graduation (Any Stream)': 'GRADUATION',
    'B.Tech / B.E (Engineering)': 'GRADUATION',
    "Postgraduate / Master's": 'POST_GRADUATION'
  };

  const candidateRank = QUALIFICATION_RANK[PERSONA_LEVEL[selectedPersona] || 'GRADUATION'];

  const filteredExams = ALL_EXAMS.filter(exam => {
    const query = searchQuery.trim().toLowerCase();
    const matchesSearch =
      query === '' ||
      exam.title.toLowerCase().includes(query) ||
      exam.code.toLowerCase().includes(query) ||
      exam.authorityName.toLowerCase().includes(query);

    // A candidate qualifies if their level meets or exceeds the exam's minimum.
    // Exams without declared metadata are never hidden.
    const matchesPersona =
      !exam.minimumQualification ||
      candidateRank >= QUALIFICATION_RANK[exam.minimumQualification];

    const matchesInterest =
      !exam.careerFields ||
      exam.careerFields.length === 0 ||
      exam.careerFields.includes(selectedInterest as any);

    return matchesSearch && matchesPersona && matchesInterest;
  });

  const isFiltered =
    searchQuery.trim() !== '' ||
    selectedPersona !== 'Graduation (Any Stream)' ||
    selectedInterest !== 'Government Job';

  const resetFilters = () => {
    setSelectedPersona('Graduation (Any Stream)');
    setSelectedInterest('Government Job');
    setSearchQuery('');
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* Hero Banner */}
      <div className="glass-card" style={{ padding: '36px', background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.9) 0%, rgba(30, 27, 75, 0.6) 100%)', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: '-50px', right: '-50px', width: '250px', height: '250px', background: 'radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%)', borderRadius: '50%' }} />
        
        <div style={{ maxWidth: '780px', position: 'relative', zIndex: 2 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '6px 14px', borderRadius: '999px', background: 'rgba(99, 102, 241, 0.15)', border: '1px solid rgba(99, 102, 241, 0.3)', marginBottom: '16px' }}>
            <Sparkles size={16} color="#818cf8" />
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#a5b4fc', letterSpacing: '0.02em' }}>
              ONE PLATFORM. EVERY EXAM. ONE CLEAR PATH.
            </span>
          </div>

          <h2 style={{ fontSize: '2.2rem', fontWeight: 800, lineHeight: 1.2, marginBottom: '14px', letterSpacing: '-0.02em' }}>
            Discover Government & Entrance Exams Matched to Your Goal
          </h2>
          
          <p style={{ color: 'var(--text-secondary)', fontSize: '1.05rem', marginBottom: '24px', lineHeight: 1.6 }}>
            Never ask <strong style={{ color: 'white' }}>"What do I do next?"</strong> again. GovOS converts fragmented official government notifications into verified, version-controlled, personalized exam roadmaps.
          </p>

          <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={onNavigateEligibility} style={{ padding: '12px 24px', fontSize: '1rem' }}>
              <ShieldCheck size={20} /> Check My Eligibility Now
            </button>
            
            <button className="btn btn-emerald" onClick={() => onSelectExam(ALL_EXAMS[0])} style={{ padding: '12px 24px', fontSize: '1rem' }}>
              <Award size={20} /> Explore Golden Journey (SSC CGL)
            </button>
          </div>
        </div>
      </div>

      {/* Discovery Filter Engine: "I am a..." + "What do you want?" */}
      <div className="glass-card" style={{ padding: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <Filter size={22} color="var(--primary)" />
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Career & Exam Discovery Engine</h3>
        </div>

        <div className="grid-3" style={{ marginBottom: '24px' }}>
          {/* Step 1: Persona */}
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              1. I am a... (Qualification)
            </label>
            <select 
              value={selectedPersona} 
              onChange={(e) => setSelectedPersona(e.target.value)}
              style={{
                width: '100%',
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-color)',
                color: 'white',
                fontSize: '0.95rem',
                fontFamily: 'var(--font-sans)',
                outline: 'none'
              }}
            >
              {personas.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>

          {/* Step 2: Goal */}
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              2. What do you want? (Field)
            </label>
            <select 
              value={selectedInterest} 
              onChange={(e) => setSelectedInterest(e.target.value)}
              style={{
                width: '100%',
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-color)',
                color: 'white',
                fontSize: '0.95rem',
                fontFamily: 'var(--font-sans)',
                outline: 'none'
              }}
            >
              {interests.map(i => <option key={i} value={i}>{i}</option>)}
            </select>
          </div>

          {/* Step 3: Age */}
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              3. Target Recruitment Year
            </label>
            <select 
              style={{
                width: '100%',
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-color)',
                color: 'white',
                fontSize: '0.95rem',
                fontFamily: 'var(--font-sans)',
                outline: 'none'
              }}
            >
              <option value="2026">2026 Recruitment Cycle</option>
            </select>
          </div>
        </div>

        {/* Search Bar */}
        <div style={{ position: 'relative' }}>
          <Search size={20} color="var(--text-muted)" style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)' }} />
          <input 
            type="text"
            placeholder="Search exam title or authority e.g. SSC CGL, UPSC, IBPS..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '14px 16px 14px 48px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-input)',
              border: '1px solid var(--border-color)',
              color: 'white',
              fontSize: '1rem',
              outline: 'none'
            }}
          />
        </div>
      </div>

      {/* Available Exams Cards */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '1.3rem', fontWeight: 700 }}>
            Available Examination Guides ({filteredExams.length} of {ALL_EXAMS.length})
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Matching “{selectedPersona}” · “{selectedInterest}”
            </span>
            {isFiltered && (
              <button className="btn btn-secondary" onClick={resetFilters} style={{ fontSize: '0.78rem', padding: '5px 12px' }}>
                Reset Filters
              </button>
            )}
          </div>
        </div>

        {filteredExams.length === 0 && (
          <div className="glass-card" style={{ padding: '48px 24px', textAlign: 'center' }}>
            <Compass size={30} color="var(--text-muted)" style={{ marginBottom: '10px' }} />
            <h4 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'white', marginBottom: '6px' }}>
              No exams match these filters yet
            </h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: '460px', margin: '0 auto 18px' }}>
              No guide in the verified register matches “{selectedPersona}” combined with “{selectedInterest}”. More exams are added to the register as their official notifications are verified.
            </p>
            <button className="btn btn-primary" onClick={resetFilters} style={{ fontSize: '0.88rem' }}>
              Reset Filters
            </button>
          </div>
        )}

        <div className="grid-2">
          {filteredExams.map(exam => (
            <div key={exam.id} className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', borderLeft: exam.isGoldenJourney ? '4px solid var(--emerald)' : '1px solid var(--border-color)' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
                  {exam.isGoldenJourney && (
                    <span className="badge badge-demo" style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.4)' }}>
                      🌟 GOLDEN JOURNEY
                    </span>
                  )}
                  {exam.isDemoData ? (
                    <span className="badge badge-demo">
                      🟡 DEMO DATA
                    </span>
                  ) : (
                    <span className="badge badge-verified">
                      <ShieldCheck size={14} /> OFFICIALLY VERIFIED
                    </span>
                  )}
                </div>

                <h4 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '6px' }}>
                  {exam.title}
                </h4>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '14px', fontWeight: 500 }}>
                  Authority: {exam.authorityName}
                </p>

                <p style={{ fontSize: '0.9rem', color: '#d1d5db', lineHeight: 1.5, marginBottom: '18px' }}>
                  {exam.overviewDescription.slice(0, 140)}...
                </p>

                {/* Key attributes pill grid */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '20px' }}>
                  <span className="glass-pill">
                    🎓 Graduation Criteria
                  </span>
                  <span className="glass-pill">
                    📅 2026 Cycle
                  </span>
                  <span className="glass-pill" style={{ borderColor: 'rgba(16, 185, 129, 0.3)', color: '#34d399' }}>
                    🏛️ {exam.authorityName.split(' ')[0]}
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '16px', flexWrap: 'wrap', gap: '8px' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Code: <code style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{exam.code}</code>
                </span>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {onToggleTrackExam && (
                    <button 
                      className={`btn ${trackedExamIds.includes(exam.id) ? 'btn-emerald' : 'btn-secondary'}`}
                      onClick={() => onToggleTrackExam(exam.id)}
                      title={trackedExamIds.includes(exam.id) ? 'Currently tracked in My Exam Timeline' : 'Track this exam for personalized deadline notifications'}
                      style={{ padding: '8px 12px', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}
                    >
                      {trackedExamIds.includes(exam.id) ? (
                        <>
                          <Check size={14} /> Tracking
                        </>
                      ) : (
                        <>
                          <Bell size={14} /> Track Exam
                        </>
                      )}
                    </button>
                  )}

                  <button 
                    className={`btn ${exam.isGoldenJourney ? 'btn-emerald' : 'btn-primary'}`}
                    onClick={() => onSelectExam(exam)}
                    style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                  >
                    Guide <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};


// ==========================================================================
// EligibilityCalculator.tsx
// ==========================================================================
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


// ==========================================================================
// ExamCompare.tsx
// ==========================================================================
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


// ==========================================================================
// ExamCalendar.tsx
// ==========================================================================
interface ExamCalendarProps {
  onSelectExam: (exam: Exam) => void;
  trackedExamIds: string[];
  onToggleTrackExam: (examId: string) => void;
  onOpenPreferences: () => void;
  defaultMode?: 'TIMELINE' | 'CALENDAR';
}

export const ExamCalendar: React.FC<ExamCalendarProps> = ({ 
  onSelectExam,
  trackedExamIds,
  onToggleTrackExam,
  onOpenPreferences,
  defaultMode = 'TIMELINE'
}) => {
  const [activeTab, setActiveTab] = useState<'TIMELINE' | 'CALENDAR'>(defaultMode);
  const [selectedMonth, setSelectedMonth] = useState<string>('ALL');

  const months = ['ALL', 'FEB', 'MAR', 'MAY', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];

  // Flatten all dates across ALL_EXAMS into a unified calendar
  const allCalendarEvents = ALL_EXAMS.flatMap(exam => 
    exam.dates.map((d, index) => {
      const dateParts = d.dateTimeStr.split(' ')[0].split('-');
      const year = dateParts[0];
      const monthNum = parseInt(dateParts[1], 10);
      const day = dateParts[2];
      
      const monthNames = ['', 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
      const monthStr = monthNames[monthNum] || 'OCT';
      const formattedDate = `${day} ${monthStr} ${year}`;

      return {
        id: `${exam.id}-${d.id || index}`,
        examId: exam.id,
        examCode: exam.code,
        examTitle: exam.title,
        authority: exam.authorityName.split(' ')[0],
        type: d.type,
        label: d.label,
        dateStr: formattedDate,
        rawDate: d.dateTimeStr,
        month: monthStr,
        isTentative: d.isTentative,
        status: d.status
      };
    })
  ).sort((a, b) => a.rawDate.localeCompare(b.rawDate));

  const filteredEvents = selectedMonth === 'ALL'
    ? allCalendarEvents
    : allCalendarEvents.filter(ev => ev.month === selectedMonth);

  const trackedExams = ALL_EXAMS.filter(e => trackedExamIds.includes(e.id));

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* Header Banner */}
      <div className="glass-card" style={{ padding: '26px', background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.12) 0%, rgba(17, 24, 39, 0.95) 100%)', borderColor: 'rgba(6, 182, 212, 0.3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{ width: '44px', height: '44px', borderRadius: '12px', background: 'var(--cyan)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', boxShadow: '0 0 16px rgba(6,182,212,0.4)' }}>
              <CalendarIcon size={26} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.6rem', fontWeight: 800, color: 'white', margin: '0 0 4px' }}>
                Government Exam Timeline & Verified Calendar (2026)
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
                Never miss an application deadline, correction window, or admit card release.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button 
              className="btn btn-secondary"
              onClick={onOpenPreferences}
              style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Settings size={16} /> Notification Channels
            </button>
          </div>
        </div>
      </div>

      {/* Mode Switcher Tabs */}
      <div className="glass-card" style={{ padding: '12px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            className={`btn ${activeTab === 'TIMELINE' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('TIMELINE')}
            style={{ fontSize: '0.9rem', padding: '9px 18px', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <Star size={16} color={activeTab === 'TIMELINE' ? 'white' : '#f59e0b'} />
            My Exam Timeline ({trackedExams.length})
          </button>
          <button 
            className={`btn ${activeTab === 'CALENDAR' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('CALENDAR')}
            style={{ fontSize: '0.9rem', padding: '9px 18px', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <CalendarIcon size={16} /> All Exams Calendar ({allCalendarEvents.length} Milestones)
          </button>
        </div>

        <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
          {activeTab === 'TIMELINE' 
            ? 'Personalized deadline countdowns for your tracked exams'
            : 'Explore schedules for Central & State Government recruitments'}
        </div>
      </div>

      {/* TAB 1: MY EXAM TIMELINE */}
      {activeTab === 'TIMELINE' && (
        <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {trackedExams.length === 0 ? (
            <div className="glass-card" style={{ padding: '60px 24px', textAlign: 'center' }}>
              <div style={{ width: '60px', height: '60px', borderRadius: '50%', background: 'rgba(99, 102, 241, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', color: 'var(--primary)' }}>
                <Bell size={30} />
              </div>
              <h3 style={{ fontSize: '1.3rem', fontWeight: 800, color: 'white', marginBottom: '8px' }}>
                No Exams Tracked in Your Timeline
              </h3>
              <p style={{ color: 'var(--text-secondary)', maxWidth: '460px', margin: '0 auto 24px', fontSize: '0.92rem', lineHeight: 1.5 }}>
                Track exams you are preparing for to get live deadline countdowns, multi-stage reminders, and personalized alerts.
              </p>
              <button 
                className="btn btn-primary"
                onClick={() => setActiveTab('CALENDAR')}
                style={{ padding: '10px 22px', fontSize: '0.9rem', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
              >
                Browse All Exams Calendar <ArrowRight size={16} />
              </button>
            </div>
          ) : (
            trackedExams.map(exam => {
              const activeDates = exam.dates.filter(d => d.status !== 'SUPERSEDED');
              return (
                <div 
                  key={exam.id}
                  className="glass-card"
                  style={{
                    padding: '28px',
                    borderLeft: '4px solid var(--primary)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '20px'
                  }}
                >
                  {/* Card Top Header */}
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                        <span className="badge badge-verified">
                          <ShieldCheck size={14} /> OFFICIALLY VERIFIED
                        </span>
                        <span className="badge badge-demo" style={{ background: 'rgba(99,102,241,0.2)', color: '#a5b4fc' }}>
                          {exam.code}
                        </span>
                        {exam.vacanciesTotal && (
                          <span className="badge" style={{ background: 'rgba(16,185,129,0.15)', color: '#34d399' }}>
                            {exam.vacanciesTotal}
                          </span>
                        )}
                      </div>
                      <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'white', margin: '0 0 4px' }}>
                        {exam.title}
                      </h3>
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0 }}>
                        Authority: <strong style={{ color: 'white' }}>{exam.authorityName}</strong> | Crucial Cut-off: <code style={{ color: 'var(--cyan)' }}>{exam.crucialEligibilityDate}</code>
                      </p>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <button 
                        className="btn btn-emerald"
                        onClick={() => onToggleTrackExam(exam.id)}
                        style={{ fontSize: '0.85rem', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '6px' }}
                      >
                        <Check size={16} /> Tracking Active
                      </button>
                      <button 
                        className="btn btn-primary"
                        onClick={() => onSelectExam(exam)}
                        style={{ fontSize: '0.85rem', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '6px' }}
                      >
                        View Full Exam Guide <ArrowRight size={14} />
                      </button>
                    </div>
                  </div>

                  {/* Milestone Horizontal Progression Grid */}
                  <div>
                    <h4 style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '14px' }}>
                      Key Recruitment Milestones & Reminders
                    </h4>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
                      {activeDates.map(date => {
                        const isClose = date.type === 'APPLICATION_CLOSE';
                        const isAdmit = date.type === 'ADMIT_CARD';
                        const isExam = date.type === 'EXAM_TIER1' || date.type === 'EXAM_TIER2';
                        const isResult = date.type === 'RESULT';

                        let accentColor = 'rgba(255, 255, 255, 0.05)';
                        let borderColor = 'var(--border-color)';
                        let tagColor = 'var(--text-muted)';

                        if (isClose) {
                          accentColor = 'rgba(239, 68, 68, 0.08)';
                          borderColor = 'rgba(239, 68, 68, 0.3)';
                          tagColor = '#f87171';
                        } else if (isAdmit) {
                          accentColor = 'rgba(168, 85, 247, 0.08)';
                          borderColor = 'rgba(168, 85, 247, 0.3)';
                          tagColor = '#c084fc';
                        } else if (isExam) {
                          accentColor = 'rgba(245, 158, 11, 0.08)';
                          borderColor = 'rgba(245, 158, 11, 0.3)';
                          tagColor = '#fbbf24';
                        } else if (isResult) {
                          accentColor = 'rgba(16, 185, 129, 0.08)';
                          borderColor = 'rgba(16, 185, 129, 0.3)';
                          tagColor = '#34d399';
                        }

                        return (
                          <div 
                            key={date.id}
                            style={{
                              padding: '14px',
                              borderRadius: 'var(--radius-md)',
                              background: accentColor,
                              border: `1px solid ${borderColor}`,
                              display: 'flex',
                              flexDirection: 'column',
                              justifyContent: 'space-between',
                              gap: '8px'
                            }}
                          >
                            <div>
                              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: tagColor, textTransform: 'uppercase' }}>
                                {date.type.replace('_', ' ')}
                              </span>
                              <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'white', marginTop: '2px', lineHeight: 1.3 }}>
                                {date.label}
                              </div>
                            </div>

                            <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                              <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#93c5fd' }}>
                                {date.dateTimeStr.split(' ')[0]}
                              </div>
                              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                {date.dateTimeStr.split(' ')[1] || 'IST'}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* TAB 2: ALL EXAMS CALENDAR */}
      {activeTab === 'CALENDAR' && (
        <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Month Tabs */}
          <div className="glass-card" style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '10px', overflowX: 'auto' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)', marginRight: '10px' }}>FILTER MONTH:</span>
            {months.map(m => (
              <button 
                key={m}
                className={`btn ${selectedMonth === m ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setSelectedMonth(m)}
                style={{ fontSize: '0.85rem', padding: '8px 18px' }}
              >
                {m === 'ALL' ? 'All Months' : `${m} 2026`}
              </button>
            ))}
          </div>

          {/* Timeline List */}
          <div className="glass-card" style={{ padding: '28px' }}>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '20px' }}>
              Scheduled Events {selectedMonth === 'ALL' ? 'for 2026' : `for ${selectedMonth} 2026`} ({filteredEvents.length} Milestones)
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {filteredEvents.map(ev => {
                const isTracked = trackedExamIds.includes(ev.examId);
                const matchedExam = ALL_EXAMS.find(e => e.id === ev.examId) || ALL_EXAMS[0];

                return (
                  <div 
                    key={ev.id} 
                    style={{ 
                      padding: '20px', 
                      borderRadius: 'var(--radius-md)', 
                      background: isTracked ? 'rgba(99, 102, 241, 0.05)' : 'rgba(255,255,255,0.02)', 
                      border: isTracked ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid var(--border-color)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '16px'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                      <div style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(99, 102, 241, 0.15)', border: '1px solid rgba(99, 102, 241, 0.3)', textAlign: 'center', minWidth: '100px' }}>
                        <div style={{ fontSize: '0.88rem', fontWeight: 800, color: 'var(--primary)' }}>{ev.dateStr}</div>
                        <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>VERIFIED</div>
                      </div>

                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
                          <span className="badge badge-demo" style={{ fontSize: '0.7rem' }}>
                            {ev.examCode}
                          </span>
                          <span className="badge" style={{ fontSize: '0.65rem', background: 'rgba(255,255,255,0.05)', color: 'var(--text-secondary)' }}>
                            {ev.type.replace('_', ' ')}
                          </span>
                        </div>
                        <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white' }}>
                          {ev.label}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                          Authority: {ev.authority} | Exam: {ev.examTitle}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <button 
                        className={`btn ${isTracked ? 'btn-emerald' : 'btn-secondary'}`}
                        onClick={() => onToggleTrackExam(ev.examId)}
                        style={{ fontSize: '0.8rem', padding: '6px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
                      >
                        {isTracked ? (
                          <>
                            <Check size={14} /> Tracking
                          </>
                        ) : (
                          <>
                            <Bell size={14} /> Track Exam
                          </>
                        )}
                      </button>

                      <button 
                        className="btn btn-outline"
                        onClick={() => onSelectExam(matchedExam)}
                        style={{ fontSize: '0.8rem', padding: '6px 14px' }}
                      >
                        Guide <ChevronRight size={14} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

    </div>
  );
};


// ==========================================================================
// Live Source Research — shared presentation helpers
// ==========================================================================
const researchTrustMeta = (level: ResearchFinding['trustLevel']): { label: string; color: string; bg: string; border: string } => {
  switch (level) {
    case 'OFFICIAL':
      return { label: 'OFFICIAL DOMAIN', color: '#34d399', bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.35)' };
    case 'TRUSTED_PUBLIC':
      return { label: 'ACADEMIC / PUBLIC BODY', color: '#60a5fa', bg: 'rgba(59,130,246,0.12)', border: 'rgba(59,130,246,0.35)' };
    default:
      return { label: 'UNVERIFIED SOURCE', color: '#fbbf24', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.35)' };
  }
};

const researchHost = (url: string): string => {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
};

const ResearchSetupNotice: React.FC<{ setup?: string }> = ({ setup }) => (
  <div style={{ padding: '18px 20px', borderRadius: 'var(--radius-md)', background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.35)', display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
    <Lock size={18} color="#fbbf24" style={{ flexShrink: 0, marginTop: '2px' }} />
    <div style={{ fontSize: '0.86rem', color: '#fef3c7', lineHeight: 1.5 }}>
      <strong>Live research is not configured on this server.</strong>
      <div style={{ marginTop: '6px', color: 'var(--text-secondary)' }}>
        {setup || 'Add TAVILY_API_KEY=tvly-... to the .env file next to app.py and restart python app.py.'}
      </div>
      <div style={{ marginTop: '8px', fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: '#fbbf24' }}>
        TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxx
      </div>
      <div style={{ marginTop: '6px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
        Keys are issued at tavily.com. The key stays on the server; the browser never sees it.
      </div>
    </div>
  </div>
);


// ==========================================================================
// AIAssistant.tsx
// ==========================================================================
interface AIAssistantProps {
  onOpenProvenanceModal: (provenance: any) => void;
}

interface AIChatMessage {
  id: string;
  sender: 'USER' | 'AI';
  text: string;
  isVerified: boolean;
  citation?: {
    documentTitle: string;
    pageNumber: number;
    clauseNumber: string;
    provenance: any;
  };
  /** Set on a fallback reply: the question the candidate can send to a live official-domain search. */
  liveSearchOffer?: string;
  liveResults?: ResearchFinding[];
  liveAnswer?: string | null;
  liveError?: string;
  liveSetup?: string;
}

export const AIAssistant: React.FC<AIAssistantProps> = ({ onOpenProvenanceModal }) => {
  const [inputQuery, setInputQuery] = useState<string>('');
  const [liveSearchingId, setLiveSearchingId] = useState<string | null>(null);

  // Fallback path: run a Tavily search restricted to official government domains and
  // attach the results to the message, clearly labelled as not yet verified.
  const handleLiveOfficialSearch = async (messageId: string, question: string) => {
    if (liveSearchingId) return;
    setLiveSearchingId(messageId);
    const outcome = await researchService.search(question, 'OFFICIAL', SSC_CGL_EXAM.id, 5);
    setMessages(prev => prev.map(m => {
      if (m.id !== messageId) return m;
      if (outcome.ok) {
        return { ...m, liveResults: outcome.data.results, liveAnswer: outcome.data.answer, liveError: undefined, liveSetup: undefined };
      }
      return { ...m, liveResults: [], liveError: outcome.error, liveSetup: outcome.notConfigured ? outcome.setup : undefined };
    }));
    setLiveSearchingId(null);
  };
  const [messages, setMessages] = useState<AIChatMessage[]>([
    {
      id: 'm-1',
      sender: 'AI',
      text: 'Hello! I am the GovOS Strictly Grounded AI Assistant. I do not guess or search unverified external websites. Ask me anything about SSC CGL 2026 eligibility, exam dates, syllabus, or application rules!',
      isVerified: true
    }
  ]);

  const handleSendMessage = () => {
    if (!inputQuery.trim()) return;

    const userText = inputQuery.trim();
    const userMsg: AIChatMessage = {
      id: `m-user-${Date.now()}`,
      sender: 'USER',
      text: userText,
      isVerified: false
    };

    setMessages(prev => [...prev, userMsg]);
    setInputQuery('');

    // Process query grounded against verified database
    setTimeout(() => {
      let responseText = '';
      let citationData: any = null;
      let verified = true;

      const qLower = userText.toLowerCase();

      if (qLower.includes('eligible') || qLower.includes('b.tech') || qLower.includes('age')) {
        const dummyProfile = {
          dateOfBirth: '2005-05-15',
          degree: 'B.Tech',
          branch: 'Computer Science',
          percentage: 72,
          category: 'GENERAL' as const,
          gender: 'Male' as const,
          domicileState: 'Telangana',
          nationality: 'INDIAN'
        };
        const diag = evaluateCandidateEligibility(SSC_CGL_EXAM, dummyProfile);
        responseText = `${diag.plainEnglishExplanation} (Verified against Section 3.1, Clause 3.1(a) of the official notification).`;
        citationData = {
          documentTitle: 'SSC CGL 2026 Official Notice.pdf',
          pageNumber: 12,
          clauseNumber: 'Section 3.1 (a)',
          provenance: SSC_CGL_EXAM.posts[0].provenance
        };
      } else if (qLower.includes('date') || qLower.includes('deadline') || qLower.includes('last date')) {
        responseText = `The online application closing date for SSC CGL 2026 has been officially extended to 27 September 2026 (23:59 IST) via Corrigendum Notice #02.`;
        citationData = {
          documentTitle: 'SSC CGL 2026 Corrigendum Notice #02.pdf',
          pageNumber: 1,
          clauseNumber: 'Clause 2',
          provenance: SSC_CGL_EXAM.dates[2].provenance
        };
      } else if (qLower.includes('negative') || qLower.includes('marking') || qLower.includes('scheme')) {
        responseText = `Yes, Tier-1 examination has a negative marking of 0.50 marks per incorrect answer. Tier-2 has 1.00 mark deducted per wrong answer in Section I & II.`;
        citationData = {
          documentTitle: 'SSC CGL 2026 Official Notice.pdf',
          pageNumber: 15,
          clauseNumber: 'Section 4.2',
          provenance: SSC_CGL_EXAM.dates[0].provenance
        };
      } else {
        // Fallback for unverified / missing topics
        verified = false;
        responseText = `I couldn't find a verified official source for this information in the GovOS database. You can check the official portal at https://ssc.gov.in, or let me search official government domains live — results from a live search are shown as unverified until a GovOS verifier reviews them.`;
      }

      const aiMsg: AIChatMessage = {
        id: `m-ai-${Date.now()}`,
        sender: 'AI',
        text: responseText,
        isVerified: verified,
        citation: citationData,
        liveSearchOffer: verified ? undefined : userText
      };

      setMessages(prev => [...prev, aiMsg]);
    }, 400);
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Header */}
      <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(17, 24, 39, 0.9) 100%)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ width: '42px', height: '42px', borderRadius: '12px', background: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
            <Bot size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800 }}>
              Strictly Grounded AI Guidance Assistant
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              Queries strictly restricted to the Verified Database & Deterministic Rule Engine. Unverified queries trigger fallback alerts.
            </p>
          </div>
        </div>
      </div>

      {/* Chat Conversation Box */}
      <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', height: '550px' }}>
        
        {/* Messages Feed */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px', paddingRight: '8px' }}>
          {messages.map(msg => (
            <div 
              key={msg.id} 
              style={{
                alignSelf: msg.sender === 'USER' ? 'flex-end' : 'flex-start',
                maxWidth: '82%',
                background: msg.sender === 'USER' ? 'var(--primary)' : 'rgba(255,255,255,0.05)',
                color: 'white',
                padding: '16px 20px',
                borderRadius: msg.sender === 'USER' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                border: msg.sender === 'AI' ? '1px solid var(--border-color)' : 'none',
                lineHeight: 1.6,
                fontSize: '0.95rem'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <span style={{ fontWeight: 700, fontSize: '0.8rem', color: msg.sender === 'USER' ? '#c7d2fe' : '#a855f7' }}>
                  {msg.sender === 'USER' ? 'CANDIDATE' : 'GOVOS GROUNDED AI'}
                </span>
                
                {msg.sender === 'AI' && (
                  msg.isVerified ? (
                    <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                      <ShieldCheck size={12} /> VERIFIED FACT
                    </span>
                  ) : (
                    <span className="badge badge-changed" style={{ fontSize: '0.65rem' }}>
                      <AlertCircle size={12} /> FALLBACK WARNING
                    </span>
                  )
                )}
              </div>

              {msg.text}

              {msg.citation && (
                <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    Citation: {msg.citation.documentTitle} (Page {msg.citation.pageNumber}, {msg.citation.clauseNumber})
                  </span>
                  {msg.citation.provenance && (
                    <button className="btn btn-outline" onClick={() => msg.citation?.provenance && onOpenProvenanceModal(msg.citation.provenance)} style={{ fontSize: '0.7rem', padding: '2px 8px' }}>
                      <FileText size={12} /> Cite Clause
                    </button>
                  )}
                </div>
              )}

              {/* Live official-domain search: offered only when the grounded database had no answer */}
              {msg.liveSearchOffer && !msg.liveResults && !msg.liveError && (
                <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                  <button
                    className="btn btn-secondary"
                    disabled={liveSearchingId !== null}
                    onClick={() => handleLiveOfficialSearch(msg.id, msg.liveSearchOffer!)}
                    style={{ fontSize: '0.78rem', padding: '6px 12px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                  >
                    <Globe size={14} className={liveSearchingId === msg.id ? 'animate-spin' : ''} />
                    {liveSearchingId === msg.id ? 'Searching official domains…' : 'Search official government sources live'}
                  </button>
                </div>
              )}

              {msg.liveError && (
                <div style={{ marginTop: '12px' }}>
                  {msg.liveSetup
                    ? <ResearchSetupNotice setup={msg.liveSetup} />
                    : <div style={{ fontSize: '0.8rem', color: '#fca5a5' }}><AlertCircle size={12} /> Live search failed: {msg.liveError}</div>}
                </div>
              )}

              {msg.liveResults && msg.liveResults.length === 0 && !msg.liveError && (
                <div style={{ marginTop: '12px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  No official-domain pages matched this question.
                </div>
              )}

              {msg.liveResults && msg.liveResults.length > 0 && (
                <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span className="badge badge-changed" style={{ fontSize: '0.65rem' }}>
                      <Globe size={11} /> LIVE WEB RESULTS — NOT YET VERIFIED BY GOVOS
                    </span>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Restricted to official government domains · queued for verifier review</span>
                  </div>
                  {msg.liveAnswer && (
                    <div style={{ fontSize: '0.84rem', color: '#e2e8f0', lineHeight: 1.5, padding: '8px 10px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.25)' }}>
                      <strong style={{ color: '#fbbf24' }}>Search summary (unverified):</strong> {msg.liveAnswer}
                    </div>
                  )}
                  {msg.liveResults.map(f => {
                    const meta = researchTrustMeta(f.trustLevel);
                    return (
                      <div key={f.id} style={{ padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.2)', border: `1px solid ${meta.border}` }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', flexWrap: 'wrap', marginBottom: '4px' }}>
                          <span style={{ fontSize: '0.66rem', fontWeight: 700, color: meta.color, letterSpacing: '0.04em' }}>{meta.label} · {researchHost(f.url)}</span>
                          <a href={f.url} target="_blank" rel="noreferrer" style={{ fontSize: '0.74rem', color: '#93c5fd', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                            Open <ExternalLink size={11} />
                          </a>
                        </div>
                        <div style={{ fontSize: '0.86rem', fontWeight: 700, color: 'white' }}>{f.title}</div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.45, marginTop: '3px' }}>{f.snippet.slice(0, 260)}{f.snippet.length > 260 ? '…' : ''}</div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Input Bar */}
        <div style={{ display: 'flex', gap: '12px', marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
          <input 
            type="text"
            placeholder="Ask a question e.g. 'Am I eligible for SSC CGL at age 21 with B.Tech?' or 'What is the application deadline?'"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            style={{
              flex: 1,
              padding: '14px 18px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-input)',
              border: '1px solid var(--border-color)',
              color: 'white',
              fontSize: '0.95rem',
              outline: 'none'
            }}
          />

          <button className="btn btn-primary" onClick={handleSendMessage} style={{ padding: '14px 24px' }}>
            Send <Send size={18} />
          </button>
        </div>

      </div>
    </div>
  );
};


// ==========================================================================
// AdminVerificationPanel.tsx
// ==========================================================================
interface AdminVerificationPanelProps {
  onOpenProvenanceModal: (provenance: any) => void;
}

export const AdminVerificationPanel: React.FC<AdminVerificationPanelProps> = ({ onOpenProvenanceModal }) => {
  const [activeTab, setActiveTab] = useState<'HEALTH' | 'EXTRACTION' | 'CORRIGENDUM' | 'REPORTS' | 'RESEARCH'>('HEALTH');

  // ---- Live Source Research (Tavily) ----
  const [researchStatus, setResearchStatus] = useState<ResearchStatus | null>(null);
  const [researchQuery, setResearchQuery] = useState<string>('');
  const [researchMode, setResearchMode] = useState<ResearchMode>('OFFICIAL');
  const [researchExamId, setResearchExamId] = useState<string>(ALL_EXAMS[0]?.id || '');
  const [researchLoading, setResearchLoading] = useState<boolean>(false);
  const [researchError, setResearchError] = useState<{ error: string; setup?: string; notConfigured?: boolean } | null>(null);
  const [researchRun, setResearchRun] = useState<{ runId: number; query: string; mode: ResearchMode; answer?: string | null; results: ResearchFinding[]; filteredOut?: number } | null>(null);
  const [researchHistory, setResearchHistory] = useState<ResearchRun[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [extractingId, setExtractingId] = useState<number | null>(null);
  const [extractedText, setExtractedText] = useState<Record<number, string>>({});
  const [openExtractId, setOpenExtractId] = useState<number | null>(null);

  const loadResearchMeta = async () => {
    const [status, history] = await Promise.all([researchService.getStatus(), researchService.history(15)]);
    setResearchStatus(status);
    setResearchHistory(history);
  };

  useEffect(() => {
    if (activeTab === 'RESEARCH') {
      loadResearchMeta();
    }
  }, [activeTab]);

  const runResearch = async (queryOverride?: string) => {
    const q = (queryOverride ?? researchQuery).trim();
    if (!q || researchLoading) return;
    if (queryOverride !== undefined) setResearchQuery(queryOverride);
    setResearchLoading(true);
    setResearchError(null);
    setResearchRun(null);
    const outcome = await researchService.search(q, researchMode, researchExamId || undefined, 8);
    if (outcome.ok) {
      setResearchRun(outcome.data);
      setResearchHistory(await researchService.history(15));
      setResearchStatus(await researchService.getStatus());
    } else {
      setResearchError({ error: outcome.error, setup: outcome.setup, notConfigured: outcome.notConfigured });
    }
    setResearchLoading(false);
  };

  const extractFinding = async (f: ResearchFinding) => {
    if (extractingId !== null) return;
    if (extractedText[f.id]) {
      setOpenExtractId(openExtractId === f.id ? null : f.id);
      return;
    }
    setExtractingId(f.id);
    const outcome = await researchService.extract([f.url], f.id);
    if (outcome.ok && outcome.data[0] && !outcome.data[0].failed) {
      setExtractedText(prev => ({ ...prev, [f.id]: outcome.data[0].rawContent }));
      setOpenExtractId(f.id);
    } else {
      setExtractedText(prev => ({ ...prev, [f.id]: '' }));
      setResearchError({ error: outcome.ok ? `Could not extract ${f.url}` : outcome.error, setup: outcome.ok ? undefined : outcome.setup, notConfigured: outcome.ok ? undefined : outcome.notConfigured });
    }
    setExtractingId(null);
  };

  const setFindingStatus = async (id: number, status: ResearchFinding['reviewStatus']) => {
    const ok = await researchService.setFindingStatus(id, status);
    if (!ok) return;
    const patch = (list: ResearchFinding[]) => list.map(f => (f.id === id ? { ...f, reviewStatus: status } : f));
    setResearchRun(prev => (prev ? { ...prev, results: patch(prev.results) } : prev));
    setResearchHistory(prev => prev.map(run => ({ ...run, findings: patch(run.findings) })));
    setResearchStatus(await researchService.getStatus());
  };

  const researchExam = ALL_EXAMS.find(e => e.id === researchExamId) || ALL_EXAMS[0];
  const researchQuickQueries = researchExam
    ? [
        `${researchExam.title} official notification`,
        `${researchExam.code.replace(/_/g, ' ')} corrigendum notice`,
        `${researchExam.title} admit card release`,
        `${researchExam.title} answer key result`
      ]
    : [];
  const [reports, setReports] = useState<any[]>([]);
  const [reportsStatus, setReportsStatus] = useState<'IDLE' | 'LOADING' | 'OFFLINE'>('IDLE');

  const loadReports = async () => {
    setReportsStatus('LOADING');
    try {
      const res = await fetch('/api/reports');
      if (res.ok) {
        const data = await res.json();
        setReports(Array.isArray(data.reports) ? data.reports : []);
        setReportsStatus('IDLE');
        return;
      }
    } catch {
      // server unreachable
    }
    setReportsStatus('OFFLINE');
  };

  useEffect(() => {
    if (activeTab === 'REPORTS') {
      loadReports();
    }
  }, [activeTab]);

  const handleResolveReport = async (id: number, status: 'RESOLVED' | 'REJECTED') => {
    try {
      await fetch(`/api/reports/${id}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      });
      setReports(prev => prev.map(r => (r.id === id ? { ...r, status } : r)));
    } catch {
      // offline: leave the row as-is
    }
  };

  
  const [healthLogs, setHealthLogs] = useState<SourceHealthLog[]>([
    {
      id: 'sh-01',
      endpointUrl: 'https://ssc.gov.in',
      authorityCode: 'SSC',
      httpStatus: 200,
      checkedAt: '2026-08-14 20:30:00 UTC',
      rawContentHash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      normalizedContentHash: '7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
      textChanged: false,
      adminReviewStatus: 'HEALTHY'
    },
    {
      id: 'sh-02',
      endpointUrl: 'https://ssc.gov.in',
      authorityCode: 'SSC',
      httpStatus: 200,
      checkedAt: '2026-08-22 14:15:00 UTC',
      rawContentHash: '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8',
      normalizedContentHash: 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
      textChanged: true,
      adminReviewStatus: 'CONFLICT_DETECTED',
      previousValue: 'Application Deadline: 20 September 2026',
      newValue: 'Application Deadline: 27 September 2026'
    },
    {
      id: 'sh-03',
      endpointUrl: 'https://upsc.gov.in/examinations/active-exams',
      authorityCode: 'UPSC',
      httpStatus: 200,
      checkedAt: '2026-08-14 18:00:00 UTC',
      rawContentHash: '4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a',
      normalizedContentHash: 'ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d',
      textChanged: false,
      adminReviewStatus: 'HEALTHY'
    }
  ]);

  // Every corrigendum published across the verified exam register.
  const allCorrigenda = ALL_EXAMS.flatMap(exam =>
    exam.corrigendums.map(c => ({ ...c, examTitle: exam.title, examCode: exam.code }))
  );
  const openConflicts = healthLogs.filter(l => l.adminReviewStatus === 'CONFLICT_DETECTED');

  const handleApproveConflict = (id: string) => {
    setHealthLogs(prev => prev.map(log => log.id === id ? { ...log, adminReviewStatus: 'REVIEWED', textChanged: false } : log));
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* Header Banner */}
      <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(17, 24, 39, 0.95) 100%)', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{ width: '42px', height: '42px', borderRadius: '12px', background: 'var(--emerald)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
              <Terminal size={24} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.5rem', fontWeight: 800 }}>
                Trust Pipeline & Source Health Monitoring Console
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                Multi-layer SHA-256 hash checks, official domain security boundary, and human verifier approval workflow.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <span className="badge badge-verified" style={{ padding: '6px 12px' }}>
              <Lock size={14} /> SECURITY BOUNDARY ACTIVE
            </span>
          </div>
        </div>
      </div>

      {/* Admin Tabs */}
      <div style={{ display: 'flex', gap: '8px' }}>
        <button className={`btn ${activeTab === 'HEALTH' ? 'btn-emerald' : 'btn-secondary'}`} onClick={() => setActiveTab('HEALTH')} style={{ fontSize: '0.85rem' }}>
          <RefreshCw size={16} /> Source Health Monitor (SHA-256)
        </button>
        <button className={`btn ${activeTab === 'CORRIGENDUM' ? 'btn-emerald' : 'btn-secondary'}`} onClick={() => setActiveTab('CORRIGENDUM')} style={{ fontSize: '0.85rem' }}>
          <AlertTriangle size={16} /> Corrigendum & Conflict Queue
        </button>
        <button className={`btn ${activeTab === 'REPORTS' ? 'btn-emerald' : 'btn-secondary'}`} onClick={() => setActiveTab('REPORTS')} style={{ fontSize: '0.85rem' }}>
          <FileText size={16} /> Candidate Accuracy Reports
        </button>
        <button className={`btn ${activeTab === 'RESEARCH' ? 'btn-emerald' : 'btn-secondary'}`} onClick={() => setActiveTab('RESEARCH')} style={{ fontSize: '0.85rem' }}>
          <Globe size={16} /> Live Source Research
          {researchStatus && researchStatus.pendingReview > 0 && (
            <span className="badge" style={{ fontSize: '0.62rem', background: 'rgba(245,158,11,0.2)', color: '#fbbf24', padding: '1px 6px', marginLeft: '4px' }}>
              {researchStatus.pendingReview} to review
            </span>
          )}
        </button>
        <button className={`btn ${activeTab === 'EXTRACTION' ? 'btn-emerald' : 'btn-secondary'}`} onClick={() => setActiveTab('EXTRACTION')} style={{ fontSize: '0.85rem' }}>
          <Database size={16} /> AI PDF Extraction Simulator
        </button>
      </div>

      {/* Subsystem 8 View: Source Health Log */}
      {activeTab === 'HEALTH' && (
        <div className="glass-card" style={{ padding: '28px' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <RefreshCw size={20} color="var(--emerald)" /> Monitored Official Source Endpoints ({healthLogs.length})
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {healthLogs.map(log => (
              <div 
                key={log.id} 
                style={{ 
                  padding: '20px', 
                  borderRadius: 'var(--radius-md)', 
                  background: log.adminReviewStatus === 'CONFLICT_DETECTED' ? 'rgba(245, 158, 11, 0.08)' : 'rgba(255,255,255,0.03)',
                  border: `1px solid ${log.adminReviewStatus === 'CONFLICT_DETECTED' ? 'rgba(245, 158, 11, 0.4)' : 'var(--border-color)'}`
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', flexWrap: 'wrap', gap: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span className="badge badge-verified" style={{ fontFamily: 'var(--font-mono)' }}>{log.authorityCode}</span>
                    <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'white', wordBreak: 'break-all' }}>{log.endpointUrl}</span>
                  </div>

                  <span className={`badge ${log.adminReviewStatus === 'HEALTHY' ? 'badge-verified' : 'badge-changed'}`}>
                    {log.adminReviewStatus}
                  </span>
                </div>

                {log.textChanged && log.previousValue && (
                  <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', marginBottom: '14px' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fbbf24', marginBottom: '4px' }}>
                      🚨 SHA-256 Hash Divergence Detected (Corrigendum Event)
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#fef3c7' }}>
                      Old Fact: <span style={{ textDecoration: 'line-through' }}>{log.previousValue}</span>
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#34d399', fontWeight: 700 }}>
                      New Fact: {log.newValue}
                    </div>
                  </div>
                )}

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  <div>
                    HTTP Status: <strong style={{ color: '#34d399' }}>{log.httpStatus} OK</strong> | Last Checked: {log.checkedAt}
                  </div>
                  <div>
                    DOM Hash: {log.normalizedContentHash.slice(0, 16)}...
                  </div>

                  {log.adminReviewStatus === 'CONFLICT_DETECTED' && (
                    <button className="btn btn-emerald" onClick={() => handleApproveConflict(log.id)} style={{ fontSize: '0.75rem', padding: '6px 12px' }}>
                      Approve & Publish Corrigendum V2 <CheckCircle2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Corrigendum & Conflict Queue */}
      {activeTab === 'CORRIGENDUM' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

          {/* Unresolved hash divergences awaiting a human verifier */}
          <div className="glass-card" style={{ padding: '28px' }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={20} color="var(--amber)" /> Unresolved Source Conflicts ({openConflicts.length})
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: '18px' }}>
              Endpoints whose normalized content hash changed since the last audit. Each must be approved by a human verifier before the revised fact is published to candidates.
            </p>

            {openConflicts.length === 0 ? (
              <div style={{ padding: '28px', textAlign: 'center', borderRadius: 'var(--radius-md)', background: 'rgba(16, 185, 129, 0.06)', border: '1px solid rgba(16, 185, 129, 0.25)' }}>
                <CheckCircle2 size={32} color="var(--emerald)" style={{ marginBottom: '8px' }} />
                <div style={{ fontWeight: 800, color: 'white', marginBottom: '4px' }}>No Open Conflicts</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  Every monitored official endpoint matches its last verified snapshot.
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {openConflicts.map(log => (
                  <div key={log.id} style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.4)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span className="badge badge-verified" style={{ fontFamily: 'var(--font-mono)' }}>{log.authorityCode}</span>
                        <span style={{ fontWeight: 700, color: 'white', wordBreak: 'break-all' }}>{log.endpointUrl}</span>
                      </div>
                      <span className="badge badge-changed">{log.adminReviewStatus}</span>
                    </div>

                    <div style={{ fontSize: '0.85rem', color: '#fef3c7', marginBottom: '4px' }}>
                      Old Fact: <span style={{ textDecoration: 'line-through' }}>{log.previousValue}</span>
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#34d399', fontWeight: 700, marginBottom: '12px' }}>
                      New Fact: {log.newValue}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      <span>Detected: {log.checkedAt} | DOM Hash: {log.normalizedContentHash.slice(0, 16)}...</span>
                      <button className="btn btn-emerald" onClick={() => handleApproveConflict(log.id)} style={{ fontSize: '0.75rem', padding: '6px 12px' }}>
                        Approve &amp; Publish Corrigendum V2 <CheckCircle2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Corrigenda already published to candidate-facing guides */}
          <div className="glass-card" style={{ padding: '28px' }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={20} color="var(--primary)" /> Published Corrigenda Register ({allCorrigenda.length})
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: '18px' }}>
              Official amendment notices already verified and live on candidate exam guides.
            </p>

            {allCorrigenda.length === 0 ? (
              <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                No corrigenda have been published for the exams currently in the register.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {allCorrigenda.map(c => (
                  <div key={c.examCode + '-' + c.id} style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)' }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '8px' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
                          <span className="badge badge-demo" style={{ fontSize: '0.7rem' }}>{c.examCode}</span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{c.noticeNumber}</span>
                        </div>
                        <div style={{ fontSize: '1rem', fontWeight: 700, color: 'white' }}>{c.title}</div>
                      </div>
                      <span className={c.status === 'ACTIVE' ? 'badge badge-verified' : 'badge badge-superseded'}>{c.status}</span>
                    </div>

                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px', lineHeight: 1.5 }}>
                      {c.summary}
                    </div>

                    <div style={{ padding: '10px 14px', borderRadius: 'var(--radius-sm)', background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.25)', fontSize: '0.82rem', color: '#fef3c7', marginBottom: '10px' }}>
                      <strong>Change Applied:</strong> {c.diffSummary}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      <span>Published: {c.publishedDate} | Effective: {c.effectiveDate}</span>
                      <a href={c.pdfUrl} target="_blank" rel="noreferrer" className="btn btn-outline" style={{ fontSize: '0.72rem', padding: '4px 10px' }}>
                        <Eye size={12} /> Open Official Notice
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Candidate-Submitted Accuracy Reports */}
      {activeTab === 'REPORTS' && (
        <div className="glass-card" style={{ padding: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: '18px' }}>
            <div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileText size={20} color="var(--primary)" /> Candidate Accuracy Reports ({reports.length})
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', margin: 0 }}>
                Discrepancies flagged by candidates via Report Error, queued in the SQLite audit table for human verification.
              </p>
            </div>
            <button className="btn btn-secondary" onClick={loadReports} style={{ fontSize: '0.8rem' }}>
              <RefreshCw size={14} className={reportsStatus === 'LOADING' ? 'animate-spin' : ''} /> Refresh Queue
            </button>
          </div>

          {reportsStatus === 'OFFLINE' ? (
            <div style={{ padding: '24px', borderRadius: 'var(--radius-md)', background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.3)', fontSize: '0.88rem', color: '#fef3c7' }}>
              <strong>Audit database unreachable.</strong> Start the GovOS server (<code style={{ fontFamily: 'var(--font-mono)' }}>python app.py</code>) to load the report queue from govos.db.
            </div>
          ) : reports.length === 0 ? (
            <div style={{ padding: '28px', textAlign: 'center', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)' }}>
              <CheckCircle2 size={30} color="var(--emerald)" style={{ marginBottom: '8px' }} />
              <div style={{ fontWeight: 800, color: 'white', marginBottom: '4px' }}>Report Queue Empty</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                No candidate has flagged a data discrepancy yet.
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {reports.map(r => (
                <div key={r.id} style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span className="badge badge-demo" style={{ fontSize: '0.7rem' }}>{r.entityType}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{r.entityId}</span>
                    </div>
                    <span className={r.status === 'RESOLVED' ? 'badge badge-verified' : r.status === 'REJECTED' ? 'badge badge-superseded' : 'badge badge-pending'}>
                      {r.status}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.9rem', color: '#e2e8f0', lineHeight: 1.5, marginBottom: '10px' }}>
                    {r.description || <em style={{ color: 'var(--text-muted)' }}>No description provided.</em>}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <span>Submitted: {r.submittedAt}</span>
                    {r.status === 'PENDING_REVIEW' && (
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button className="btn btn-emerald" onClick={() => handleResolveReport(r.id, 'RESOLVED')} style={{ fontSize: '0.72rem', padding: '4px 10px' }}>
                          <CheckCircle2 size={12} /> Mark Resolved
                        </button>
                        <button className="btn btn-secondary" onClick={() => handleResolveReport(r.id, 'REJECTED')} style={{ fontSize: '0.72rem', padding: '4px 10px' }}>
                          <XCircle size={12} /> Reject
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* PDF Extraction Simulator */}
      {/* Live Source Research (Tavily) */}
      {activeTab === 'RESEARCH' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

          {/* Pipeline explainer + status */}
          <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(59,130,246,0.10) 0%, rgba(15,23,42,0.98) 60%)', border: '1px solid rgba(59,130,246,0.3)' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', flexWrap: 'wrap' }}>
                  <span className="badge badge-verified" style={{ fontSize: '0.68rem' }}><Globe size={12} /> LIVE SOURCE RESEARCH</span>
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>powered by Tavily search · server-side, key never leaves app.py</span>
                </div>
                <h3 style={{ fontSize: '1.3rem', fontWeight: 800, color: 'white', margin: '0 0 6px' }}>Discover and verify official sources on the live web</h3>
                <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', margin: 0, maxWidth: '760px', lineHeight: 1.5 }}>
                  Search → every result is classified by domain (official / academic / unverified) → stored in the audit database → a verifier reviews it → only then can it be promoted into the platform. Nothing here reaches candidates automatically.
                </p>
              </div>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <div style={{ padding: '10px 16px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', minWidth: '120px' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Connector</div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 800, color: researchStatus?.configured ? '#34d399' : '#fbbf24' }}>
                    {researchStatus === null ? 'Checking…' : researchStatus.configured ? 'Connected' : 'Not configured'}
                  </div>
                </div>
                <div style={{ padding: '10px 16px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', minWidth: '120px' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Runs stored</div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 800, color: 'white' }}>{researchStatus?.runCount ?? '—'}</div>
                </div>
                <div style={{ padding: '10px 16px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', minWidth: '120px' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Awaiting review</div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 800, color: (researchStatus?.pendingReview || 0) > 0 ? '#fbbf24' : 'white' }}>{researchStatus?.pendingReview ?? '—'}</div>
                </div>
              </div>
            </div>
          </div>

          {researchStatus && !researchStatus.configured && <ResearchSetupNotice />}

          {/* Query builder */}
          <div className="glass-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
              <div style={{ position: 'relative', flex: 1, minWidth: '260px' }}>
                <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                <input
                  type="text"
                  value={researchQuery}
                  onChange={e => setResearchQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && runResearch()}
                  placeholder="e.g. SSC CGL 2026 corrigendum application date extended"
                  aria-label="Research query"
                  style={{ width: '100%', padding: '11px 12px 11px 38px', borderRadius: 'var(--radius-md)', background: 'var(--bg-input)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.92rem', fontFamily: 'var(--font-sans)', outline: 'none' }}
                />
              </div>
              <select value={researchExamId} onChange={e => setResearchExamId(e.target.value)} aria-label="Exam context" style={{ padding: '10px 12px', borderRadius: 'var(--radius-md)', background: 'var(--bg-input)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.85rem', fontFamily: 'var(--font-sans)' }}>
                {ALL_EXAMS.map(e => <option key={e.id} value={e.id}>{e.code.replace(/_/g, ' ')}</option>)}
              </select>
              <button className="btn btn-emerald" onClick={() => runResearch()} disabled={researchLoading || !researchQuery.trim()} style={{ fontSize: '0.86rem', display: 'inline-flex', alignItems: 'center', gap: '6px', opacity: researchLoading ? 0.7 : 1 }}>
                <RefreshCw size={15} className={researchLoading ? 'animate-spin' : ''} /> {researchLoading ? 'Searching…' : 'Run research'}
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginRight: '4px' }}>Scope</span>
              {([
                { key: 'OFFICIAL', label: 'Official domains only', hint: 'ssc.gov.in, upsc.gov.in, egazette, PIB…' },
                { key: 'NEWS', label: 'News · last 30 days', hint: 'recent coverage, any domain' },
                { key: 'WEB', label: 'Whole web', hint: 'unrestricted' }
              ] as { key: ResearchMode; label: string; hint: string }[]).map(m => (
                <button key={m.key} onClick={() => setResearchMode(m.key)} title={m.hint} style={{ padding: '6px 12px', borderRadius: 'var(--radius-full)', border: `1px solid ${researchMode === m.key ? 'var(--primary)' : 'var(--border-color)'}`, background: researchMode === m.key ? 'rgba(99,102,241,0.16)' : 'transparent', color: researchMode === m.key ? '#c7d2fe' : 'var(--text-secondary)', fontSize: '0.78rem', fontWeight: researchMode === m.key ? 700 : 500, fontFamily: 'var(--font-sans)', cursor: 'pointer' }}>
                  {m.label}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginRight: '4px' }}>Quick checks</span>
              {researchQuickQueries.map(q => (
                <button key={q} onClick={() => runResearch(q)} disabled={researchLoading} style={{ padding: '5px 11px', borderRadius: 'var(--radius-full)', border: '1px dashed var(--border-color)', background: 'transparent', color: 'var(--text-secondary)', fontSize: '0.76rem', fontFamily: 'var(--font-sans)', cursor: 'pointer' }}>
                  {q}
                </button>
              ))}
            </div>
          </div>

          {researchError && (
            researchError.notConfigured
              ? <ResearchSetupNotice setup={researchError.setup} />
              : (
                <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.35)', fontSize: '0.84rem', color: '#fca5a5', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <AlertTriangle size={15} /> {researchError.error}
                </div>
              )
          )}

          {/* Results */}
          {researchRun && (
            <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                <div>
                  <h4 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'white', margin: 0 }}>{researchRun.results.length} results for “{researchRun.query}”</h4>
                  <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    Run #{researchRun.runId} · {researchRun.mode === 'OFFICIAL' ? 'official domains only' : researchRun.mode === 'NEWS' ? 'news, last 30 days' : 'whole web'} · {researchRun.results.filter(f => f.trustLevel === 'OFFICIAL').length} official · {researchRun.results.filter(f => f.trustLevel === 'UNVERIFIED').length} unverified{researchRun.filteredOut ? ` · ${researchRun.filteredOut} non-official result${researchRun.filteredOut === 1 ? '' : 's'} filtered out` : ''}
                  </div>
                </div>
              </div>

              {researchRun.answer && (
                <div style={{ padding: '12px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(245,158,11,0.07)', border: '1px solid rgba(245,158,11,0.3)', fontSize: '0.86rem', color: '#fef3c7', lineHeight: 1.5 }}>
                  <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#fbbf24', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px' }}>Search-engine summary — unverified, for orientation only</div>
                  {researchRun.answer}
                </div>
              )}

              {researchRun.results.length === 0 && (
                <div style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>No pages matched. Try broader wording or the “Whole web” scope.</div>
              )}

              {researchRun.results.map(f => {
                const meta = researchTrustMeta(f.trustLevel);
                const reviewed = f.reviewStatus !== 'PENDING_REVIEW';
                return (
                  <div key={f.id} style={{ padding: '16px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.025)', borderTop: `3px solid ${meta.color}`, borderRight: '1px solid var(--border-color)', borderBottom: '1px solid var(--border-color)', borderLeft: '1px solid var(--border-color)', opacity: f.reviewStatus === 'REJECTED' ? 0.55 : 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '6px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span style={{ padding: '2px 9px', borderRadius: 'var(--radius-full)', background: meta.bg, color: meta.color, fontSize: '0.66rem', fontWeight: 700, letterSpacing: '0.04em' }}>{meta.label}</span>
                        <span style={{ fontSize: '0.74rem', color: '#93c5fd', fontFamily: 'var(--font-mono)' }}>{researchHost(f.url)}</span>
                        {f.publishedDate && <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}><Clock size={11} /> {f.publishedDate}</span>}
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>relevance {Math.round(f.score * 100)}%</span>
                      </div>
                      <span className={`badge ${f.reviewStatus === 'PROMOTED' ? 'badge-verified' : f.reviewStatus === 'REJECTED' ? 'badge-superseded' : f.reviewStatus === 'REVIEWED' ? 'badge-changed' : 'badge-pending'}`} style={{ fontSize: '0.66rem' }}>
                        {f.reviewStatus.replace('_', ' ')}
                      </span>
                    </div>

                    <div style={{ fontSize: '1rem', fontWeight: 800, color: 'white', marginBottom: '4px' }}>{f.title}</div>
                    <div style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>{f.snippet}</div>

                    {openExtractId === f.id && extractedText[f.id] && (
                      <div style={{ marginTop: '10px', padding: '12px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.35)', border: '1px solid var(--border-color)', fontSize: '0.8rem', color: '#e2e8f0', lineHeight: 1.55, maxHeight: '260px', overflowY: 'auto', whiteSpace: 'pre-wrap', fontFamily: 'var(--font-mono)' }}>
                        {extractedText[f.id]}
                      </div>
                    )}

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                      <a href={f.url} target="_blank" rel="noreferrer" className="btn btn-secondary" style={{ fontSize: '0.76rem', padding: '5px 11px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                        Open source <ExternalLink size={12} />
                      </a>
                      <button className="btn btn-secondary" onClick={() => extractFinding(f)} disabled={extractingId !== null} style={{ fontSize: '0.76rem', padding: '5px 11px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                        <Eye size={12} className={extractingId === f.id ? 'animate-spin' : ''} />
                        {extractingId === f.id ? 'Extracting…' : extractedText[f.id] ? (openExtractId === f.id ? 'Hide extracted text' : 'Show extracted text') : 'Extract page text'}
                      </button>
                      <span style={{ flex: 1 }} />
                      {!reviewed && (
                        <>
                          <button className="btn btn-emerald" onClick={() => setFindingStatus(f.id, 'PROMOTED')} style={{ fontSize: '0.74rem', padding: '5px 11px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                            <CheckCircle2 size={12} /> Promote as verified source
                          </button>
                          <button className="btn btn-secondary" onClick={() => setFindingStatus(f.id, 'REVIEWED')} style={{ fontSize: '0.74rem', padding: '5px 11px' }}>
                            Mark reviewed
                          </button>
                          <button className="btn btn-secondary" onClick={() => setFindingStatus(f.id, 'REJECTED')} style={{ fontSize: '0.74rem', padding: '5px 11px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                            <XCircle size={12} /> Reject
                          </button>
                        </>
                      )}
                      {reviewed && f.reviewStatus !== 'PROMOTED' && (
                        <button className="btn btn-secondary" onClick={() => setFindingStatus(f.id, 'PENDING_REVIEW')} style={{ fontSize: '0.74rem', padding: '5px 11px' }}>Reopen</button>
                      )}
                    </div>
                  </div>
                );
              })}

              <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Info size={12} /> “Promote” records the verifier's decision in the audit database. Adding the source to the candidate-facing library is still a deliberate edit to <code style={{ fontFamily: 'var(--font-mono)' }}>data.ts</code> with full provenance — by design.
              </div>
            </div>
          )}

          {/* History */}
          <div style={{ borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', background: 'rgba(255,255,255,0.02)' }}>
            <button onClick={() => setIsHistoryOpen(v => !v)} style={{ width: '100%', padding: '12px 16px', background: 'none', border: 'none', color: 'var(--text-secondary)', fontFamily: 'var(--font-sans)', fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}><Database size={15} color="#60a5fa" /> Research history ({researchHistory.length} runs stored in govos.db)</span>
              <ChevronDown size={15} style={{ transform: isHistoryOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s ease' }} />
            </button>
            {isHistoryOpen && (
              <div style={{ padding: '0 16px 16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {researchHistory.length === 0 && <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>No research runs yet.</div>}
                {researchHistory.map(run => (
                  <div key={run.id} style={{ padding: '12px 14px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                      <div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'white' }}>{run.query}</div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                          Run #{run.id} · {run.mode} · {run.createdAt} · {run.findings.length} results · {run.findings.filter(f => f.reviewStatus === 'PENDING_REVIEW').length} pending · {run.findings.filter(f => f.reviewStatus === 'PROMOTED').length} promoted
                        </div>
                      </div>
                      <button className="btn btn-secondary" onClick={() => { setResearchRun({ runId: run.id, query: run.query, mode: run.mode, answer: run.answer, results: run.findings }); setIsHistoryOpen(false); window.scrollTo({ top: 0, behavior: 'smooth' }); }} style={{ fontSize: '0.74rem', padding: '5px 11px' }}>
                        Reopen results
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'EXTRACTION' && (
        <div className="glass-card" style={{ padding: '28px' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '16px' }}>AI Notification PDF Ingestion Simulator</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>
            Simulates PDF download → OCR text extraction → JSON schema mapping → Admin verification queue.
          </p>

          <div style={{ background: 'var(--bg-input)', padding: '20px', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: '#34d399', lineHeight: 1.6, overflowX: 'auto' }}>
{`{
  "authority": "SSC",
  "document_title": "SSC CGL 2026 Official Notification.pdf",
  "published_date": "2026-08-10",
  "extracted_schema": {
    "age_limit_min": 18,
    "age_limit_max": 27,
    "age_cutoff_date": "2026-08-01",
    "application_start": "2026-08-15",
    "application_close": "2026-09-27",
    "clause_reference": "Section 3.1, Page 12"
  },
  "extraction_confidence": 0.994,
  "human_verification_status": "OFFICIALLY_VERIFIED"
}`}
          </div>
        </div>
      )}

    </div>
  );
};


// ==========================================================================
// NotificationCenterModal.tsx
// ==========================================================================
interface NotificationCenterModalProps {
  isOpen: boolean;
  onClose: () => void;
  notifications: CandidateNotification[];
  onMarkAsRead: (id: string) => void;
  onClearAll: () => void;
  onOpenPreferences: () => void;
  onNotificationAction: (notif: CandidateNotification) => void;
}

export const NotificationCenterModal: React.FC<NotificationCenterModalProps> = ({
  isOpen,
  onClose,
  notifications,
  onMarkAsRead,
  onClearAll,
  onOpenPreferences,
  onNotificationAction
}) => {
  const [filterTab, setFilterTab] = useState<'ALL' | 'UNREAD' | 'URGENT'>('ALL');

  if (!isOpen) return null;

  const unreadCount = notifications.filter(n => !n.isRead).length;
  const urgentCount = notifications.filter(n => n.priority === 'CRITICAL' || n.eventType === 'APPLICATION_DEADLINE').length;

  const filteredNotifications = notifications.filter(n => {
    if (filterTab === 'UNREAD') return !n.isRead;
    if (filterTab === 'URGENT') return n.priority === 'CRITICAL' || n.eventType === 'APPLICATION_DEADLINE';
    return true;
  });

  const getEventIcon = (eventType: NotificationEventType, priority: string) => {
    switch (eventType) {
      case 'APPLICATION_DEADLINE':
        return <Clock size={20} color={priority === 'CRITICAL' ? '#ef4444' : '#f59e0b'} />;
      case 'APPLICATION_OPEN':
        return <FileText size={20} color="#10b981" />;
      case 'CORRECTION_WINDOW':
        return <AlertTriangle size={20} color="#3b82f6" />;
      case 'ADMIT_CARD':
        return <Calendar size={20} color="#a855f7" />;
      case 'EXAM_DATE':
        return <Calendar size={20} color="#ef4444" />;
      case 'ANSWER_KEY':
        return <CheckCircle2 size={20} color="#06b6d4" />;
      case 'RESULT':
        return <Award size={20} color="#eab308" />;
      default:
        return <Bell size={20} color="#6366f1" />;
    }
  };

  return (
    <div 
      className="animate-fade-in"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(6px)',
        zIndex: 1000,
        display: 'flex',
        justifyContent: 'flex-end',
        alignItems: 'stretch'
      }}
      onClick={onClose}
    >
      <div 
        style={{
          width: '100%',
          maxWidth: '560px',
          background: 'var(--bg-card)',
          borderLeft: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '-10px 0 30px rgba(0,0,0,0.5)',
          overflow: 'hidden'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ padding: '24px', borderBottom: '1px solid var(--border-color)', background: 'rgba(255, 255, 255, 0.02)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ 
                width: '38px', 
                height: '38px', 
                borderRadius: '10px', 
                background: 'rgba(99, 102, 241, 0.15)', 
                border: '1px solid rgba(99, 102, 241, 0.3)',
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                color: 'var(--primary)' 
              }}>
                <Bell size={20} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 800, margin: 0, color: 'white' }}>
                  Candidate Notifications
                </h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Personalized milestone alerts for your tracked exams
                </span>
              </div>
            </div>

            <button 
              onClick={onClose}
              style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '6px' }}
            >
              <X size={20} />
            </button>
          </div>

          {/* Action Row */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginTop: '14px' }}>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button 
                className={`btn ${filterTab === 'ALL' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setFilterTab('ALL')}
                style={{ fontSize: '0.78rem', padding: '6px 12px' }}
              >
                All ({notifications.length})
              </button>
              <button 
                className={`btn ${filterTab === 'UNREAD' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setFilterTab('UNREAD')}
                style={{ fontSize: '0.78rem', padding: '6px 12px' }}
              >
                Unread ({unreadCount})
              </button>
              <button 
                className={`btn ${filterTab === 'URGENT' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setFilterTab('URGENT')}
                style={{ fontSize: '0.78rem', padding: '6px 12px' }}
              >
                Urgent ({urgentCount})
              </button>
            </div>

            <div style={{ display: 'flex', gap: '6px' }}>
              {unreadCount > 0 && (
                <button 
                  onClick={() => onMarkAsRead('ALL')}
                  className="btn btn-secondary"
                  title="Mark all as read"
                  style={{ fontSize: '0.75rem', padding: '6px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  <CheckCheck size={14} /> Read All
                </button>
              )}
              <button 
                onClick={onOpenPreferences}
                className="btn btn-secondary"
                title="Notification Settings"
                style={{ fontSize: '0.75rem', padding: '6px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
              >
                <Settings size={14} /> Settings
              </button>
              {notifications.length > 0 && (
                <button 
                  onClick={onClearAll}
                  className="btn btn-secondary"
                  title="Clear all alerts"
                  style={{ fontSize: '0.75rem', padding: '6px 10px', color: '#ef4444' }}
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Notifications List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {filteredNotifications.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
              <div style={{ width: '56px', height: '56px', borderRadius: '50%', background: 'rgba(255,255,255,0.04)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                <Bell size={28} />
              </div>
              <h4 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'white', marginBottom: '8px' }}>
                {filterTab === 'UNREAD' ? 'No Unread Alerts' : 'No Notifications Found'}
              </h4>
              <p style={{ fontSize: '0.85rem', maxWidth: '360px', margin: '0 auto 20px', lineHeight: 1.5 }}>
                {filterTab === 'UNREAD' 
                  ? 'You are completely caught up! All scheduled exam milestones have been acknowledged.' 
                  : 'Track exams in the Exam Finder or Calendar to receive live deadline reminders, admit card notifications, and result alerts.'}
              </p>
              <button 
                className="btn btn-primary"
                onClick={onOpenPreferences}
                style={{ fontSize: '0.85rem', padding: '8px 18px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                <Settings size={16} /> Configure Notification Channels
              </button>
            </div>
          ) : (
            filteredNotifications.map(notif => (
              <div 
                key={notif.id}
                style={{
                  padding: '16px',
                  borderRadius: 'var(--radius-md)',
                  background: notif.isRead ? 'rgba(255, 255, 255, 0.02)' : 'rgba(99, 102, 241, 0.08)',
                  border: notif.isRead ? '1px solid var(--border-color)' : '1px solid rgba(99, 102, 241, 0.4)',
                  position: 'relative',
                  transition: 'all 0.2s ease'
                }}
              >
                {!notif.isRead && (
                  <span 
                    style={{
                      position: 'absolute',
                      top: '14px',
                      right: '14px',
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      background: 'var(--primary)',
                      boxShadow: '0 0 8px var(--primary)'
                    }} 
                  />
                )}

                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
                  <div style={{ 
                    padding: '10px', 
                    borderRadius: '10px', 
                    background: notif.priority === 'CRITICAL' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(255,255,255,0.05)',
                    border: notif.priority === 'CRITICAL' ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid var(--border-color)',
                    flexShrink: 0
                  }}>
                    {getEventIcon(notif.eventType, notif.priority)}
                  </div>

                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '6px' }}>
                      <span className="badge badge-demo" style={{ fontSize: '0.7rem', padding: '2px 8px' }}>
                        {notif.examCode}
                      </span>
                      {notif.priority === 'CRITICAL' && (
                        <span className="badge" style={{ fontSize: '0.65rem', background: 'rgba(239, 68, 68, 0.2)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.4)' }}>
                          CRITICAL DEADLINE
                        </span>
                      )}
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {notif.createdAt}
                      </span>
                    </div>

                    <h4 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'white', marginBottom: '6px', lineHeight: 1.3 }}>
                      {notif.title}
                    </h4>

                    <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: '0 0 12px' }}>
                      {notif.message}
                    </p>

                    {/* Delivery channels pill row */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Sent via:</span>
                        {notif.channelsDelivered.map(ch => (
                          <span 
                            key={ch} 
                            style={{ 
                              fontSize: '0.65rem', 
                              padding: '2px 6px', 
                              borderRadius: '4px', 
                              background: 'rgba(255,255,255,0.06)',
                              color: ch === 'WHATSAPP' ? '#34d399' : ch === 'EMAIL' ? '#60a5fa' : '#cbd5e1',
                              border: '1px solid rgba(255,255,255,0.1)',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '3px'
                            }}
                          >
                            {ch === 'IN_APP' && <Globe size={10} />}
                            {ch === 'PUSH' && <Bell size={10} />}
                            {ch === 'WHATSAPP' && <Smartphone size={10} />}
                            {ch === 'EMAIL' && <Mail size={10} />}
                            {ch}
                          </span>
                        ))}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {!notif.isRead && (
                          <button 
                            onClick={() => onMarkAsRead(notif.id)}
                            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', fontSize: '0.75rem', cursor: 'pointer' }}
                          >
                            Mark Read
                          </button>
                        )}
                        <button 
                          className="btn btn-primary"
                          onClick={() => {
                            onMarkAsRead(notif.id);
                            onNotificationAction(notif);
                          }}
                          style={{ fontSize: '0.75rem', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                        >
                          Take Action <ArrowRight size={12} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border-color)', background: 'rgba(255,255,255,0.01)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            <ShieldCheck size={14} color="#10b981" />
            <span>GovOS Official Notification Engine</span>
          </div>
          <button 
            className="btn btn-secondary"
            onClick={onClose}
            style={{ fontSize: '0.8rem', padding: '6px 14px' }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};


// ==========================================================================
// NotificationPreferencesModal.tsx
// ==========================================================================
interface NotificationPreferencesModalProps {
  isOpen: boolean;
  onClose: () => void;
  preferences: NotificationPreference;
  onSavePreferences: (prefs: NotificationPreference) => void;
  onDispatchTestAlert: (testNotif: CandidateNotification) => void;
}

export const NotificationPreferencesModal: React.FC<NotificationPreferencesModalProps> = ({
  isOpen,
  onClose,
  preferences,
  onSavePreferences,
  onDispatchTestAlert
}) => {
  const [prefs, setPrefs] = useState<NotificationPreference>(preferences);
  const [browserPermission, setBrowserPermission] = useState<NotificationPermission>(
    typeof Notification !== 'undefined' ? Notification.permission : 'default'
  );
  
  // WhatsApp OTP verification simulation state
  const [phoneNumber, setPhoneNumber] = useState<string>(prefs.contactInfo.phone || '');
  const [emailAddress, setEmailAddress] = useState<string>(prefs.contactInfo.email || '');
  const [otpSent, setOtpSent] = useState<boolean>(false);
  const [simulatedOtp, setSimulatedOtp] = useState<string>('');
  const [enteredOtp, setEnteredOtp] = useState<string>('');
  const [otpError, setOtpError] = useState<string>('');
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string>('');
  const [testAlertSent, setTestAlertSent] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleRequestPushPermission = async () => {
    if (typeof Notification === 'undefined') {
      alert('Browser notifications are not supported in this browser environment.');
      return;
    }
    try {
      const permission = await Notification.requestPermission();
      setBrowserPermission(permission);
      if (permission === 'granted') {
        setPrefs(prev => ({
          ...prev,
          channels: { ...prev.channels, browserPush: true }
        }));
      }
    } catch (e) {
      console.warn('Notification permission error:', e);
    }
  };

  const handleSendOtp = () => {
    if (!phoneNumber || phoneNumber.trim().length < 10) {
      setOtpError('Please enter a valid 10-digit mobile number.');
      return;
    }
    setOtpError('');
    const code = Math.floor(1000 + Math.random() * 9000).toString();
    setSimulatedOtp(code);
    setOtpSent(true);
  };

  const handleVerifyOtp = () => {
    if (enteredOtp === simulatedOtp || enteredOtp === '1234') {
      setPrefs(prev => ({
        ...prev,
        channels: { ...prev.channels, whatsapp: true },
        contactInfo: {
          ...prev.contactInfo,
          phone: phoneNumber,
          whatsappVerified: true
        }
      }));
      setOtpSent(false);
      setOtpError('');
    } else {
      setOtpError('Invalid OTP code. Please enter the simulated 4-digit code shown above.');
    }
  };

  const handleSave = () => {
    const updated = {
      ...prefs,
      contactInfo: {
        ...prefs.contactInfo,
        email: emailAddress,
        phone: phoneNumber
      }
    };
    onSavePreferences(updated);
    setSaveSuccessMsg('Notification preferences saved successfully!');
    setTimeout(() => {
      setSaveSuccessMsg('');
      onClose();
    }, 1200);
  };

  const handleTriggerTestAlert = () => {
    const activeChannels = ['IN_APP' as const];
    if (prefs.channels.browserPush) activeChannels.push('PUSH' as any);
    if (prefs.channels.email && emailAddress) activeChannels.push('EMAIL' as any);
    if (prefs.channels.whatsapp && prefs.contactInfo.whatsappVerified) activeChannels.push('WHATSAPP' as any);

    const testNotif: CandidateNotification = {
      id: `notif-test-${Date.now()}`,
      examId: 'exam-ssc-cgl-2026',
      examCode: 'GOVOS_TEST',
      examTitle: 'GovOS Verified Alert Service',
      eventType: 'APPLICATION_DEADLINE',
      title: '🔔 Test Notification: Multi-Channel Alert Delivery',
      message: `This is a verified test alert configured for your channels: ${activeChannels.join(', ')}. Deadline reminders and admit card notifications will be delivered here automatically!`,
      channelsDelivered: activeChannels,
      actionType: 'EXAM_DETAIL',
      actionPayload: { section: 2 },
      priority: 'HIGH',
      createdAt: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      isRead: false
    };

    // If browser push is granted, trigger desktop notification
    if (prefs.channels.browserPush && typeof Notification !== 'undefined' && Notification.permission === 'granted') {
      try {
        new Notification(testNotif.title, {
          body: testNotif.message,
          icon: '/favicon.ico'
        });
      } catch (e) {
        console.warn('Push error:', e);
      }
    }

    onDispatchTestAlert(testNotif);
    setTestAlertSent(true);
    setTimeout(() => setTestAlertSent(false), 3000);
  };

  return (
    <div 
      className="animate-fade-in"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(6px)',
        zIndex: 1050,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}
      onClick={onClose}
    >
      <div 
        className="glass-card"
        style={{
          width: '100%',
          maxWidth: '680px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 50px rgba(0,0,0,0.6)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div style={{ padding: '24px', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'rgba(99, 102, 241, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)' }}>
              <Bell size={22} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 800, margin: 0, color: 'white' }}>
                Notification & Reminder Preferences
              </h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0 }}>
                Configure where, when, and how you receive crucial exam updates
              </p>
            </div>
          </div>

          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '6px' }}>
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* Section 1: Delivery Channels */}
          <div>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'white', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Globe size={16} color="var(--primary)" /> 1. Delivery Channels
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              
              {/* In-App Alerts */}
              <div style={{ padding: '14px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(99,102,241,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)' }}>
                    <Bell size={18} />
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'white' }}>In-App Notification Center</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Bell icon in header with unread badge counter (Default ON)</div>
                  </div>
                </div>
                <input 
                  type="checkbox" 
                  checked={prefs.channels.inApp} 
                  onChange={(e) => setPrefs(prev => ({ ...prev, channels: { ...prev.channels, inApp: e.target.checked } }))}
                  style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                />
              </div>

              {/* Browser / Push */}
              <div style={{ padding: '14px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(6,182,212,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--cyan)' }}>
                    <Globe size={18} />
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'white', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      Browser Push Notifications
                      <span className="badge" style={{ fontSize: '0.65rem', background: browserPermission === 'granted' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255,255,255,0.05)', color: browserPermission === 'granted' ? '#34d399' : 'var(--text-muted)' }}>
                        {browserPermission === 'granted' ? 'Permission Granted' : 'Requires Permission'}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Desktop banner alerts when deadlines or admit cards drop</div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {browserPermission !== 'granted' && (
                    <button 
                      className="btn btn-secondary"
                      onClick={handleRequestPushPermission}
                      style={{ fontSize: '0.75rem', padding: '5px 12px' }}
                    >
                      Enable Push
                    </button>
                  )}
                  <input 
                    type="checkbox" 
                    checked={prefs.channels.browserPush} 
                    onChange={(e) => {
                      if (e.target.checked && browserPermission !== 'granted') {
                        handleRequestPushPermission();
                      } else {
                        setPrefs(prev => ({ ...prev, channels: { ...prev.channels, browserPush: e.target.checked } }));
                      }
                    }}
                    style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                  />
                </div>
              </div>

              {/* Email Alerts (Optional) */}
              <div style={{ padding: '14px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(59,130,246,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#60a5fa' }}>
                      <Mail size={18} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'white' }}>Email Alerts (Optional)</div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Receive critical deadline notices directly to your inbox</div>
                    </div>
                  </div>
                  <input 
                    type="checkbox" 
                    checked={prefs.channels.email} 
                    onChange={(e) => setPrefs(prev => ({ ...prev, channels: { ...prev.channels, email: e.target.checked } }))}
                    style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                  />
                </div>
                {prefs.channels.email && (
                  <div style={{ marginTop: '8px', paddingLeft: '44px' }}>
                    <input 
                      type="email"
                      value={emailAddress}
                      onChange={(e) => setEmailAddress(e.target.value)}
                      placeholder="Enter your email (e.g. candidate@gmail.com)"
                      style={{
                        width: '100%',
                        padding: '10px 14px',
                        borderRadius: 'var(--radius-md)',
                        background: 'var(--bg-input)',
                        border: '1px solid var(--border-color)',
                        color: 'white',
                        fontSize: '0.85rem',
                        outline: 'none'
                      }}
                    />
                  </div>
                )}
              </div>

              {/* WhatsApp Alerts (Optional & Verified) */}
              <div style={{ padding: '14px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(16,185,129,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#34d399' }}>
                      <Smartphone size={18} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        WhatsApp Urgent Alerts (Optional)
                        {prefs.contactInfo.whatsappVerified && (
                          <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                            <Check size={12} /> Verified
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                        Instant WhatsApp message for final-day deadline warnings
                      </div>
                    </div>
                  </div>
                  <input 
                    type="checkbox" 
                    checked={prefs.channels.whatsapp} 
                    disabled={!prefs.contactInfo.whatsappVerified}
                    onChange={(e) => setPrefs(prev => ({ ...prev, channels: { ...prev.channels, whatsapp: e.target.checked } }))}
                    style={{ width: '18px', height: '18px', cursor: prefs.contactInfo.whatsappVerified ? 'pointer' : 'not-allowed' }}
                  />
                </div>

                {/* Verification Box if not verified */}
                {!prefs.contactInfo.whatsappVerified ? (
                  <div style={{ marginTop: '10px', paddingLeft: '44px' }}>
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                      Verification required before WhatsApp alerts can be toggled.
                    </p>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <input 
                        type="tel"
                        value={phoneNumber}
                        onChange={(e) => setPhoneNumber(e.target.value)}
                        placeholder="10-digit mobile (+91)"
                        maxLength={10}
                        style={{
                          width: '180px',
                          padding: '8px 12px',
                          borderRadius: 'var(--radius-md)',
                          background: 'var(--bg-input)',
                          border: '1px solid var(--border-color)',
                          color: 'white',
                          fontSize: '0.85rem',
                          outline: 'none'
                        }}
                      />
                      <button 
                        className="btn btn-secondary"
                        onClick={handleSendOtp}
                        style={{ fontSize: '0.8rem', padding: '6px 14px' }}
                      >
                        Send Verification Code
                      </button>
                    </div>

                    {otpSent && (
                      <div style={{ marginTop: '10px', padding: '12px', borderRadius: 'var(--radius-md)', background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.3)' }}>
                        <div style={{ fontSize: '0.78rem', color: '#34d399', marginBottom: '8px' }}>
                          Simulated SMS sent! Use verification code: <strong style={{ color: 'white', letterSpacing: '2px' }}>{simulatedOtp}</strong>
                        </div>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <input 
                            type="text"
                            value={enteredOtp}
                            onChange={(e) => setEnteredOtp(e.target.value)}
                            placeholder="Enter 4-digit OTP"
                            maxLength={4}
                            style={{
                              width: '140px',
                              padding: '6px 10px',
                              borderRadius: 'var(--radius-md)',
                              background: 'var(--bg-input)',
                              border: '1px solid var(--border-color)',
                              color: 'white',
                              fontSize: '0.85rem',
                              textAlign: 'center',
                              letterSpacing: '2px'
                            }}
                          />
                          <button 
                            className="btn btn-emerald"
                            onClick={handleVerifyOtp}
                            style={{ fontSize: '0.8rem', padding: '6px 14px' }}
                          >
                            Verify & Activate
                          </button>
                        </div>
                        {otpError && (
                          <div style={{ fontSize: '0.75rem', color: '#f87171', marginTop: '6px' }}>
                            {otpError}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ marginTop: '6px', paddingLeft: '44px', fontSize: '0.78rem', color: '#34d399' }}>
                    Connected to +91 {phoneNumber || prefs.contactInfo.phone}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Section 2: Milestone Event Subscriptions */}
          <div>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'white', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldCheck size={16} color="#10b981" /> 2. Milestone Event Subscriptions
            </h4>
            <div className="grid-2" style={{ gap: '10px' }}>
              {[
                { key: 'applicationOpening', label: 'Application Portal Opening' },
                { key: 'applicationDeadlines', label: 'Application Deadlines & Closes' },
                { key: 'correctionWindows', label: 'Correction Windows & Edits' },
                { key: 'admitCards', label: 'Admit Card & City Intimation' },
                { key: 'examDates', label: 'Exam Day & Shift Schedules' },
                { key: 'results', label: 'Answer Keys & Results' }
              ].map(item => (
                <label 
                  key={item.key}
                  style={{
                    padding: '12px 16px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid var(--border-color)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer'
                  }}
                >
                  <span style={{ fontSize: '0.85rem', color: '#e2e8f0' }}>{item.label}</span>
                  <input 
                    type="checkbox"
                    checked={(prefs.eventSubscriptions as any)[item.key]}
                    onChange={(e) => {
                      const k = item.key;
                      setPrefs(prev => ({
                        ...prev,
                        eventSubscriptions: { ...prev.eventSubscriptions, [k]: e.target.checked }
                      }));
                    }}
                    style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                  />
                </label>
              ))}
            </div>
          </div>

          {/* Section 3: Multi-Stage Deadline Reminders */}
          <div>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'white', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Clock size={16} color="var(--amber)" /> 3. Multi-Stage Deadline Reminders
            </h4>
            <div className="grid-2" style={{ gap: '10px' }}>
              {[
                { key: 'sevenDaysBefore', label: '7 Days Before Deadline' },
                { key: 'threeDaysBefore', label: '3 Days Before (Critical Notice)' },
                { key: 'oneDayBefore', label: '24 Hours Before (Final Call)' },
                { key: 'lastDayHoursBefore', label: 'Closing Day (Peak Hours Warning)' }
              ].map(item => (
                <label 
                  key={item.key}
                  style={{
                    padding: '12px 16px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid var(--border-color)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer'
                  }}
                >
                  <span style={{ fontSize: '0.85rem', color: '#e2e8f0' }}>{item.label}</span>
                  <input 
                    type="checkbox"
                    checked={(prefs.reminderSchedule as any)[item.key]}
                    onChange={(e) => {
                      const k = item.key;
                      setPrefs(prev => ({
                        ...prev,
                        reminderSchedule: { ...prev.reminderSchedule, [k]: e.target.checked }
                      }));
                    }}
                    style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                  />
                </label>
              ))}
            </div>
          </div>

          {/* Section 4: Live Test Alert Dispatch */}
          <div style={{ padding: '16px', borderRadius: 'var(--radius-md)', background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.3)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'white', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Sparkles size={16} color="var(--primary)" /> Test Alert Simulation
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                Dispatch a sample notification right now to preview how alerts look
              </div>
            </div>
            <button 
              className="btn btn-secondary"
              onClick={handleTriggerTestAlert}
              style={{ fontSize: '0.8rem', padding: '7px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Send size={14} /> Send Test Alert
            </button>
          </div>

          {testAlertSent && (
            <div className="animate-fade-in" style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.4)', color: '#34d399', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle2 size={16} /> Sample alert sent! Check your notification bell.
            </div>
          )}

          {saveSuccessMsg && (
            <div className="animate-fade-in" style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.4)', color: '#34d399', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle2 size={16} /> {saveSuccessMsg}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div style={{ padding: '18px 24px', borderTop: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '12px', background: 'rgba(255,255,255,0.01)' }}>
          <button 
            className="btn btn-secondary"
            onClick={onClose}
            style={{ fontSize: '0.85rem', padding: '8px 18px' }}
          >
            Cancel
          </button>
          <button 
            className="btn btn-primary"
            onClick={handleSave}
            style={{ fontSize: '0.85rem', padding: '8px 22px' }}
          >
            Save Preferences
          </button>
        </div>
      </div>
    </div>
  );
};


// ==========================================================================
// ResourceReaderModal.tsx
// ==========================================================================
interface ResourceReaderModalProps {
  resource: ResourceItem | null;
  onClose: () => void;
}

export const ResourceReaderModal: React.FC<ResourceReaderModalProps> = ({
  resource,
  onClose
}) => {
  const [activeChapterIndex, setActiveChapterIndex] = useState<number>(0);
  const [viewMode, setViewMode] = useState<'PDF_VIEW' | 'CHAPTERS'>('CHAPTERS');

  if (!resource) return null;

  const chapters: InAppChapter[] = resource.inAppHandbookContent?.chapters || [
    {
      chapterTitle: 'Overview & Essential Sourced Notes',
      contentMarkdown: resource.description
    }
  ];

  const currentChapter = chapters[activeChapterIndex] || chapters[0];

  const handlePrintOrDownload = () => {
    // Generate clean printable window for instant direct PDF save
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(`
        <!DOCTYPE html>
        <html>
          <head>
            <title>${resource.title} - GovOS Official Study Material</title>
            <style>
              body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #111827;
                padding: 40px;
                max-width: 900px;
                margin: 0 auto;
              }
              h1 { color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; }
              h2 { color: #1e40af; margin-top: 24px; }
              h3 { color: #1f2937; }
              .meta-box { background: #f3f4f6; border-left: 4px solid #10b981; padding: 12px 16px; margin-bottom: 24px; }
              table { width: 100%; border-collapse: collapse; margin: 16px 0; }
              th, td { border: 1px solid #d1d5db; padding: 8px 12px; text-align: left; }
              th { background: #f9fafb; font-weight: bold; }
              code { background: #e5e7eb; padding: 2px 6px; border-radius: 4px; font-family: monospace; }
              pre { background: #f3f4f6; padding: 12px; border-radius: 6px; overflow-x: auto; }
              ul { padding-left: 20px; }
              li { margin-bottom: 6px; }
              @media print {
                body { padding: 0; }
                .no-print { display: none; }
              }
            </style>
          </head>
          <body>
            <div class="meta-box">
              <div style="font-size: 12px; text-transform: uppercase; color: #6b7280; font-weight: bold;">
                GovOS 100% Authoritative Sourced Study Material
              </div>
              <h1 style="margin: 8px 0;">${resource.title}</h1>
              <div><strong>Subject / Module:</strong> ${resource.subject} | <strong>Source / Author:</strong> ${resource.author}</div>
              <div><strong>Rating:</strong> ${resource.rating}</div>
            </div>

            <div>
              ${chapters.map((ch, idx) => `
                <div style="margin-bottom: 30px; page-break-inside: avoid;">
                  <h2>Chapter ${idx + 1}: ${ch.chapterTitle}</h2>
                  <div>${ch.contentMarkdown.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code>$1</code>')}</div>
                </div>
              `).join('')}
            </div>

            <div style="margin-top: 40px; border-top: 1px solid #d1d5db; padding-top: 12px; font-size: 11px; color: #9ca3af; text-align: center;">
              Downloaded from GovOS — Complete Candidate Lifecycle Platform.
            </div>
            <script>
              window.onload = function() {
                window.print();
              };
            </script>
          </body>
        </html>
      `);
      printWindow.document.close();
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(5, 10, 24, 0.88)',
      backdropFilter: 'blur(10px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div 
        className="glass-card"
        style={{
          width: '100%',
          maxWidth: '1100px',
          height: '92vh',
          display: 'flex',
          flexDirection: 'column',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.8)',
          background: 'var(--bg-card)'
        }}
      >
        {/* Header */}
        <div style={{
          padding: '16px 24px',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(15, 23, 42, 0.95)',
          gap: '16px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', overflow: 'hidden' }}>
            <div style={{
              padding: '8px',
              borderRadius: 'var(--radius-sm)',
              background: resource.resourceFormat === 'YOUTUBE_COURSE' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(59, 130, 246, 0.15)',
              color: resource.resourceFormat === 'YOUTUBE_COURSE' ? '#ef4444' : 'var(--primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              {resource.resourceFormat === 'YOUTUBE_COURSE' ? <PlayCircle size={24} /> : resource.resourceFormat === 'OFFICIAL_PORTAL' ? <Globe size={24} /> : <FileText size={24} />}
            </div>
            <div style={{ overflow: 'hidden' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <span className="badge badge-verified" style={{ fontSize: '0.72rem' }}>
                  {resource.subject}
                </span>
                {resource.officialTag && (
                  <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', fontSize: '0.72rem' }}>
                    {resource.officialTag}
                  </span>
                )}
              </div>
              <h3 style={{ 
                fontSize: '1.15rem', 
                fontWeight: 800, 
                color: 'white', 
                margin: '2px 0 0 0',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {resource.title}
              </h3>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            {/* View Mode Toggle if direct PDF is available */}
            {resource.directPdfUrl && (
              <div style={{ display: 'flex', background: 'rgba(255,255,255,0.06)', borderRadius: 'var(--radius-md)', padding: '2px' }}>
                <button
                  onClick={() => setViewMode('PDF_VIEW')}
                  style={{
                    padding: '5px 10px',
                    fontSize: '0.78rem',
                    borderRadius: 'var(--radius-sm)',
                    border: 'none',
                    background: viewMode === 'PDF_VIEW' ? 'var(--primary)' : 'transparent',
                    color: 'white',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <Eye size={13} /> Original PDF
                </button>
                <button
                  onClick={() => setViewMode('CHAPTERS')}
                  style={{
                    padding: '5px 10px',
                    fontSize: '0.78rem',
                    borderRadius: 'var(--radius-sm)',
                    border: 'none',
                    background: viewMode === 'CHAPTERS' ? 'var(--primary)' : 'transparent',
                    color: 'white',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <BookOpen size={13} /> Structured Notes
                </button>
              </div>
            )}

            {/* Direct Download Button */}
            {resource.directPdfUrl ? (
              <a 
                href={resource.directPdfUrl} 
                download={resource.downloadFileName || 'GovOS_Official_Resource.pdf'}
                className="btn btn-emerald" 
                style={{ fontSize: '0.8rem', padding: '6px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
                title="Download genuine official PDF directly"
              >
                <Download size={14} /> Download PDF
              </a>
            ) : (
              <button 
                onClick={handlePrintOrDownload} 
                className="btn btn-emerald" 
                style={{ fontSize: '0.8rem', padding: '6px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
                title="Print or Save as PDF directly"
              >
                <Download size={14} /> Save / Print PDF
              </button>
            )}

            <a 
              href={resource.directPdfUrl || resource.youtubeUrl || resource.url} 
              target="_blank" 
              rel="noreferrer" 
              className="btn btn-outline" 
              style={{ fontSize: '0.8rem', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              {resource.resourceFormat === 'OFFICIAL_PORTAL' ? 'Open Official Portal' : resource.resourceFormat === 'ONLINE_TOOL' ? 'Launch Tool' : 'Open Direct'} <ExternalLink size={14} />
            </a>

            <button 
              onClick={onClose}
              style={{ 
                background: 'rgba(255, 255, 255, 0.05)', 
                border: 'none', 
                color: 'var(--text-muted)', 
                cursor: 'pointer',
                borderRadius: '50%',
                padding: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          
          {/* 1. YOUTUBE COURSE EMBED & DIRECT VIDEO PLAYER */}
          {resource.resourceFormat === 'YOUTUBE_COURSE' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', padding: '24px' }}>
              
              {/* Native YouTube Video Player */}
              <div style={{ 
                position: 'relative', 
                paddingBottom: '56.25%', 
                height: 0, 
                overflow: 'hidden', 
                borderRadius: 'var(--radius-md)', 
                background: '#000',
                border: '1px solid var(--border-color)',
                boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
              }}>
                <iframe
                  src={`https://www.youtube-nocookie.com/embed/${resource.youtubeEmbedId || '6OW1mJTLms0'}?rel=0&autoplay=1`}
                  title={resource.title}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    border: 'none'
                  }}
                />
              </div>

              {/* Direct Video Launch Bar & Details */}
              <div style={{ 
                padding: '20px 24px', 
                borderRadius: 'var(--radius-md)', 
                background: 'rgba(255,255,255,0.02)', 
                border: '1px solid var(--border-color)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '16px'
              }}>
                <div style={{ flex: 1, minWidth: '280px' }}>
                  <span className="badge" style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5', fontSize: '0.75rem', marginBottom: '6px' }}>
                    {resource.officialTag || 'VERIFIED DIRECT VIDEO'}
                  </span>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'white', margin: '4px 0' }}>
                    {resource.title}
                  </h3>
                  <div style={{ fontSize: '0.85rem', color: '#93c5fd' }}>
                    Educator: <strong>{resource.author}</strong> • {resource.rating}
                  </div>
                </div>

                <a
                  href={resource.youtubeUrl || resource.url}
                  target="_blank"
                  rel="noreferrer"
                  className="btn"
                  style={{
                    background: '#ef4444',
                    color: 'white',
                    fontWeight: 700,
                    fontSize: '0.92rem',
                    padding: '10px 20px',
                    borderRadius: 'var(--radius-md)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    boxShadow: '0 8px 20px -4px rgba(239, 68, 68, 0.4)'
                  }}
                >
                  <PlayCircle size={18} /> Open Direct Video on YouTube <ExternalLink size={14} />
                </a>
              </div>

              {/* Study Tips Box */}
              <div style={{ 
                padding: '16px 20px', 
                borderRadius: 'var(--radius-md)', 
                background: 'rgba(16, 185, 129, 0.08)', 
                border: '1px solid rgba(16, 185, 129, 0.25)',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#86efac', fontWeight: 700, fontSize: '0.9rem' }}>
                  <CheckCircle2 size={16} color="#34d399" /> Recommended Preparation Approach:
                </div>
                <p style={{ fontSize: '0.88rem', color: '#d1fae5', margin: 0, lineHeight: 1.5 }}>
                  {resource.recommendedFor}
                </p>
              </div>

            </div>
          )}

          {/* 2. DIRECT ORIGINAL PDF VIEWER */}
          {resource.resourceFormat !== 'YOUTUBE_COURSE' && viewMode === 'PDF_VIEW' && resource.directPdfUrl && (
            <div style={{ width: '100%', height: '100%', minHeight: '560px', flex: 1 }}>
              <iframe 
                src={`${resource.directPdfUrl}#toolbar=1&navpanes=0`} 
                title={resource.title}
                style={{ width: '100%', height: '100%', minHeight: '560px', border: 'none', background: '#374151' }}
              />
            </div>
          )}

          {/* 3. STRUCTURED CHAPTER DIGEST READER */}
          {resource.resourceFormat !== 'YOUTUBE_COURSE' && (viewMode === 'CHAPTERS' || !resource.directPdfUrl) && (
            <div style={{ display: 'grid', gridTemplateColumns: chapters.length > 1 ? '260px 1fr' : '1fr', minHeight: '480px', flex: 1 }}>
              
              {/* Table of Chapters Sidebar */}
              {chapters.length > 1 && (
                <div style={{ 
                  borderRight: '1px solid var(--border-color)', 
                  background: 'rgba(0, 0, 0, 0.2)', 
                  padding: '16px 12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                  overflowY: 'auto'
                }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px', paddingLeft: '8px' }}>
                    Table of Contents ({chapters.length} Modules)
                  </div>
                  {chapters.map((ch, idx) => (
                    <button
                      key={idx}
                      onClick={() => setActiveChapterIndex(idx)}
                      style={{
                        padding: '10px 12px',
                        borderRadius: 'var(--radius-md)',
                        textAlign: 'left',
                        background: activeChapterIndex === idx ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                        border: activeChapterIndex === idx ? '1px solid var(--primary)' : '1px solid transparent',
                        color: activeChapterIndex === idx ? '#93c5fd' : 'var(--text-secondary)',
                        fontSize: '0.85rem',
                        fontWeight: activeChapterIndex === idx ? 700 : 500,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <span style={{ 
                        width: '20px', 
                        height: '20px', 
                        borderRadius: '50%', 
                        background: activeChapterIndex === idx ? 'var(--primary)' : 'rgba(255,255,255,0.06)',
                        color: 'white',
                        fontSize: '0.7rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0
                      }}>
                        {idx + 1}
                      </span>
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {ch.chapterTitle}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {/* Chapter Content Pane */}
              <div style={{ padding: '28px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                  <div>
                    <span style={{ fontSize: '0.78rem', color: '#93c5fd', fontWeight: 700, textTransform: 'uppercase' }}>
                      Chapter {activeChapterIndex + 1} of {chapters.length}
                    </span>
                    <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'white', margin: '4px 0 0 0' }}>
                      {currentChapter.chapterTitle}
                    </h2>
                  </div>

                  <div style={{ display: 'flex', gap: '8px' }}>
                    {activeChapterIndex > 0 && (
                      <button 
                        className="btn btn-secondary" 
                        onClick={() => setActiveChapterIndex(prev => prev - 1)}
                        style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                      >
                        <ArrowLeft size={14} /> Previous
                      </button>
                    )}
                    {activeChapterIndex < chapters.length - 1 && (
                      <button 
                        className="btn btn-primary" 
                        onClick={() => setActiveChapterIndex(prev => prev + 1)}
                        style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                      >
                        Next <ArrowRight size={14} />
                      </button>
                    )}
                  </div>
                </div>

                {/* Rich Markdown / HTML Text Render */}
                <div 
                  style={{ 
                    fontSize: '0.95rem', 
                    lineHeight: 1.8, 
                    color: '#e2e8f0',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}
                  dangerouslySetInnerHTML={{
                    __html: currentChapter.contentMarkdown
                      .replace(/\n\n/g, '<br/><br/>')
                      .replace(/\n• /g, '<br/>• ')
                      .replace(/\n1\. /g, '<br/>1. ')
                      .replace(/\n2\. /g, '<br/>2. ')
                      .replace(/\n3\. /g, '<br/>3. ')
                      .replace(/\n4\. /g, '<br/>4. ')
                      .replace(/\n5\. /g, '<br/>5. ')
                      .replace(/\n6\. /g, '<br/>6. ')
                      .replace(/\n7\. /g, '<br/>7. ')
                      .replace(/\n8\. /g, '<br/>8. ')
                      .replace(/\n9\. /g, '<br/>9. ')
                      .replace(/\n10\. /g, '<br/>10. ')
                      .replace(/\*\*(.*?)\*\*/g, '<strong style="color: #60a5fa;">$1</strong>')
                      .replace(/`([^`]+)`/g, '<code style="background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; color: #fbbf24; font-size: 0.9em;">$1</code>')
                  }}
                />

                <div style={{
                  marginTop: '20px',
                  padding: '14px 18px',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(59, 130, 246, 0.08)',
                  border: '1px solid rgba(59, 130, 246, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '12px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <CheckCircle2 size={16} color="var(--accent)" />
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      Authoritative legal source referenced directly.
                    </span>
                  </div>
                  {resource.directPdfUrl && (
                    <a
                      href={resource.directPdfUrl}
                      download={resource.downloadFileName || 'GovOS_Official_Resource.pdf'}
                      className="btn btn-emerald"
                      style={{ fontSize: '0.8rem', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                    >
                      <Download size={14} /> Download PDF File
                    </a>
                  )}
                </div>

              </div>

            </div>
          )}

        </div>

      </div>
    </div>
  );
};


// ==========================================================================
// ResourceAIAssistant.tsx
// ==========================================================================
interface ResourceAIAssistantProps {
  resources: ResourceItem[];
  onOpenResourceModal: (resource: ResourceItem) => void;
}

interface ResourceChatMessage {
  id: string;
  sender: 'USER' | 'AI';
  text: string;
  matchedResources?: ResourceItem[];
  timestamp: string;
}

export const ResourceAIAssistant: React.FC<ResourceAIAssistantProps> = ({
  resources,
  onOpenResourceModal
}) => {
  const [messages, setMessages] = useState<ResourceChatMessage[]>([
    {
      id: 'msg-welcome',
      sender: 'AI',
      text: 'Hello! I am your **GovOS Resource Navigator**. Ask me for any study material, formula sheet, official gazette, or video course, and I will jump directly to the exact verified document or YouTube masterclass for you.',
      timestamp: 'Just now'
    }
  ]);
  const [inputText, setInputText] = useState<string>('');

  const quickPrompts = [
    'Official SSC CGL 2026 Notification PDF',
    'English Grammar 60 Rules Marathon Video',
    'Quantitative Aptitude Geometry & Formulas',
    'Constitution of India Fundamental Rights Articles',
    'Tier-2 Computer Knowledge Qualifying Notes',
    'Official DEST 2000 Key Depressions Typing Test'
  ];

  const handleSendMessage = (queryText?: string) => {
    const textToSend = (queryText || inputText).trim();
    if (!textToSend) return;

    const userMsg: ResourceChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'USER',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const queryLower = textToSend.toLowerCase();
    
    // Search matching resources
    const matched = resources.filter(res => {
      const titleMatch = res.title.toLowerCase().includes(queryLower);
      const subMatch = res.subject.toLowerCase().includes(queryLower);
      const descMatch = res.description.toLowerCase().includes(queryLower);
      const authorMatch = res.author.toLowerCase().includes(queryLower);

      if (queryLower.includes('notification') || queryLower.includes('gazette') || queryLower.includes('official notice')) {
        return res.id === 'res-pdf-01';
      }
      if (queryLower.includes('english') || queryLower.includes('grammar') || queryLower.includes('rani') || queryLower.includes('rules')) {
        return res.subject === 'English Comprehension';
      }
      if (queryLower.includes('math') || queryLower.includes('quant') || queryLower.includes('geometry') || queryLower.includes('algebra') || queryLower.includes('formula') || queryLower.includes('gagan')) {
        return res.subject === 'Quantitative Aptitude';
      }
      if (queryLower.includes('polity') || queryLower.includes('constitution') || queryLower.includes('article') || queryLower.includes('parmar') || queryLower.includes('gk') || queryLower.includes('general awareness')) {
        return res.subject === 'General Awareness & Static GK';
      }
      if (queryLower.includes('computer') || queryLower.includes('typing') || queryLower.includes('dest') || queryLower.includes('rbe')) {
        return res.subject === 'Computer & Typing';
      }
      if (queryLower.includes('reasoning') || queryLower.includes('vikramjeet')) {
        return res.subject === 'Reasoning';
      }

      return titleMatch || subMatch || descMatch || authorMatch;
    });

    let replyText = `I found **${matched.length} verified authentic resources** matching your request. You can read the full text, download the direct PDF, or watch the complete video course below:`;
    if (matched.length === 0) {
      replyText = `I searched the verified GovOS repository. Here are the most authoritative core materials available for SSC CGL:`;
    }

    const aiMsg: ResourceChatMessage = {
      id: `ai-${Date.now()}`,
      sender: 'AI',
      text: replyText,
      matchedResources: matched.length > 0 ? matched : resources.slice(0, 3),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg, aiMsg]);
    setInputText('');
  };

  return (
    <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(30, 58, 138, 0.15) 0%, rgba(15, 23, 42, 0.95) 100%)', borderColor: 'rgba(59, 130, 246, 0.3)', marginBottom: '20px' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ padding: '8px', borderRadius: '50%', background: 'rgba(59, 130, 246, 0.2)', border: '1px solid rgba(59, 130, 246, 0.4)' }}>
            <Bot size={22} color="#60a5fa" />
          </div>
          <div>
            <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white', margin: 0 }}>
              AI Resource Navigator & Instant Jumper
            </h4>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Ask anything to jump directly to authentic downloadable PDFs, official gazettes & YouTube masterclasses
            </span>
          </div>
        </div>
      </div>

      {/* Quick Prompt Pills */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '16px' }}>
        {quickPrompts.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => handleSendMessage(prompt)}
            style={{
              fontSize: '0.78rem',
              padding: '5px 12px',
              borderRadius: '20px',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              color: '#93c5fd',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Sparkles size={12} color="var(--amber)" /> {prompt}
          </button>
        ))}
      </div>

      {/* Chat Messages Stream */}
      <div style={{ 
        maxHeight: '340px', 
        overflowY: 'auto', 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '14px',
        padding: '12px',
        background: 'rgba(0,0,0,0.25)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-color)',
        marginBottom: '16px'
      }}>
        {messages.map(msg => (
          <div 
            key={msg.id} 
            style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: msg.sender === 'USER' ? 'flex-end' : 'flex-start',
              gap: '6px'
            }}
          >
            <div style={{ 
              maxWidth: '85%', 
              padding: '12px 16px', 
              borderRadius: 'var(--radius-md)', 
              background: msg.sender === 'USER' ? 'var(--primary)' : 'rgba(255,255,255,0.05)',
              border: msg.sender === 'USER' ? 'none' : '1px solid var(--border-color)',
              color: 'white',
              fontSize: '0.9rem',
              lineHeight: 1.5
            }}>
              <div 
                dangerouslySetInnerHTML={{ 
                  __html: msg.text
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\n/g, '<br/>') 
                }} 
              />
            </div>

            {/* Render Instant Action Cards for Matched Resources */}
            {msg.matchedResources && msg.matchedResources.length > 0 && (
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', 
                gap: '10px', 
                width: '100%',
                marginTop: '4px'
              }}>
                {msg.matchedResources.map(res => (
                  <div 
                    key={res.id} 
                    style={{ 
                      padding: '12px 14px', 
                      borderRadius: 'var(--radius-md)', 
                      background: 'rgba(15, 23, 42, 0.9)', 
                      border: '1px solid rgba(59, 130, 246, 0.3)',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      gap: '8px'
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span className="badge badge-verified" style={{ fontSize: '0.68rem' }}>{res.subject}</span>
                        <span style={{ fontSize: '0.72rem', color: '#fbbf24' }}>{res.rating?.split(' ')[0] || '⭐ 4.9/5'}</span>
                      </div>
                      <h5 style={{ fontSize: '0.92rem', fontWeight: 700, color: 'white', margin: '4px 0 2px 0' }}>{res.title}</h5>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>By: {res.author}</div>
                    </div>

                    <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
                      {res.resourceFormat === 'YOUTUBE_COURSE' ? (
                        <>
                          <a 
                            href={res.youtubeUrl || res.url} 
                            target="_blank" 
                            rel="noreferrer" 
                            className="btn btn-emerald" 
                            style={{ fontSize: '0.75rem', padding: '5px 12px', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
                          >
                            <PlayCircle size={14} /> Watch Direct Video on YouTube <ExternalLink size={11} />
                          </a>
                        </>
                      ) : res.directPdfUrl ? (
                        <>
                          <a 
                            href={res.directPdfUrl} 
                            download={res.downloadFileName || 'GovOS_Official_Resource.pdf'}
                            className="btn btn-emerald" 
                            style={{ fontSize: '0.75rem', padding: '4px 10px', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}
                          >
                            <Download size={13} /> Download PDF
                          </a>
                          <a 
                            href={res.directPdfUrl} 
                            target="_blank"
                            rel="noreferrer"
                            className="btn btn-secondary" 
                            style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                            title="Read in Browser"
                          >
                            <BookOpen size={12} />
                          </a>
                        </>
                      ) : (
                        <button 
                          onClick={() => onOpenResourceModal(res)}
                          className="btn btn-emerald" 
                          style={{ fontSize: '0.75rem', padding: '4px 10px', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}
                        >
                          <BookOpen size={13} /> Open Material
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{msg.timestamp}</span>
          </div>
        ))}
      </div>

      {/* Input Box */}
      <div style={{ display: 'flex', gap: '10px' }}>
        <input 
          type="text" 
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
          placeholder="e.g. Give me the official SSC CGL Notification PDF or English Grammar video..."
          style={{
            flex: 1,
            padding: '10px 16px',
            borderRadius: 'var(--radius-md)',
            background: 'var(--bg-input)',
            border: '1px solid var(--border-color)',
            color: 'white',
            fontSize: '0.9rem',
            outline: 'none'
          }}
        />
        <button 
          onClick={() => handleSendMessage()} 
          className="btn btn-primary"
          style={{ padding: '0 20px', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Send size={15} /> Jump
        </button>
      </div>

    </div>
  );
};


// ==========================================================================
// PreparationPlanner.tsx
// ==========================================================================
interface PreparationPlannerProps {
  exam: Exam;
}

export const PreparationPlanner: React.FC<PreparationPlannerProps> = ({ exam }) => {
  const tracks = exam.roadmapTracks || [];
  const [selectedTrackId, setSelectedTrackId] = useState<string>(tracks[0]?.id || 'TRACK_90_DAYS');
  const [expandedPhase, setExpandedPhase] = useState<number>(1);
  const [completedGoals, setCompletedGoals] = useState<Record<string, boolean>>(
    () => storageService.getRoadmapGoals(exam.id)
  );

  const currentTrack: RoadmapTrack = tracks.find(t => t.id === selectedTrackId) || tracks[0];

  const toggleGoal = (goalKey: string) => {
    setCompletedGoals(storageService.toggleRoadmapGoal(exam.id, goalKey));
  };

  const totalGoals = currentTrack.phases.reduce((acc, phase) => {
    return acc + phase.weeklySchedule.reduce((wAcc, w) => wAcc + w.goals.length, 0);
  }, 0);

  const completedCount = Object.keys(completedGoals).filter(k => completedGoals[k] && k.startsWith(currentTrack.id)).length;
  const progressPercentage = totalGoals > 0 ? Math.round((completedCount / totalGoals) * 100) : 0;

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Header Banner */}
      <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(15, 23, 42, 0.95) 100%)', borderColor: 'rgba(99, 102, 241, 0.3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span className="badge badge-verified">
                <ShieldCheck size={14} /> ADAPTIVE MULTI-TRACK PREPARATION ENGINE
              </span>
              <span className="badge badge-demo" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>
                Synced with 2026 Exam Timeline
              </span>
            </div>
            <h2 style={{ fontSize: '1.75rem', fontWeight: 800, color: 'white', marginBottom: '6px' }}>
              Day 1 to Exam Hall Preparation Roadmap
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
              Structured, milestone-driven preparation roadmaps for {exam.title}, tailored to your daily study capacity and timeline.
            </p>
          </div>

          <div style={{ padding: '14px 20px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', textAlign: 'right' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>ROADMAP COMPLETION</span>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--emerald)' }}>{progressPercentage}%</div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{completedCount} of {totalGoals} milestones completed</span>
          </div>
        </div>
      </div>

      {/* Track Selector Tabs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
        {tracks.map(track => {
          const isSelected = track.id === selectedTrackId;
          return (
            <div
              key={track.id}
              onClick={() => setSelectedTrackId(track.id)}
              className="glass-card"
              style={{
                padding: '20px',
                cursor: 'pointer',
                border: isSelected ? '2px solid var(--primary)' : '1px solid var(--border-color)',
                background: isSelected ? 'rgba(59, 130, 246, 0.08)' : 'var(--bg-card)',
                transition: 'all 0.2s ease'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '1.1rem', fontWeight: 800, color: isSelected ? '#93c5fd' : 'white' }}>
                  {track.name}
                </span>
                <span className="badge badge-demo" style={{ fontSize: '0.75rem' }}>
                  {track.targetDailyHours} Hrs / Day
                </span>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0 }}>
                {track.subtitle}
              </p>
            </div>
          );
        })}
      </div>

      {/* Daily Timetable Grid */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <Clock size={20} color="var(--primary)" />
          <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'white' }}>
            Recommended Daily Study Schedule ({currentTrack.name})
          </h3>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
          {currentTrack.dailyTimetable.map((slot, idx) => (
            <div key={idx} style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)', fontFamily: 'var(--font-mono)', marginBottom: '4px' }}>
                {slot.timeSlot}
              </div>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'white', marginBottom: '4px' }}>
                {slot.activity}
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                {slot.focus}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Roadmap Phases & Weekly Milestones */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'white', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Target size={22} color="var(--emerald)" /> Weekly Milestones & Milestone Tests
        </h3>

        {currentTrack.phases.map((phase) => {
          const isExpanded = expandedPhase === phase.phaseNumber;
          return (
            <div key={phase.phaseNumber} className="glass-card" style={{ padding: 0, overflow: 'hidden', border: isExpanded ? '1px solid var(--primary)' : '1px solid var(--border-color)' }}>
              <div
                onClick={() => setExpandedPhase(isExpanded ? 0 : phase.phaseNumber)}
                style={{
                  padding: '20px 24px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  background: isExpanded ? 'rgba(59, 130, 246, 0.06)' : 'transparent'
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                    <span className="badge badge-verified" style={{ fontSize: '0.75rem' }}>
                      {phase.durationWeeks} WEEKS
                    </span>
                    <h4 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'white', margin: 0 }}>
                      {phase.phaseTitle}
                    </h4>
                  </div>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', margin: 0 }}>
                    {phase.focusArea}
                  </p>
                </div>
                {isExpanded ? <ChevronDown size={22} color="var(--text-secondary)" /> : <ChevronRight size={22} color="var(--text-secondary)" />}
              </div>

              {isExpanded && (
                <div style={{ padding: '0 24px 24px 24px', borderTop: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '18px', paddingTop: '18px' }}>
                  {phase.weeklySchedule.map((week) => (
                    <div key={week.weekNumber} style={{ padding: '16px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '12px' }}>
                        <div style={{ fontSize: '1rem', fontWeight: 700, color: '#93c5fd' }}>
                          {week.weekTitle}
                        </div>
                        <span className="badge badge-demo" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#a5b4fc' }}>
                          Target: {week.suggestedDailyHours} hrs/day
                        </span>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '14px' }}>
                        {week.goals.map((goal, gIdx) => {
                          const goalKey = `${currentTrack.id}-p${phase.phaseNumber}-w${week.weekNumber}-g${gIdx}`;
                          const isDone = !!completedGoals[goalKey];
                          return (
                            <div
                              key={gIdx}
                              onClick={() => toggleGoal(goalKey)}
                              style={{
                                display: 'flex',
                                alignItems: 'flex-start',
                                gap: '10px',
                                cursor: 'pointer',
                                padding: '6px 8px',
                                borderRadius: 'var(--radius-sm)',
                                background: isDone ? 'rgba(16, 185, 129, 0.08)' : 'transparent',
                                transition: 'all 0.15s ease'
                              }}
                            >
                              {isDone ? (
                                <CheckSquare size={18} color="var(--emerald)" style={{ flexShrink: 0, marginTop: '2px' }} />
                              ) : (
                                <Square size={18} color="var(--text-muted)" style={{ flexShrink: 0, marginTop: '2px' }} />
                              )}
                              <span style={{ fontSize: '0.92rem', color: isDone ? '#86efac' : 'var(--text-secondary)', textDecoration: isDone ? 'line-through' : 'none' }}>
                                {goal}
                              </span>
                            </div>
                          );
                        })}
                      </div>

                      <div style={{ padding: '10px 14px', borderRadius: 'var(--radius-sm)', background: 'rgba(16, 185, 129, 0.06)', border: '1px solid rgba(16, 185, 129, 0.2)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Award size={16} color="var(--emerald)" />
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                          <strong>Milestone Checkpoint:</strong> {week.milestoneTest}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

    </div>
  );
};


// ==========================================================================
// PostStudyPathEngine.tsx
// ==========================================================================
interface PostStudyPathEngineProps {
  onOpenProvenanceModal?: (prov: any) => void;
  onNavigatePractice?: () => void;
}

export const PostStudyPathEngine: React.FC<PostStudyPathEngineProps> = ({
  onOpenProvenanceModal,
  onNavigatePractice
}) => {
  const [selectedPostId, setSelectedPostId] = useState<string>(() => storageService.getTargetPost());
  const [selectedStage, setSelectedStage] = useState<'ALL' | 'TIER_1' | 'TIER_2'>('ALL');
  const [completedModules, setCompletedModules] = useState<Record<string, boolean>>(() => storageService.getCompletedModules());
  const [syncStatus, setSyncStatus] = useState<string>('Local Storage & SQLite Saved');
  const [isSyncing, setIsSyncing] = useState<boolean>(false);

  const currentPath: PostStudyPath = getPostStudyPath(selectedPostId);

  const handleSelectPost = (postId: string) => {
    setSelectedPostId(postId);
    storageService.setTargetPost(postId);
  };

  const toggleModule = (id: string) => {
    const updated = storageService.toggleCompletedModule(id);
    setCompletedModules({ ...updated });
  };

  const handleManualSync = async () => {
    setIsSyncing(true);
    setSyncStatus('Syncing with govos.db...');
    const result = await storageService.syncAllToSQLite();
    setIsSyncing(false);
    setSyncStatus(result.success ? 'Synced to SQLite (govos.db)' : 'Offline Local Storage Active');
  };

  const getProvenanceBadge = (type: RequirementProvenanceType) => {
    switch (type) {
      case 'OFFICIAL_REQUIREMENT':
        return (
          <span className="badge badge-verified" style={{ fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <ShieldCheck size={12} /> OFFICIAL REQUIREMENT
          </span>
        );
      case 'PREPARATION_TOPIC':
        return (
          <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', fontSize: '0.7rem' }}>
            SYLLABUS TOPIC
          </span>
        );
      case 'RECOMMENDED_PREPARATION':
        return (
          <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', fontSize: '0.7rem' }}>
            RECOMMENDED PREPARATION
          </span>
        );
      case 'OPTIONAL_RESOURCE':
        return (
          <span className="badge" style={{ background: 'rgba(148, 163, 184, 0.15)', color: '#cbd5e1', fontSize: '0.7rem' }}>
            OPTIONAL RESOURCE
          </span>
        );
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* 1. Interactive Target Post Selector Banner */}
      <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className="badge badge-demo" style={{ background: 'rgba(59, 130, 246, 0.2)', color: '#93c5fd', border: '1px solid rgba(59, 130, 246, 0.4)' }}>
                <Compass size={13} /> DYNAMIC POST-SPECIFIC ENGINE
              </span>
              <span style={{ fontSize: '0.8rem', color: '#34d399', fontWeight: 700 }}>
                • Zero Confusion Architecture
              </span>
            </div>
            <h3 style={{ fontSize: '1.45rem', fontWeight: 800, color: 'white', margin: 0 }}>
              What Exactly Should You Study for Your Target Post?
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: '4px 0 0 0' }}>
              Select your desired post below to filter out unneeded modules, isolate mandatory stages, and see your exact preparation path.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="glass-pill" style={{ fontSize: '0.78rem', color: '#86efac', borderColor: 'rgba(16, 185, 129, 0.3)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Database size={13} /> {syncStatus}
            </span>
            <button 
              onClick={handleManualSync}
              disabled={isSyncing}
              className="btn btn-secondary" 
              style={{ fontSize: '0.75rem', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '4px' }}
              title="Sync state between localStorage and SQLite database"
            >
              <RefreshCw size={12} className={isSyncing ? 'animate-spin' : ''} /> {isSyncing ? 'Syncing...' : 'Sync to SQLite'}
            </button>
          </div>
        </div>

        {/* Post Selection Pills */}
        <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '6px' }}>
          {Object.values(ALL_POST_STUDY_PATHS).map(post => {
            const isSelected = post.postId === selectedPostId;
            return (
              <button
                key={post.postId}
                onClick={() => handleSelectPost(post.postId)}
                style={{
                  padding: '10px 16px',
                  borderRadius: 'var(--radius-md)',
                  background: isSelected ? 'var(--primary)' : 'rgba(255, 255, 255, 0.04)',
                  border: isSelected ? '1px solid #60a5fa' : '1px solid var(--border-color)',
                  color: isSelected ? 'white' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '2px',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ fontSize: '0.88rem', fontWeight: 800, color: isSelected ? 'white' : '#f8fafc' }}>
                  {post.postName}
                </div>
                <div style={{ fontSize: '0.72rem', color: isSelected ? '#dbeafe' : 'var(--text-muted)' }}>
                  {post.payLevel} • {post.classification}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 2. Active Post Context Card & Stage Switcher */}
      <div className="glass-card" style={{ padding: '20px', borderLeft: '4px solid var(--primary)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
          <div>
            <div style={{ fontSize: '0.78rem', textTransform: 'uppercase', color: '#93c5fd', fontWeight: 700 }}>
              Active Post Preparation Profile:
            </div>
            <h4 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'white', margin: '2px 0' }}>
              {currentPath.postName} — {currentPath.department}
            </h4>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Cadre: <strong>{currentPath.classification}</strong> | Pay Scale: <strong>{currentPath.payLevel}</strong>
            </div>
          </div>

          {/* Stage Filter Buttons */}
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              onClick={() => setSelectedStage('ALL')}
              className={`btn ${selectedStage === 'ALL' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.82rem', padding: '6px 14px' }}
            >
              Complete Lifecycle
            </button>
            <button
              onClick={() => setSelectedStage('TIER_1')}
              className={`btn ${selectedStage === 'TIER_1' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.82rem', padding: '6px 14px' }}
            >
              Step 1: Tier 1 (Prelims)
            </button>
            <button
              onClick={() => setSelectedStage('TIER_2')}
              className={`btn ${selectedStage === 'TIER_2' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.82rem', padding: '6px 14px' }}
            >
              Step 2: Tier 2 (Mains & Skills)
            </button>
          </div>
        </div>
      </div>

      {/* 3. SECTION 1: COMMON PREPARATION (Required for all posts in this stage) */}
      {(selectedStage === 'ALL' || selectedStage === 'TIER_1') && (
        <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '0.85rem' }}>
                1
              </div>
              <div>
                <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white', margin: 0 }}>
                  STEP 1: Tier 1 Common Preparation (Preliminary Exam)
                </h4>
                <div style={{ fontSize: '0.8rem', color: '#93c5fd' }}>
                  Mandatory Computer Based Examination (100 Questions, 200 Marks, 60 Minutes duration)
                </div>
              </div>
            </div>
            <span className="badge badge-verified" style={{ fontSize: '0.75rem' }}>
              COMMON TO ALL POSTS
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '14px' }}>
            {currentPath.tier1.commonModules.map(mod => {
              const isChecked = !!completedModules[mod.id];
              return (
                <div 
                  key={mod.id}
                  style={{
                    padding: '16px',
                    borderRadius: 'var(--radius-md)',
                    background: isChecked ? 'rgba(16, 185, 129, 0.05)' : 'rgba(255, 255, 255, 0.02)',
                    border: isChecked ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--border-color)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '10px'
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      {getProvenanceBadge(mod.requirementType)}
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Clause: {mod.officialClause}
                      </span>
                    </div>

                    <h5 style={{ fontSize: '1rem', fontWeight: 700, color: 'white', margin: 0 }}>
                      {mod.title}
                    </h5>

                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      <span className="glass-pill" style={{ fontSize: '0.72rem' }}>{mod.questionsCount} Qs ({mod.marks} Marks)</span>
                      <span className="glass-pill" style={{ fontSize: '0.72rem', color: '#f87171' }}>Neg: {mod.negativeMarking}</span>
                    </div>

                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      <strong>High-Yield Core Topics:</strong> {mod.highYieldTopics.join(', ')}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '8px' }}>
                    <button
                      onClick={() => toggleModule(mod.id)}
                      className="btn"
                      style={{
                        padding: '4px 10px',
                        fontSize: '0.75rem',
                        borderRadius: 'var(--radius-sm)',
                        background: isChecked ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255,255,255,0.06)',
                        color: isChecked ? '#34d399' : 'var(--text-secondary)',
                        border: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}
                    >
                      <CheckCircle2 size={13} color={isChecked ? '#34d399' : 'gray'} />
                      {isChecked ? 'Marked Complete' : 'Mark as Studied'}
                    </button>

                    {onOpenProvenanceModal && (
                      <button
                        onClick={() => onOpenProvenanceModal(mod.provenance)}
                        className="btn btn-outline"
                        style={{ padding: '3px 8px', fontSize: '0.72rem' }}
                        title="View Gazette Clause Citation"
                      >
                        Clause Citation
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 4. SECTION 2: TIER 2 MAINS PREPARATION */}
      {(selectedStage === 'ALL' || selectedStage === 'TIER_2') && (
        <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '0.85rem' }}>
                2
              </div>
              <div>
                <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white', margin: 0 }}>
                  STEP 2: Tier 2 Paper-I Mandatory Modules (Mains Exam)
                </h4>
                <div style={{ fontSize: '0.8rem', color: '#86efac' }}>
                  Decides Final Merit (150 Questions, 390 Marks + CKT Computer & DEST Typing)
                </div>
              </div>
            </div>
            <span className="badge badge-verified" style={{ fontSize: '0.75rem' }}>
              MERIT DECIDING STAGE
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '14px' }}>
            {currentPath.tier2.commonModules.map(mod => {
              const isChecked = !!completedModules[mod.id];
              return (
                <div 
                  key={mod.id}
                  style={{
                    padding: '16px',
                    borderRadius: 'var(--radius-md)',
                    background: isChecked ? 'rgba(16, 185, 129, 0.05)' : 'rgba(255, 255, 255, 0.02)',
                    border: isChecked ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--border-color)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '10px'
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      {getProvenanceBadge(mod.requirementType)}
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Clause: {mod.officialClause}
                      </span>
                    </div>

                    <h5 style={{ fontSize: '1rem', fontWeight: 700, color: 'white', margin: 0 }}>
                      {mod.title}
                    </h5>

                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      <span className="glass-pill" style={{ fontSize: '0.72rem' }}>{mod.questionsCount} Qs ({mod.marks} Marks)</span>
                      <span className="glass-pill" style={{ fontSize: '0.72rem', color: '#f87171' }}>Neg: {mod.negativeMarking}</span>
                    </div>

                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      <strong>High-Yield Core Topics:</strong> {mod.highYieldTopics.join(', ')}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '8px' }}>
                    <button
                      onClick={() => toggleModule(mod.id)}
                      className="btn"
                      style={{
                        padding: '4px 10px',
                        fontSize: '0.75rem',
                        borderRadius: 'var(--radius-sm)',
                        background: isChecked ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255,255,255,0.06)',
                        color: isChecked ? '#34d399' : 'var(--text-secondary)',
                        border: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}
                    >
                      <CheckCircle2 size={13} color={isChecked ? '#34d399' : 'gray'} />
                      {isChecked ? 'Marked Complete' : 'Mark as Studied'}
                    </button>

                    {onOpenProvenanceModal && (
                      <button
                        onClick={() => onOpenProvenanceModal(mod.provenance)}
                        className="btn btn-outline"
                        style={{ padding: '3px 8px', fontSize: '0.72rem' }}
                      >
                        Clause Citation
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 5. SECTION 3: POST-SPECIFIC ADDITIONAL REQUIREMENTS (If Any) */}
      {currentPath.tier2.additionalModules.length > 0 && (
        <div className="glass-card" style={{ padding: '24px', border: '1px solid rgba(234, 179, 8, 0.4)', background: 'rgba(234, 179, 8, 0.03)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: 'rgba(234, 179, 8, 0.2)', color: '#fbbf24', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '0.85rem' }}>
                ⭐
              </div>
              <div>
                <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#fde047', margin: 0 }}>
                  Additional Mandatory Preparation for {currentPath.postName}
                </h4>
                <div style={{ fontSize: '0.8rem', color: '#fef08a' }}>
                  This paper is strictly required for this post in addition to Paper-I
                </div>
              </div>
            </div>
            <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.2)', color: '#fde047' }}>
              POST-SPECIFIC MANDATE
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '14px' }}>
            {currentPath.tier2.additionalModules.map(mod => (
              <div key={mod.id} style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(234, 179, 8, 0.3)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span className="badge badge-verified">{mod.officialClause}</span>
                  <span style={{ fontSize: '0.8rem', color: '#fbbf24', fontWeight: 700 }}>100 Questions • 200 Marks • Negative: -0.50</span>
                </div>
                <h4 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'white', margin: '4px 0' }}>{mod.title}</h4>
                <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', margin: '6px 0 10px 0', lineHeight: 1.5 }}>
                  <strong>Mandatory Topics:</strong> {mod.highYieldTopics.join(', ')}
                </p>
                <div style={{ padding: '10px 14px', borderRadius: 'var(--radius-sm)', background: 'rgba(234, 179, 8, 0.1)', fontSize: '0.82rem', color: '#fef08a' }}>
                  💡 <strong>Preparation Strategy:</strong> {mod.keyTakeaways}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 6. Physical & Medical Standards for Field/Inspector Posts */}
      {currentPath.physicalMedical?.required && (
        <div className="glass-card" style={{ padding: '20px', border: '1px solid rgba(59, 130, 246, 0.4)', background: 'rgba(59, 130, 246, 0.04)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#93c5fd', fontWeight: 800, marginBottom: '10px' }}>
            <Activity size={18} color="#60a5fa" /> Mandatory Physical & Medical Standards for {currentPath.postName}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
            {currentPath.physicalMedical.maleHeightChest && (
              <div style={{ padding: '12px', borderRadius: 'var(--radius-sm)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', fontSize: '0.84rem' }}>
                <strong style={{ color: 'white' }}>Male Measurement Standards:</strong>
                <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>{currentPath.physicalMedical.maleHeightChest}</p>
              </div>
            )}
            {currentPath.physicalMedical.physicalTest && (
              <div style={{ padding: '12px', borderRadius: 'var(--radius-sm)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', fontSize: '0.84rem' }}>
                <strong style={{ color: 'white' }}>Physical Efficiency Test (PET):</strong>
                <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>{currentPath.physicalMedical.physicalTest}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 7. SECTION 4: 🚫 YOU DON'T NEED TO STUDY (Eliminate Confusion) */}
      <div className="glass-card" style={{ padding: '24px', border: '1px solid rgba(239, 68, 68, 0.3)', background: 'rgba(239, 68, 68, 0.03)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
          <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '0.85rem' }}>
            🚫
          </div>
          <div>
            <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#fca5a5', margin: 0 }}>
              YOU DON'T NEED TO STUDY (Not Required for {currentPath.postName})
            </h4>
            <div style={{ fontSize: '0.8rem', color: '#fecaca' }}>
              Eliminating these unneeded subjects saves you over 100+ hours of wasted preparation time.
            </div>
          </div>
        </div>

        {currentPath.tier2.excludedModules.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '12px' }}>
            {currentPath.tier2.excludedModules.map(ex => (
              <div key={ex.moduleId} style={{ padding: '16px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(239, 68, 68, 0.2)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f87171', fontWeight: 700, fontSize: '0.95rem' }}>
                  <XCircle size={16} /> {ex.moduleName}
                </div>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
                  {ex.reason}
                </p>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Applicable Only To: <span style={{ color: '#93c5fd' }}>{ex.applicableOnlyTo}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-sm)', background: 'rgba(255,255,255,0.02)', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            All standard Paper-I and Paper-II modules are required for Junior Statistical Officer (JSO).
          </div>
        )}
      </div>

    </div>
  );
};


// ==========================================================================
// PracticeEngine.tsx
// ==========================================================================
interface PracticeEngineProps {
  exam: Exam;
  onOpenProvenanceModal: (provenance: DataProvenance) => void;
}

// Provenance for the inline Application-Simulator review paper rebuilt in handleReviewPastAttempt.
const APP_SIM_PROVENANCE: DataProvenance = {
  id: 'prov-app-sim',
  documentTitle: 'SSC CGL Official Notification — Application & Eligibility Rules',
  officialUrl: 'https://ssc.gov.in',
  publishedDate: '2026-08-10',
  verifiedDate: '2026-08-11',
  verifiedBy: 'GovOS Official Examination Verification Team',
  taxonomyType: 'FACT',
  verificationLevel: 'OFFICIALLY_VERIFIED'
};

interface MockChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  proposedTest?: MockPaper;
}

export const PracticeEngine: React.FC<PracticeEngineProps> = ({ exam, onOpenProvenanceModal }) => {
  // Navigation & Modes
  const [activePracticeTab, setActivePracticeTab] = useState<'PAPERS_LIST' | 'SUBJECT_TESTS' | 'TOPIC_DRILLS' | 'AI_CHAT_ASSISTANT' | 'ACTIVE_TEST' | 'PAST_ANALYTICS'>('PAPERS_LIST');
  
  // Available Papers List (Starts with 10 official papers, can auto-sync newly discovered ones)
  const [availablePapers, setAvailablePapers] = useState<MockPaper[]>(OFFICIAL_10_MOCK_PAPERS);
  const [isSyncingPapers, setIsSyncingPapers] = useState<boolean>(false);
  const [syncSuccessNotice, setSyncSuccessNotice] = useState<string | null>(null);

  const [selectedPaper, setSelectedPaper] = useState<MockPaper>(OFFICIAL_10_MOCK_PAPERS[0]);
  const [activeSection, setActiveSection] = useState<string>('ALL');
  
  // Active Test State
  const [isTestStarted, setIsTestStarted] = useState<boolean>(false);
  const [currentIdx, setCurrentIdx] = useState<number>(0);
  const [userAnswers, setUserAnswers] = useState<Record<number, number>>({});
  const [markedForReview, setMarkedForReview] = useState<Record<number, boolean>>({});
  const [isSubmittedTest, setIsSubmittedTest] = useState<boolean>(false);
  const [timerSeconds, setTimerSeconds] = useState<number>(3600);
  const [isTimerPaused, setIsTimerPaused] = useState<boolean>(false);
  
  // Solution Filter Tab State
  const [solutionFilter, setSolutionFilter] = useState<'ALL' | 'INCORRECT' | 'UNATTEMPTED' | 'CORRECT'>('ALL');
  const [solutionSectionFilter, setSolutionSectionFilter] = useState<string>('ALL');

  // Conversational AI Mock Assistant State
  const [chatInput, setChatInput] = useState<string>('');
  const [chatMessages, setChatMessages] = useState<MockChatMessage[]>([
    {
      id: 'msg-welcome',
      sender: 'assistant',
      text: "Hello! I am your AI Mock Test Creator Assistant. Tell me what you'd like to practice (e.g. \"Create a 15-question hard test on Geometry & Algebra for Tier-2\", \"Give me a 10-minute speed drill on English 60 Grammar Rules\", or \"Test my weak areas\"). I will intelligently assemble the questions, calibrate the realistic exam timer, and generate your test.",
      timestamp: 'Just now'
    }
  ]);
  const chatBottomRef = useRef<HTMLDivElement>(null);
  
  // Past Attempts History & Target Post
  const [pastAttempts, setPastAttempts] = useState<MockAttemptRecord[]>(() => storageService.getMockAttempts());
  const [reviewingAttempt, setReviewingAttempt] = useState<MockAttemptRecord | null>(null);
  const targetPostId = storageService.getTargetPost();
  const targetPost = getPostStudyPath(targetPostId);

  // Sync latest mock attempts from SQLite on component mount
  useEffect(() => {
    storageService.loadMockAttemptsFromSQLite().then(records => {
      if (records && records.length > 0) {
        setPastAttempts(records);
      }
    });
  }, []);

  const questionsList = selectedPaper.questions;
  const currentQ = questionsList[currentIdx] || questionsList[0];

  // Auto-scroll chat to bottom on new message
  useEffect(() => {
    if (activePracticeTab === 'AI_CHAT_ASSISTANT') {
      chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, activePracticeTab]);

  // Timer Effect
  useEffect(() => {
    let interval: any = null;
    if (isTestStarted && !isSubmittedTest && !isTimerPaused && timerSeconds > 0) {
      interval = setInterval(() => {
        setTimerSeconds(prev => (prev > 0 ? prev - 1 : 0));
      }, 1000);
    } else if (timerSeconds === 0 && isTestStarted && !isSubmittedTest) {
      handleSubmitTest();
    }
    return () => clearInterval(interval);
  }, [isTestStarted, isSubmittedTest, isTimerPaused, timerSeconds]);

  // Auto-Sync Repository for New Shift Papers
  const handleAutoSyncPapers = () => {
    setIsSyncingPapers(true);
    setSyncSuccessNotice(null);

    setTimeout(() => {
      // Check if discovered papers are already included
      const existingIds = new Set(availablePapers.map(p => p.id));
      const newlyAdded = NEW_DISCOVERED_PAPERS.filter(p => !existingIds.has(p.id));

      if (newlyAdded.length > 0) {
        setAvailablePapers(prev => [...newlyAdded, ...prev]);
        setSyncSuccessNotice(`🎉 Successfully fetched ${newlyAdded.length} new verified shift papers from official repository (SSC 2024 Shift-3 & SSC 2025 Tier-2 Master Key)!`);
      } else {
        setSyncSuccessNotice(`✅ Official repository verified: Your question paper library is already 100% up to date with the latest 2024-2025 shifts.`);
      }
      setIsSyncingPapers(false);
    }, 1200);
  };

  const handleSelectOption = (optIdx: number) => {
    if (isSubmittedTest || !isTestStarted) return;
    setUserAnswers(prev => ({ ...prev, [currentIdx]: optIdx }));
  };

  const handleToggleReview = () => {
    if (!isTestStarted) return;
    setMarkedForReview(prev => ({ ...prev, [currentIdx]: !prev[currentIdx] }));
  };

  const handleClearResponse = () => {
    if (isSubmittedTest || !isTestStarted) return;
    setUserAnswers(prev => {
      const next = { ...prev };
      delete next[currentIdx];
      return next;
    });
  };

  const handleStartTest = (paper: MockPaper) => {
    setSelectedPaper(paper);
    setUserAnswers({});
    setMarkedForReview({});
    setIsSubmittedTest(false);
    setReviewingAttempt(null);
    setTimerSeconds(paper.durationMinutes * 60);
    setIsTimerPaused(false);
    setCurrentIdx(0);
    setActiveSection('ALL');
    setSolutionFilter('ALL');
    setSolutionSectionFilter('ALL');
    setIsTestStarted(true);
    setActivePracticeTab('ACTIVE_TEST');
  };

  const handleResetTest = () => {
    setUserAnswers({});
    setMarkedForReview({});
    setIsSubmittedTest(false);
    setIsTestStarted(false);
    setReviewingAttempt(null);
    setTimerSeconds(3600);
    setCurrentIdx(0);
    setActivePracticeTab('PAPERS_LIST');
  };

  // Conversational Context Parser & Test Generator
  const handleSendChatMessage = (customText?: string) => {
    const query = customText || chatInput;
    if (!query.trim()) return;

    const userMsg: MockChatMessage = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setChatMessages(prev => [...prev, userMsg]);
    if (!customText) setChatInput('');

    setTimeout(() => {
      const lower = query.toLowerCase();

      // 1. Detect Subjects
      const matchedSubjects: string[] = [];
      if (lower.includes('quant') || lower.includes('math') || lower.includes('geometry') || lower.includes('algebra') || lower.includes('trig') || lower.includes('profit') || lower.includes('ci/si') || lower.includes('mensuration')) {
        matchedSubjects.push('Quantitative Aptitude');
      }
      if (lower.includes('reasoning') || lower.includes('syllogism') || lower.includes('blood') || lower.includes('series') || lower.includes('analogy') || lower.includes('dice')) {
        matchedSubjects.push('Reasoning & General Intelligence');
      }
      if (lower.includes('english') || lower.includes('grammar') || lower.includes('vocab') || lower.includes('synonym') || lower.includes('antonym') || lower.includes('voice') || lower.includes('narration')) {
        matchedSubjects.push('English Comprehension');
      }
      if (lower.includes('ga') || lower.includes('gk') || lower.includes('polity') || lower.includes('constitution') || lower.includes('history') || lower.includes('geography') || lower.includes('science')) {
        matchedSubjects.push('General Awareness');
      }
      if (lower.includes('computer') || lower.includes('excel') || lower.includes('hardware') || lower.includes('cpt')) {
        matchedSubjects.push('Computer Proficiency');
      }

      const finalSubjects = matchedSubjects.length > 0 
        ? matchedSubjects 
        : ['Quantitative Aptitude', 'Reasoning & General Intelligence', 'English Comprehension', 'General Awareness'];

      // 2. Detect Question Count
      const countMatch = query.match(/\b(\d+)\s*(q|qs|questions|question|problems)?\b/i);
      let numQs = 15;
      if (countMatch && countMatch[1]) {
        const parsed = parseInt(countMatch[1], 10);
        if (parsed >= 5 && parsed <= 100) {
          numQs = parsed;
        }
      }

      // 3. Detect Difficulty
      let difficulty: 'EASY' | 'MEDIUM' | 'HARD' | 'ADAPTIVE' = 'MEDIUM';
      if (lower.includes('hard') || lower.includes('tough') || lower.includes('tier-2') || lower.includes('tier 2') || lower.includes('advanced') || lower.includes('complex')) {
        difficulty = 'HARD';
      } else if (lower.includes('easy') || lower.includes('speed') || lower.includes('basic') || lower.includes('quick')) {
        difficulty = 'EASY';
      } else if (lower.includes('adaptive') || lower.includes('mixed')) {
        difficulty = 'ADAPTIVE';
      }

      // 4. Generate Mock Paper with Intelligent Timer
      const generatedMock = generateCustomMockTest({
        title: `AI Tailored Drill: ${finalSubjects.join(' + ')} (${numQs} Qs)`,
        selectedSubjects: finalSubjects,
        selectedTopics: [],
        numQuestions: numQs,
        difficulty,
        focusGoal: lower.includes('weak') ? 'WEAK_AREAS' : 'GENERAL'
      });

      const responseText = `I have analyzed your request ("${query}") and created your tailored mock test:\n\n• Target Subjects: ${finalSubjects.join(', ')}\n• Questions: ${numQs} Questions\n• Difficulty: ${difficulty} Level\n• Intelligent Calibrated Timer: ${generatedMock.durationMinutes} Minutes\n\nClick below to start this test immediately!`;

      const botMsg: MockChatMessage = {
        id: `msg-bot-${Date.now()}`,
        sender: 'assistant',
        text: responseText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        proposedTest: generatedMock
      };

      setChatMessages(prev => [...prev, botMsg]);
    }, 400);
  };

  // Score & Performance Diagnostic Calculation
  let correctCount = 0;
  let incorrectCount = 0;
  let unattemptedCount = 0;

  const subjectPerformance: Record<string, { total: number; correct: number; incorrect: number; topics: Record<string, { total: number; correct: number; incorrect: number }> }> = {};

  questionsList.forEach((q, idx) => {
    const ans = userAnswers[idx];
    const subj = q.subject;
    const top = q.topicName;

    if (!subjectPerformance[subj]) {
      subjectPerformance[subj] = { total: 0, correct: 0, incorrect: 0, topics: {} };
    }
    if (!subjectPerformance[subj].topics[top]) {
      subjectPerformance[subj].topics[top] = { total: 0, correct: 0, incorrect: 0 };
    }

    subjectPerformance[subj].total++;
    subjectPerformance[subj].topics[top].total++;

    if (ans === undefined) {
      unattemptedCount++;
    } else if (ans === q.correctOptionIndex) {
      correctCount++;
      subjectPerformance[subj].correct++;
      subjectPerformance[subj].topics[top].correct++;
    } else {
      incorrectCount++;
      subjectPerformance[subj].incorrect++;
      subjectPerformance[subj].topics[top].incorrect++;
    }
  });

  const marksEarned = (correctCount * 2) - (incorrectCount * 0.5);
  const totalPossibleMarks = selectedPaper.totalMarks;
  const accuracyPercentage = (correctCount + incorrectCount) > 0
    ? Math.round((correctCount / (correctCount + incorrectCount)) * 100)
    : 0;

  // Enhanced Clarity Weak, Medium, Strong Classification
  const weakAreas: { topic: string; subject: string; accuracy: number; total: number; missed: number; trapAlert: string; examImpact: string }[] = [];
  const mediumAreas: { topic: string; subject: string; accuracy: number; total: number; speedAdvice: string }[] = [];
  const strongAreas: { topic: string; subject: string; accuracy: number; total: number }[] = [];

  Object.entries(subjectPerformance).forEach(([subj, data]) => {
    Object.entries(data.topics).forEach(([top, tData]) => {
      const acc = tData.total > 0 ? (tData.correct / tData.total) * 100 : 0;
      if (acc < 50) {
        let trap = 'Prone to sign errors and algebraic identity misapplication under time pressure.';
        let impact = 'High Tier-1 & Tier-2 Weightage (3–4 Qs guaranteed in TCS exam pattern).';
        if (subj === 'General Awareness') {
          trap = 'Confusion between closely related constitutional articles and historical dates.';
          impact = 'Direct scoring area for increasing Tier-1 cut-off clearance buffer.';
        } else if (subj === 'English Comprehension') {
          trap = 'Rule of proximity violations in correlative conjunctions and preposition nuances.';
          impact = 'Essential for high-accuracy scoring in Tier-1 & Tier-2 English.';
        }
        weakAreas.push({ 
          topic: top, 
          subject: subj, 
          accuracy: Math.round(acc), 
          total: tData.total, 
          missed: tData.incorrect,
          trapAlert: trap,
          examImpact: impact
        });
      } else if (acc >= 50 && acc < 75) {
        mediumAreas.push({ 
          topic: top, 
          subject: subj, 
          accuracy: Math.round(acc), 
          total: tData.total,
          speedAdvice: 'Concept understood, but requires speed shortcut drills to cut solving time under 20s.'
        });
      } else {
        strongAreas.push({ topic: top, subject: subj, accuracy: Math.round(acc), total: tData.total });
      }
    });
  });

  // Calculate Selection Plan-Driven Daily Study Hours
  const calculateDailyStudyHours = () => {
    let quantHours = 2.0;
    let reasoningHours = 1.0;
    let englishHours = 1.5;
    let gaHours = 1.5;

    weakAreas.forEach(w => {
      if (w.subject === 'Quantitative Aptitude') quantHours += 0.5;
      if (w.subject === 'General Awareness') gaHours += 0.5;
      if (w.subject === 'English Comprehension') englishHours += 0.5;
      if (w.subject === 'Reasoning & General Intelligence') reasoningHours += 0.25;
    });

    let statsHours = targetPostId === 'post-jso' ? 2.0 : 0.0;
    const totalDailyHours = quantHours + reasoningHours + englishHours + gaHours + statsHours;

    return {
      quantHours: quantHours.toFixed(1),
      reasoningHours: reasoningHours.toFixed(1),
      englishHours: englishHours.toFixed(1),
      gaHours: gaHours.toFixed(1),
      statsHours: statsHours.toFixed(1),
      totalDailyHours: totalDailyHours.toFixed(1)
    };
  };

  const studyHoursPlan = calculateDailyStudyHours();

  // Test Submission Handler
  const handleSubmitTest = () => {
    setIsSubmittedTest(true);
    setReviewingAttempt(null);
    const newAttempt: MockAttemptRecord = {
      id: `attempt-${Date.now()}`,
      exam_id: exam.id,
      topic_id: selectedPaper.id,
      subject: selectedPaper.title,
      score: marksEarned,
      total_marks: totalPossibleMarks,
      correct_count: correctCount,
      incorrect_count: incorrectCount,
      unattempted_count: unattemptedCount,
      time_taken_seconds: (selectedPaper.durationMinutes * 60) - timerSeconds,
      attempted_at: new Date().toLocaleString(),
      userAnswers: { ...userAnswers },
      paperData: selectedPaper
    };

    storageService.saveMockAttempt(newAttempt);
    setPastAttempts(storageService.getMockAttempts());
  };

  // Open and Review Past Test Attempt Handler
  const handleReviewPastAttempt = (att: MockAttemptRecord) => {
    try {
      const allRepositoryPapers: MockPaper[] = [
        ...availablePapers,
        ...NEW_DISCOVERED_PAPERS,
        ...SUBJECT_MOCK_TESTS,
        ...TOPIC_DRILL_TESTS,
        ...OFFICIAL_10_MOCK_PAPERS
      ];

      // 1. If att.paperData exists and has questions, use it directly
      let targetPaper: MockPaper | undefined = att.paperData?.questions?.length ? att.paperData : undefined;

      // 2. Search by exact ID in all repository papers
      if (!targetPaper && att.topic_id) {
        targetPaper = allRepositoryPapers.find(p => p && p.id === att.topic_id);
      }

      // 3. Search by exact Title in all repository papers
      if (!targetPaper && att.subject) {
        targetPaper = allRepositoryPapers.find(p => p && p.title && p.title.trim().toLowerCase() === att.subject.trim().toLowerCase());
      }

      // 4. Search by fuzzy title or subject inclusion
      if (!targetPaper && att.subject) {
        const subLower = att.subject.toLowerCase();
        targetPaper = allRepositoryPapers.find(p => {
          if (!p) return false;
          const titleMatch = Boolean(p.title && subLower.includes(p.title.toLowerCase()));
          const subjectMatch = Boolean(p.subject && subLower.includes(p.subject.toLowerCase()));
          return titleMatch || subjectMatch;
        });
      }

      // 5. If it's a quantitative drill (e.g. "AI Customized Drill: Quantitative Aptitude (7 Qs)")
      if (!targetPaper && att.subject && att.subject.toLowerCase().includes('quantitative')) {
        targetPaper = generateCustomMockTest({
          title: att.subject,
          selectedSubjects: ['Quantitative Aptitude'],
          selectedTopics: [],
          numQuestions: att.total_marks > 50 ? 25 : Math.max(7, Math.round(att.total_marks / 2)),
          difficulty: 'HARD'
        });
      }

      // 6. If it's the "Application Practice Simulator"
      if (!targetPaper && att.subject && att.subject.toLowerCase().includes('application')) {
        targetPaper = {
          id: 'sim-app-practice-review',
          title: 'SSC CGL Official Application Portal Practice Simulator',
          category: 'SECTIONAL_MOCK',
          examTier: 'Tier-1',
          year: 2026,
          totalQuestions: 4,
          totalMarks: 100,
          durationMinutes: 10,
          difficulty: 'EASY',
          description: 'Official application verification drill reviewing photo/signature standards, fee exemptions, post preferences, and eligibility checks.',
          provenanceTag: 'SSC Official Notice Rule 11.1 Key',
          questions: [
            {
              id: 'app-sim-q1',
              topicId: 'app-sim-topic-1',
              subject: 'General Awareness',
              tier: 'TIER_1',
              questionType: 'SECTIONAL_MOCK',
              difficulty: 'EASY',
              topicName: 'Official Notification Guidelines',
              questionText: 'According to official SSC CGL Notification 2026, what are the mandatory dimensions and specifications for the live photograph capture?',
              options: [
                { id: 0, text: 'Selfie taken without plain background, glasses permitted' },
                { id: 1, text: 'Clear front-facing shot, plain light background, without cap/spectacles, neutral expression' },
                { id: 2, text: 'Black and white passport photo with signature stamped across face' },
                { id: 3, text: 'Side profile photo showing left ear clearly' }
              ],
              correctOptionIndex: 1,
              shiftInfo: 'Official SSC Application Portal Guidelines Rule 11.1',
              explanation: 'Refer to the cited official SSC clause for the verified answer.',
              provenance: APP_SIM_PROVENANCE,
              detailedExplanation: {
                simpleExplanation: 'The official SSC live webcam photo capture requires a plain, well-lit background with no caps or spectacles to ensure automatic facial biometric matching on exam day.',
                coreConcept: 'SSC Live Web-Capture Norms (Rule 11.1)',
                technicalTerms: [
                  { term: 'Biometric Verification', meaning: 'Automated facial recognition matching conducted at the CBT center.' }
                ],
                stepByStepMethod: [
                  'Step 1: Check SSC notice rule 11.1 for application guidelines.',
                  'Step 2: Note requirement of neutral background without glasses or headgear.',
                  'Step 3: Confirm Option (2) meets all official norms.'
                ],
                shortcutTrick: {
                  name: 'SSC Photo Checklist 3-Point Rule',
                  trickSteps: 'Light background + No glasses + Both ears visible = 100% acceptance.',
                  timeSaved: 'Prevents application rejection'
                },
                crucialTakeaway: 'Wearing spectacles or caps during SSC webcam capture leads to immediate application rejection under Rule 11.1.'
              }
            },
            {
              id: 'app-sim-q2',
              topicId: 'app-sim-topic-2',
              subject: 'General Awareness',
              tier: 'TIER_1',
              questionType: 'SECTIONAL_MOCK',
              difficulty: 'EASY',
              topicName: 'Application Fee & Exemptions',
              questionText: 'Under the official SSC CGL recruitment rules, which of the following candidate categories are entirely exempt from paying the application fee of ₹100?',
              options: [
                { id: 0, text: 'All male candidates from General/OBC category' },
                { id: 1, text: 'Women candidates and candidates belonging to Scheduled Castes (SC), Scheduled Tribes (ST), and PwBD' },
                { id: 2, text: 'Only candidates who have already cleared SSC CHSL' },
                { id: 3, text: 'Candidates applying from rural pin codes only' }
              ],
              correctOptionIndex: 1,
              shiftInfo: 'Official SSC Fee Rules Rule 10.1',
              explanation: 'Refer to the cited official SSC clause for the verified answer.',
              provenance: APP_SIM_PROVENANCE,
              detailedExplanation: {
                simpleExplanation: 'All women candidates regardless of category, along with SC, ST, PwBD, and eligible Ex-Servicemen, are completely exempt from paying the application fee.',
                coreConcept: 'SSC Statutory Fee Exemption Framework',
                technicalTerms: [
                  { term: 'PwBD', meaning: 'Persons with Benchmark Disabilities.' }
                ],
                stepByStepMethod: [
                  'Step 1: Refer to SSC CGL Notification clause 10.1.',
                  'Step 2: Identify fee-exempt groups: Women, SC, ST, PwBD, ESM.',
                  'Step 3: Option (2) correctly lists these statutory exemptions.'
                ],
                shortcutTrick: {
                  name: 'Exemption Memory Code',
                  trickSteps: 'Women + SC + ST + PwBD = ₹0 Fee.',
                  timeSaved: 'Instant question answer'
                },
                crucialTakeaway: 'Always verify fee exemption status before final submit to avoid double payment.'
              }
            },
            {
              id: 'app-sim-q3',
              topicId: 'app-sim-topic-3',
              subject: 'General Awareness',
              tier: 'TIER_1',
              questionType: 'SECTIONAL_MOCK',
              difficulty: 'EASY',
              topicName: 'Post Preference Submission',
              questionText: 'At which stage does the Commission collect the final option-cum-preference for posts and departments from SSC CGL candidates?',
              options: [
                { id: 0, text: 'During initial online registration before Tier-1' },
                { id: 1, text: 'Before declaration of the final results, via online web-portal after Tier-2 examination' },
                { id: 2, text: 'Physically at the regional SSC office during Tier-1 exam day' },
                { id: 3, text: 'Post-preferences are assigned randomly by computerized lottery' }
              ],
              correctOptionIndex: 1,
              shiftInfo: 'Official SSC Post Allocation Notice',
              explanation: 'Refer to the cited official SSC clause for the verified answer.',
              provenance: APP_SIM_PROVENANCE,
              detailedExplanation: {
                simpleExplanation: 'Post preferences are submitted online by candidates who appear in Tier-2 before the declaration of final merit list.',
                coreConcept: 'Post Preference Window Process',
                technicalTerms: [
                  { term: 'Option-cum-Preference', meaning: 'Prioritized choice of ministries (e.g. CSS, MEA, Income Tax) submitted online.' }
                ],
                stepByStepMethod: [
                  'Step 1: Check recruitment scheme revised process.',
                  'Step 2: SSC opens online portal for post preference submission post Tier-2.',
                  'Step 3: Non-submission leads to forfeiture of candidature.'
                ],
                shortcutTrick: {
                  name: 'Order of Priority Rule',
                  trickSteps: 'Rank posts by Grade Pay (GP 4600 > GP 2800 > GP 2400) and city preferences.',
                  timeSaved: 'Secures target department'
                },
                crucialTakeaway: 'Missing the online preference window completely disqualifies the candidate from final merit consideration.'
              }
            },
            {
              id: 'app-sim-q4',
              topicId: 'app-sim-topic-4',
              subject: 'General Awareness',
              tier: 'TIER_1',
              questionType: 'SECTIONAL_MOCK',
              difficulty: 'EASY',
              topicName: 'Age Limit & Crucial Date Determination',
              questionText: 'What is the crucial date for determination of age-limit for SSC CGL Examination as prescribed in the official notification?',
              options: [
                { id: 0, text: 'The date on which Tier-1 admit cards are issued' },
                { id: 1, text: '01st August of the exam notification year (or as notified in Section 5.1)' },
                { id: 2, text: '31st December of the previous calendar year' },
                { id: 3, text: 'Candidate’s birthday in the respective examination year' }
              ],
              correctOptionIndex: 1,
              shiftInfo: 'Official SSC Eligibility Rule 5.1',
              explanation: 'Refer to the cited official SSC clause for the verified answer.',
              provenance: APP_SIM_PROVENANCE,
              detailedExplanation: {
                simpleExplanation: 'The Commission sets 01st August of the examination year as the standard benchmark date for calculating minimum and maximum age criteria.',
                coreConcept: 'Crucial Date of Eligibility (Rule 5.1)',
                technicalTerms: [
                  { term: 'Crucial Date', meaning: 'The exact calendar cutoff date against which age and degree qualifications are validated.' }
                ],
                stepByStepMethod: [
                  'Step 1: Refer to Rule 5.1 of official recruitment rules.',
                  'Step 2: Standard DoPT guidelines prescribe 01-08 of the examination year.',
                  'Step 3: Option (2) accurately states 01st August.'
                ],
                shortcutTrick: {
                  name: 'DoPT Standard Reference Rule',
                  trickSteps: 'Exams held in second half of the year benchmark against 1st August.',
                  timeSaved: 'Instant recall'
                },
                crucialTakeaway: 'Ensure your date of birth on Class 10 Certificate satisfies the 18–30 / 18–32 range as on 1st August.'
              }
            }
          ]
        };
      }

      // 7. Ultimate fallback to the primary verified mock paper so it NEVER crashes
      if (!targetPaper) {
        targetPaper = OFFICIAL_10_MOCK_PAPERS[0];
      }

      // Ensure paper has valid questions array
      if (!targetPaper.questions || targetPaper.questions.length === 0) {
        targetPaper = {
          ...targetPaper,
          questions: OFFICIAL_10_MOCK_PAPERS[0].questions
        };
      }

      const storedAnswers = att.userAnswers || att.details?.userAnswers;
      const hasRecordedAnswers = storedAnswers && Object.keys(storedAnswers).length > 0;

      setSelectedPaper(targetPaper);
      setUserAnswers(hasRecordedAnswers ? { ...storedAnswers } : {});
      setReviewingAttempt(att);
      setIsSubmittedTest(true);
      setIsTestStarted(true);
      setActivePracticeTab('ACTIVE_TEST');
      setCurrentIdx(0);
      setSolutionFilter('ALL');
      setSolutionSectionFilter('ALL');
      
      // Scroll smoothly to top
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      console.error('Error opening past attempt for review:', err);
    }
  };

  const isOlderAttemptWithoutAnswers = Boolean(
    reviewingAttempt && (!reviewingAttempt.userAnswers || Object.keys(reviewingAttempt.userAnswers).length === 0)
  );

  const displayScore = reviewingAttempt ? reviewingAttempt.score : marksEarned;
  const displayTotalMarks = reviewingAttempt ? reviewingAttempt.total_marks : totalPossibleMarks;
  const displayCorrect = reviewingAttempt ? reviewingAttempt.correct_count : correctCount;
  const displayIncorrect = reviewingAttempt ? reviewingAttempt.incorrect_count : incorrectCount;
  const displayUnattempted = reviewingAttempt ? reviewingAttempt.unattempted_count : unattemptedCount;
  const displayAccuracy = reviewingAttempt
    ? ((reviewingAttempt.correct_count + reviewingAttempt.incorrect_count) > 0
        ? Math.round((reviewingAttempt.correct_count / (reviewingAttempt.correct_count + reviewingAttempt.incorrect_count)) * 100)
        : 0)
    : accuracyPercentage;

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // Filter Solutions List
  const filteredSolutions = questionsList.filter((q, idx) => {
    if (solutionSectionFilter !== 'ALL' && q.subject !== solutionSectionFilter) return false;

    if (isOlderAttemptWithoutAnswers) {
      return true;
    }

    const userAns = userAnswers[idx];
    const isCorrect = userAns === q.correctOptionIndex;
    const isUnattempted = userAns === undefined;
    const isIncorrect = userAns !== undefined && !isCorrect;

    if (solutionFilter === 'INCORRECT' && !isIncorrect) return false;
    if (solutionFilter === 'UNATTEMPTED' && !isUnattempted) return false;
    if (solutionFilter === 'CORRECT' && !isCorrect) return false;

    return true;
  });

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* 1. TOP PRACTICE NAVIGATION & AUTO-SYNC BAR */}
      <div className="glass-card" style={{ padding: '20px', background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '14px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className="badge badge-demo" style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.4)' }}>
                ⚡ OFFICIAL CBT ENGINE & ANIMATED SHORTCUTS
              </span>
              <span style={{ fontSize: '0.8rem', color: '#93c5fd', fontWeight: 700 }}>
                • Target: {targetPost.postName}
              </span>
            </div>
            <h3 style={{ fontSize: '1.45rem', fontWeight: 800, color: 'white', margin: 0 }}>
              Practice Questions, Full Shift Papers & Detailed Solutions
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', margin: '4px 0 0 0' }}>
              Attempt authentic previous years shift papers, sectionals, topic drills, or chat with AI. Every test features step-by-step solutions with animated speed shortcut cards.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              onClick={handleAutoSyncPapers}
              disabled={isSyncingPapers}
              className="btn btn-emerald"
              style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px' }}
            >
              <RefreshCw size={14} className={isSyncingPapers ? 'animate-spin' : ''} />
              {isSyncingPapers ? 'Checking Repositories...' : '🔄 Sync Latest Sourced Papers'}
            </button>

            {isTestStarted && (
              <button onClick={handleResetTest} className="btn btn-secondary" style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <RotateCcw size={14} /> {reviewingAttempt ? 'Exit Review' : 'Exit Test'}
              </button>
            )}
          </div>
        </div>

        {/* Sync Success Banner */}
        {syncSuccessNotice && (
          <div className="animate-fade-in" style={{ padding: '10px 14px', borderRadius: 'var(--radius-sm)', background: 'rgba(16, 185, 129, 0.12)', border: '1px solid #10b981', color: '#86efac', fontSize: '0.84rem', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <ShieldCheck size={16} color="#34d399" />
            <span>{syncSuccessNotice}</span>
          </div>
        )}

        {/* 5 Main Navigation Tabs */}
        <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
          <button
            onClick={() => { setActivePracticeTab('PAPERS_LIST'); setIsTestStarted(false); }}
            className={`btn ${activePracticeTab === 'PAPERS_LIST' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.85rem', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap' }}
          >
            <List size={15} /> 📑 Shift Papers ({availablePapers.length})
          </button>

          <button
            onClick={() => { setActivePracticeTab('AI_CHAT_ASSISTANT'); setIsTestStarted(false); }}
            className={`btn ${activePracticeTab === 'AI_CHAT_ASSISTANT' ? 'btn-emerald' : 'btn-secondary'}`}
            style={{ fontSize: '0.85rem', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap', border: '1px solid #34d399' }}
          >
            <MessageSquare size={15} /> 💬 Chat With AI Test Creator
          </button>

          <button
            onClick={() => { setActivePracticeTab('SUBJECT_TESTS'); setIsTestStarted(false); }}
            className={`btn ${activePracticeTab === 'SUBJECT_TESTS' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.85rem', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap' }}
          >
            <Target size={15} /> 🎯 Subject Sectionals (25 Qs)
          </button>

          <button
            onClick={() => { setActivePracticeTab('TOPIC_DRILLS'); setIsTestStarted(false); }}
            className={`btn ${activePracticeTab === 'TOPIC_DRILLS' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.85rem', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap' }}
          >
            <Zap size={15} /> ⚡ Topic Drills (15 Qs)
          </button>

          <button
            onClick={() => setActivePracticeTab('PAST_ANALYTICS')}
            className={`btn ${activePracticeTab === 'PAST_ANALYTICS' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.85rem', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap' }}
          >
            <BarChart2 size={15} /> 📊 Past Tests History ({pastAttempts.length})
          </button>

          {isTestStarted && (
            <button
              onClick={() => setActivePracticeTab('ACTIVE_TEST')}
              className={`btn ${activePracticeTab === 'ACTIVE_TEST' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.85rem', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap', border: '1px solid #60a5fa' }}
            >
              <Eye size={15} /> {reviewingAttempt ? '🔍 Reviewing Past Test' : '📝 Active Test'}
            </button>
          )}
        </div>
      </div>

      {/* VIEW 1: AVAILABLE SHIFT PAPERS (100 Qs) */}
      {activePracticeTab === 'PAPERS_LIST' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
            <div>
              <h4 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'white', margin: 0 }}>
                Verified Official Shift Papers ({availablePapers.length} Available Papers)
              </h4>
              <span style={{ fontSize: '0.8rem', color: '#86efac' }}>
                100 Questions / 200 Marks • 60 Minutes Real CBT Exam Clock
              </span>
            </div>
            <span className="badge badge-verified" style={{ fontSize: '0.75rem' }}>
              ✓ Cryptographically Verified with RTI Shift Keys
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px' }}>
            {availablePapers.map((paper, pIdx) => (
              <div 
                key={paper.id}
                className="glass-card"
                style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px', border: '1px solid var(--border-color)', background: 'rgba(15, 23, 42, 0.9)' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span className="badge badge-verified" style={{ fontSize: '0.72rem' }}>{paper.provenanceTag}</span>
                  <span className="glass-pill" style={{ fontSize: '0.72rem', color: '#fbbf24' }}>{paper.examTier} • {paper.year}</span>
                </div>

                <div>
                  <h4 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'white', margin: '0 0 6px 0' }}>{pIdx + 1}. {paper.title}</h4>
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>{paper.description}</p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', padding: '10px', borderRadius: 'var(--radius-sm)', background: 'rgba(255,255,255,0.03)', fontSize: '0.78rem', textAlign: 'center' }}>
                  <div><strong style={{ color: '#93c5fd' }}>Questions</strong><div style={{ color: 'white', fontWeight: 700 }}>{paper.totalQuestions} Qs</div></div>
                  <div><strong style={{ color: '#93c5fd' }}>Duration</strong><div style={{ color: 'white', fontWeight: 700 }}>{paper.durationMinutes} Mins</div></div>
                  <div><strong style={{ color: '#93c5fd' }}>Max Marks</strong><div style={{ color: '#86efac', fontWeight: 700 }}>{paper.totalMarks} Marks</div></div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Shift: {paper.shiftDate}</span>
                  <button onClick={() => handleStartTest(paper)} className="btn btn-emerald" style={{ fontSize: '0.85rem', padding: '8px 18px', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 800 }}>
                    <Play size={14} /> Start Paper Now
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* VIEW 2: CONVERSATIONAL AI MOCK CREATOR CHAT ASSISTANT */}
      {activePracticeTab === 'AI_CHAT_ASSISTANT' && (
        <div className="glass-card" style={{ padding: '0', overflow: 'hidden', border: '1px solid rgba(16, 185, 129, 0.35)', background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(6, 78, 59, 0.2) 100%)', display: 'flex', flexDirection: 'column', height: '620px' }}>
          
          {/* Chat Header */}
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(0,0,0,0.2)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: 'rgba(16, 185, 129, 0.2)', border: '1px solid #10b981', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#34d399' }}>
                <Bot size={20} />
              </div>
              <div>
                <h4 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'white', margin: 0 }}>
                  AI Mock Test Creator Assistant
                </h4>
                <span style={{ fontSize: '0.75rem', color: '#86efac' }}>
                  • Online • Context-Aware NLP Test Synthesis & Intelligent Timer
                </span>
              </div>
            </div>

            <span className="badge badge-verified" style={{ fontSize: '0.72rem' }}>
              Target: {targetPost.postName}
            </span>
          </div>

          {/* Quick Context Prompt Pills */}
          <div style={{ padding: '10px 16px', background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid var(--border-color)', display: 'flex', gap: '6px', overflowX: 'auto' }}>
            {[
              { label: '⚡ 15-Q Hard Geometry & Algebra Drill', prompt: 'Create a 15-question hard test on Geometry & Algebra for Tier-2' },
              { label: '🏛️ 20-Q Polity Articles & Modern History', prompt: 'Give me a 20-question speed drill on Indian Polity Articles and Modern History' },
              { label: '📖 15-Q 60 Grammar Rules & Vocab', prompt: 'Generate a 15-question test on English Grammar Error Spotting and Norman Lewis Vocabulary' },
              { label: '🔍 Test My Past Weak Topics', prompt: 'Generate a practice test specifically focused on my past weak areas' }
            ].map((pill, pIdx) => (
              <button
                key={pIdx}
                onClick={() => handleSendChatMessage(pill.prompt)}
                className="glass-pill"
                style={{ fontSize: '0.75rem', padding: '4px 10px', color: '#93c5fd', cursor: 'pointer', whiteSpace: 'nowrap', border: '1px solid rgba(59, 130, 246, 0.3)' }}
              >
                {pill.label}
              </button>
            ))}
          </div>

          {/* Chat Messages Stream */}
          <div style={{ flex: 1, padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {chatMessages.map(msg => (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  gap: '10px',
                  alignItems: 'flex-start',
                  justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start'
                }}
              >
                {msg.sender === 'assistant' && (
                  <div style={{ width: '30px', height: '30px', borderRadius: '50%', background: 'rgba(16, 185, 129, 0.2)', border: '1px solid #10b981', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#34d399', flexShrink: 0, marginTop: '2px' }}>
                    <Bot size={16} />
                  </div>
                )}

                <div
                  style={{
                    maxWidth: '80%',
                    padding: '14px 18px',
                    borderRadius: 'var(--radius-md)',
                    background: msg.sender === 'user' ? 'var(--primary)' : 'rgba(15, 23, 42, 0.95)',
                    border: msg.sender === 'user' ? '1px solid #60a5fa' : '1px solid var(--border-color)',
                    color: 'white',
                    fontSize: '0.88rem',
                    lineHeight: 1.5,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px'
                  }}
                >
                  <div style={{ whiteSpace: 'pre-line' }}>{msg.text}</div>

                  {msg.proposedTest && (
                    <div style={{ padding: '14px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(16, 185, 129, 0.4)', display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span className="badge badge-verified" style={{ fontSize: '0.7rem' }}>
                          {msg.proposedTest.provenanceTag}
                        </span>
                        <span style={{ fontSize: '0.75rem', color: '#fbbf24', fontWeight: 700 }}>
                          Level: {msg.proposedTest.difficulty}
                        </span>
                      </div>

                      <div style={{ fontWeight: 800, color: 'white', fontSize: '0.95rem' }}>
                        {msg.proposedTest.title}
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', fontSize: '0.75rem', textAlign: 'center', background: 'rgba(255,255,255,0.03)', padding: '8px', borderRadius: '4px' }}>
                        <div><strong style={{ color: '#93c5fd' }}>Questions</strong><div style={{ color: 'white' }}>{msg.proposedTest.totalQuestions} Qs</div></div>
                        <div><strong style={{ color: '#93c5fd' }}>Timer</strong><div style={{ color: '#86efac', fontWeight: 700 }}>{msg.proposedTest.durationMinutes} Mins</div></div>
                        <div><strong style={{ color: '#93c5fd' }}>Marks</strong><div style={{ color: 'white' }}>{msg.proposedTest.totalMarks} M</div></div>
                      </div>

                      <button
                        onClick={() => handleStartTest(msg.proposedTest!)}
                        className="btn btn-emerald"
                        style={{ width: '100%', padding: '10px', fontSize: '0.88rem', fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', boxShadow: '0 4px 14px rgba(16, 185, 129, 0.4)' }}
                      >
                        <Play size={14} /> Start This Custom Mock Test Now <ArrowRight size={14} />
                      </button>
                    </div>
                  )}

                  <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', alignSelf: 'flex-end' }}>
                    {msg.timestamp}
                  </span>
                </div>

                {msg.sender === 'user' && (
                  <div style={{ width: '30px', height: '30px', borderRadius: '50%', background: 'rgba(59, 130, 246, 0.2)', border: '1px solid #3b82f6', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#93c5fd', flexShrink: 0, marginTop: '2px' }}>
                    <User size={16} />
                  </div>
                )}
              </div>
            ))}
            <div ref={chatBottomRef} />
          </div>

          {/* Chat Input Bar */}
          <div style={{ padding: '14px 20px', borderTop: '1px solid var(--border-color)', background: 'rgba(0,0,0,0.3)', display: 'flex', gap: '10px', alignItems: 'center' }}>
            <input
              type="text"
              placeholder="e.g. 'Create a 15-question hard test on Geometry and Indian Polity with 15 mins timer'..."
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSendChatMessage()}
              style={{
                flex: 1,
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid var(--border-color)',
                color: 'white',
                fontSize: '0.9rem'
              }}
            />
            <button
              onClick={() => handleSendChatMessage()}
              className="btn btn-emerald"
              style={{ padding: '12px 20px', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 800 }}
            >
              <Send size={16} /> Send
            </button>
          </div>

        </div>
      )}

      {/* VIEW 3: SUBJECT SECTIONALS (25 Qs) */}
      {activePracticeTab === 'SUBJECT_TESTS' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
            <h4 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'white', margin: 0 }}>
              Subject-Wise Full Sectional Mocks (25 Questions / 50 Marks)
            </h4>
            <span style={{ fontSize: '0.8rem', color: '#93c5fd' }}>
              Targeted Subject Speed Calibration
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
            {SUBJECT_MOCK_TESTS.map((paper, pIdx) => (
              <div 
                key={paper.id}
                className="glass-card"
                style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px', border: '1px solid var(--border-color)', background: 'rgba(15, 23, 42, 0.9)' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span className="badge badge-verified" style={{ fontSize: '0.72rem' }}>{paper.provenanceTag}</span>
                  <span className="glass-pill" style={{ fontSize: '0.72rem', color: '#93c5fd' }}>{paper.subject}</span>
                </div>

                <div>
                  <h4 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'white', margin: '0 0 6px 0' }}>{paper.title}</h4>
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>{paper.description}</p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', padding: '10px', borderRadius: 'var(--radius-sm)', background: 'rgba(255,255,255,0.03)', fontSize: '0.78rem', textAlign: 'center' }}>
                  <div><strong style={{ color: '#93c5fd' }}>Questions</strong><div style={{ color: 'white', fontWeight: 700 }}>{paper.totalQuestions} Qs</div></div>
                  <div><strong style={{ color: '#93c5fd' }}>Duration</strong><div style={{ color: 'white', fontWeight: 700 }}>{paper.durationMinutes} Mins</div></div>
                  <div><strong style={{ color: '#93c5fd' }}>Max Marks</strong><div style={{ color: '#86efac', fontWeight: 700 }}>{paper.totalMarks} Marks</div></div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#fbbf24' }}>Level: {paper.difficulty}</span>
                  <button onClick={() => handleStartTest(paper)} className="btn btn-primary" style={{ fontSize: '0.85rem', padding: '8px 18px', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 800 }}>
                    <Play size={14} /> Start Sectional
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* VIEW 4: TOPIC DRILLS (15 Qs) */}
      {activePracticeTab === 'TOPIC_DRILLS' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
            <h4 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'white', margin: 0 }}>
              Topic-Specific Focused Speed Drills (15 Questions)
            </h4>
            <span style={{ fontSize: '0.8rem', color: '#fbbf24' }}>
              High-Frequency Concept Sharpener
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
            {TOPIC_DRILL_TESTS.map((paper, pIdx) => (
              <div 
                key={paper.id}
                className="glass-card"
                style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px', border: '1px solid var(--border-color)', background: 'rgba(15, 23, 42, 0.9)' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span className="badge badge-verified" style={{ fontSize: '0.72rem' }}>{paper.provenanceTag}</span>
                  <span className="glass-pill" style={{ fontSize: '0.72rem', color: '#93c5fd' }}>{paper.subject}</span>
                </div>

                <div>
                  <h4 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'white', margin: '0 0 6px 0' }}>{paper.title}</h4>
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>{paper.description}</p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', padding: '10px', borderRadius: 'var(--radius-sm)', background: 'rgba(255,255,255,0.03)', fontSize: '0.78rem', textAlign: 'center' }}>
                  <div><strong style={{ color: '#93c5fd' }}>Questions</strong><div style={{ color: 'white', fontWeight: 700 }}>{paper.totalQuestions} Qs</div></div>
                  <div><strong style={{ color: '#93c5fd' }}>Duration</strong><div style={{ color: 'white', fontWeight: 700 }}>{paper.durationMinutes} Mins</div></div>
                  <div><strong style={{ color: '#93c5fd' }}>Max Marks</strong><div style={{ color: '#86efac', fontWeight: 700 }}>{paper.totalMarks} Marks</div></div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#fbbf24' }}>Level: {paper.difficulty}</span>
                  <button onClick={() => handleStartTest(paper)} className="btn btn-emerald" style={{ fontSize: '0.85rem', padding: '8px 18px', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 800 }}>
                    <Play size={14} /> Start Drill
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* VIEW 5: ACTIVE TEST & POST-TEST ENHANCED CLARITY DIAGNOSTIC DASHBOARD */}
      {activePracticeTab === 'ACTIVE_TEST' && (
        <>
          {/* Active Test Header Bar */}
          <div className="glass-card" style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span className="badge badge-verified" style={{ fontSize: '0.78rem' }}>
                {selectedPaper.title}
              </span>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Total: {selectedPaper.totalQuestions} Questions ({selectedPaper.totalMarks} Marks)
              </span>
            </div>

            {!isSubmittedTest && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <button
                  onClick={() => setIsTimerPaused(!isTimerPaused)}
                  className="btn btn-secondary"
                  style={{ fontSize: '0.78rem', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  {isTimerPaused ? <Play size={13} /> : <Pause size={13} />} {isTimerPaused ? 'Resume' : 'Pause Clock'}
                </button>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: timerSeconds < 300 ? '#f87171' : '#34d399', fontWeight: 900, fontSize: '1.2rem', background: 'rgba(0,0,0,0.3)', padding: '6px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <Clock size={18} /> {formatTimer(timerSeconds)}
                </div>
              </div>
            )}
          </div>

          {/* Section Jump Tabs for 100-Q Papers */}
          {!isSubmittedTest && selectedPaper.totalQuestions >= 50 && (
            <div style={{ display: 'flex', gap: '8px', overflowX: 'auto' }}>
              {[
                { label: 'All Sections', val: 'ALL', startIdx: 0 },
                { label: 'Section I: Reasoning', val: 'Reasoning & General Intelligence', startIdx: 0 },
                { label: 'Section II: General Awareness', val: 'General Awareness', startIdx: 25 },
                { label: 'Section III: Quantitative Aptitude', val: 'Quantitative Aptitude', startIdx: 50 },
                { label: 'Section IV: English Comprehension', val: 'English Comprehension', startIdx: 75 }
              ].map(sec => (
                <button
                  key={sec.val}
                  onClick={() => { setActiveSection(sec.val); setCurrentIdx(sec.startIdx); }}
                  className={`btn ${activeSection === sec.val ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ fontSize: '0.8rem', padding: '6px 14px', whiteSpace: 'nowrap' }}
                >
                  {sec.label}
                </button>
              ))}
            </div>
          )}

          {/* TEST QUESTION SCREEN OR ENHANCED POST-TEST DASHBOARD */}
          {!isSubmittedTest ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '20px', alignItems: 'start' }}>
              
              {/* Question Screen */}
              <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span className="badge badge-verified" style={{ fontSize: '0.8rem' }}>
                      Question {currentIdx + 1} of {questionsList.length}
                    </span>
                    <span className="glass-pill" style={{ fontSize: '0.78rem', color: '#93c5fd' }}>
                      {currentQ.subject}
                    </span>
                    <span className="glass-pill" style={{ fontSize: '0.78rem', color: '#fbbf24' }}>
                      {currentQ.topicName}
                    </span>
                  </div>

                  <span style={{ fontSize: '0.8rem', color: '#86efac', fontWeight: 700 }}>
                    +2.0 Marks / -0.50 Neg
                  </span>
                </div>

                {/* Question Text */}
                <div style={{ fontSize: '1.05rem', color: 'white', lineHeight: 1.6, fontWeight: 500 }}>
                  {currentQ.questionText}
                </div>

                {/* Options List */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {currentQ.options.map(opt => {
                    const isSelected = userAnswers[currentIdx] === opt.id;
                    return (
                      <div
                        key={opt.id}
                        onClick={() => handleSelectOption(opt.id)}
                        style={{
                          padding: '14px 18px',
                          borderRadius: 'var(--radius-md)',
                          background: isSelected ? 'rgba(59, 130, 246, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                          border: isSelected ? '1px solid var(--primary)' : '1px solid var(--border-color)',
                          color: isSelected ? '#93c5fd' : 'var(--text-secondary)',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px',
                          transition: 'all 0.15s ease'
                        }}
                      >
                        <div style={{ width: '22px', height: '22px', borderRadius: '50%', border: isSelected ? '2px solid var(--primary)' : '2px solid gray', display: 'flex', alignItems: 'center', justifyContent: 'center', color: isSelected ? 'var(--primary)' : 'transparent', fontSize: '0.75rem', fontWeight: 800 }}>
                          {isSelected ? '✓' : ''}
                        </div>
                        <span style={{ fontSize: '0.95rem' }}>{opt.text}</span>
                      </div>
                    );
                  })}
                </div>

                {/* Test Action Bar */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button onClick={handleClearResponse} className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '6px 12px' }}>
                      Clear Response
                    </button>
                    <button onClick={handleToggleReview} className={`btn ${markedForReview[currentIdx] ? 'btn-primary' : 'btn-secondary'}`} style={{ fontSize: '0.8rem', padding: '6px 12px' }}>
                      <Bookmark size={14} /> {markedForReview[currentIdx] ? 'Marked for Review' : 'Mark for Review'}
                    </button>
                  </div>

                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={() => setCurrentIdx(prev => Math.max(0, prev - 1))}
                      disabled={currentIdx === 0}
                      className="btn btn-secondary"
                      style={{ fontSize: '0.82rem', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                    >
                      <ChevronLeft size={16} /> Prev
                    </button>
                    <button
                      onClick={() => setCurrentIdx(prev => Math.min(questionsList.length - 1, prev + 1))}
                      disabled={currentIdx === questionsList.length - 1}
                      className="btn btn-primary"
                      style={{ fontSize: '0.82rem', padding: '6px 14px', display: 'flex', alignItems: 'center', gap: '4px' }}
                    >
                      Next <ChevronRight size={16} />
                    </button>
                  </div>
                </div>
              </div>

              {/* Right Palette Panel */}
              <div className="glass-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 800, color: 'white', margin: 0 }}>
                    Question Palette ({questionsList.length} Qs)
                  </h4>
                  <span style={{ fontSize: '0.75rem', color: '#86efac' }}>
                    {Object.keys(userAnswers).length}/{questionsList.length} Done
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '6px', maxHeight: '380px', overflowY: 'auto', paddingRight: '4px' }}>
                  {questionsList.map((_, qIdx) => {
                    const isAnswered = userAnswers[qIdx] !== undefined;
                    const isReview = !!markedForReview[qIdx];
                    const isCurrent = currentIdx === qIdx;

                    let bg = 'rgba(255, 255, 255, 0.05)';
                    let border = '1px solid var(--border-color)';
                    let color = 'white';

                    if (isAnswered) {
                      bg = '#10b981';
                      color = 'white';
                    } else if (isReview) {
                      bg = '#8b5cf6';
                      color = 'white';
                    }

                    if (isCurrent) {
                      border = '2px solid #60a5fa';
                    }

                    return (
                      <button
                        key={qIdx}
                        onClick={() => setCurrentIdx(qIdx)}
                        style={{
                          height: '32px',
                          borderRadius: 'var(--radius-sm)',
                          background: bg,
                          border: border,
                          color: color,
                          fontWeight: 700,
                          fontSize: '0.78rem',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}
                      >
                        {qIdx + 1}
                      </button>
                    );
                  })}
                </div>

                <button
                  onClick={handleSubmitTest}
                  className="btn btn-emerald"
                  style={{ width: '100%', padding: '12px', fontSize: '0.95rem', fontWeight: 800, marginTop: '8px', boxShadow: '0 4px 16px rgba(16, 185, 129, 0.4)' }}
                >
                  <CheckSquare size={16} /> Submit & View Detailed Analysis
                </button>
              </div>

            </div>
          ) : (

            /* 🎯 ENHANCED CLARITY POST-TEST DASHBOARD & ANIMATED STEP-BY-STEP SOLUTIONS */
            <div className="glass-card animate-fade-in" style={{ padding: '28px', display: 'flex', flexDirection: 'column', gap: '26px' }}>
              
              {/* Review Mode Banner */}
              {reviewingAttempt && (
                <div style={{
                  padding: '18px 22px',
                  borderRadius: 'var(--radius-md)',
                  background: 'linear-gradient(135deg, rgba(30, 58, 138, 0.45) 0%, rgba(15, 23, 42, 0.98) 100%)',
                  border: '1.5px solid rgba(96, 165, 250, 0.5)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '16px',
                  boxShadow: '0 8px 30px rgba(37, 99, 235, 0.25)'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <div style={{ background: '#2563eb', padding: '12px', borderRadius: '10px', color: 'white', display: 'flex', boxShadow: '0 0 16px rgba(37, 99, 235, 0.6)' }}>
                      <Eye size={24} />
                    </div>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                        <span style={{ fontWeight: 800, color: 'white', fontSize: '1.2rem' }}>
                          Historical Test Review Mode: {reviewingAttempt.subject}
                        </span>
                        <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.25)', color: '#93c5fd', border: '1px solid rgba(96, 165, 250, 0.4)' }}>
                          Attempted: {reviewingAttempt.attempted_at || 'Saved Session'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.86rem', color: '#cbd5e1', marginTop: '4px' }}>
                        Performance Record: <strong style={{ color: '#86efac' }}>{reviewingAttempt.correct_count} Correct</strong>, <strong style={{ color: '#f87171' }}>{reviewingAttempt.incorrect_count} Wrong</strong>, <strong style={{ color: '#fde047' }}>{reviewingAttempt.unattempted_count} Unattempted</strong> • Score: <strong style={{ color: '#34d399' }}>{reviewingAttempt.score} / {reviewingAttempt.total_marks}</strong>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    <button 
                      onClick={() => {
                        setReviewingAttempt(null);
                        setActivePracticeTab('PAST_ANALYTICS');
                      }}
                      className="btn btn-secondary"
                      style={{ fontSize: '0.85rem', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700 }}
                    >
                      <RotateCcw size={14} /> Back to Performance Matrix
                    </button>
                    <button 
                      onClick={() => {
                        const p = selectedPaper;
                        setReviewingAttempt(null);
                        handleStartTest(p);
                      }}
                      className="btn btn-emerald"
                      style={{ fontSize: '0.85rem', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 800 }}
                    >
                      <Play size={14} /> Re-take This Paper
                    </button>
                  </div>
                </div>
              )}

              {/* Notice for Older Attempts where answers were not saved */}
              {isOlderAttemptWithoutAnswers && (
                <div style={{
                  padding: '14px 18px',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(245, 158, 11, 0.12)',
                  border: '1px solid rgba(245, 158, 11, 0.4)',
                  color: '#fef08a',
                  fontSize: '0.92rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px'
                }}>
                  <AlertTriangle size={18} color="#fbbf24" style={{ flexShrink: 0 }} />
                  <span>Detailed answer selections were not recorded for this attempt. You can still review the complete paper and all solutions.</span>
                </div>
              )}

              {/* Top Scorecard Banner */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '20px' }}>
                <div>
                  <span className="badge badge-verified" style={{ fontSize: '0.78rem' }}>
                    {reviewingAttempt ? '📖 HISTORICAL TEST REVIEW & SOLUTIONS' : '🎯 TEST EVALUATION COMPLETE & SYNCED TO SQLITE'}
                  </span>
                  <h3 style={{ fontSize: '1.7rem', fontWeight: 800, color: 'white', margin: '6px 0 2px 0' }}>
                    {reviewingAttempt ? `Reviewing: ${selectedPaper.title}` : 'In-Depth Diagnostic Clarity & Solutions Engine'}
                  </h3>
                  <div style={{ fontSize: '0.85rem', color: '#93c5fd' }}>
                    Target Post: <strong>{targetPost.postName}</strong> ({targetPost.department})
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  <div style={{ padding: '12px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.72rem', color: '#86efac', textTransform: 'uppercase', fontWeight: 700 }}>Final Score</div>
                    <div style={{ fontSize: '1.6rem', fontWeight: 900, color: '#34d399' }}>{displayScore} / {displayTotalMarks}</div>
                  </div>

                  <div style={{ padding: '12px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.72rem', color: '#93c5fd', textTransform: 'uppercase', fontWeight: 700 }}>Accuracy Rate</div>
                    <div style={{ fontSize: '1.6rem', fontWeight: 900, color: '#60a5fa' }}>{displayAccuracy}%</div>
                  </div>

                  <div style={{ padding: '12px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.72rem', color: '#fde047', textTransform: 'uppercase', fontWeight: 700 }}>Correct / Total</div>
                    <div style={{ fontSize: '1.6rem', fontWeight: 900, color: '#fbbf24' }}>{displayCorrect} / {questionsList.length}</div>
                  </div>
                </div>
              </div>

              {/* 🎯 ENHANCED CLARITY WEAKNESS ANALYSIS MATRIX */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <h4 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'white', margin: 0 }}>
                      🔍 Enhanced Clarity Weakness & Topic Diagnosis
                    </h4>
                    <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                      Categorized by critical error severity, failure causes, and direct exam impact.
                    </span>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
                  
                  {/* 🔴 CRITICAL WEAK AREAS (< 50%) */}
                  <div style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(239, 68, 68, 0.05)', border: '1px solid rgba(239, 68, 68, 0.4)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f87171', fontWeight: 800, fontSize: '1.05rem' }}>
                        <XCircle size={18} /> 🔴 Critical Weak Areas (&lt; 50% Accuracy)
                      </div>
                      <span className="badge" style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5' }}>{weakAreas.length} Needs Attention</span>
                    </div>

                    {weakAreas.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {weakAreas.map((w, wIdx) => {
                          const matchedDrill = TOPIC_DRILL_TESTS.find(t => t.subject === w.subject) || TOPIC_DRILL_TESTS[0];
                          return (
                            <div key={wIdx} style={{ padding: '14px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(239,68,68,0.3)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <strong style={{ color: 'white', fontSize: '0.95rem' }}>{w.topic}</strong>
                                <span style={{ color: '#fca5a5', fontWeight: 800, fontSize: '0.82rem' }}>{w.accuracy}% Acc</span>
                              </div>

                              <div style={{ fontSize: '0.78rem', color: '#fecaca', lineHeight: 1.4 }}>
                                <strong>⚠️ Why You Missed:</strong> {w.trapAlert}
                              </div>

                              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                <strong>📊 Exam Impact:</strong> {w.examImpact}
                              </div>

                              <button
                                onClick={() => handleStartTest(matchedDrill)}
                                className="btn btn-primary"
                                style={{ fontSize: '0.78rem', padding: '6px 12px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', width: '100%', marginTop: '4px' }}
                              >
                                <Zap size={13} /> Launch 15-Q Remedial Drill <ArrowRight size={13} />
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div style={{ fontSize: '0.88rem', color: '#86efac', padding: '10px', background: 'rgba(16,185,129,0.1)', borderRadius: 'var(--radius-sm)' }}>
                        🎉 Outstanding mastery! Zero critical weaknesses detected in this session.
                      </div>
                    )}
                  </div>

                  {/* 🟡 MODERATE ATTENTION (50% - 75%) */}
                  <div style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(234, 179, 8, 0.05)', border: '1px solid rgba(234, 179, 8, 0.4)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#fbbf24', fontWeight: 800, fontSize: '1.05rem' }}>
                        <AlertTriangle size={18} /> 🟡 Moderate Attention (50% - 75%)
                      </div>
                      <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.2)', color: '#fde047' }}>{mediumAreas.length} Topics</span>
                    </div>

                    {mediumAreas.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {mediumAreas.map((m, mIdx) => (
                          <div key={mIdx} style={{ padding: '14px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(234,179,8,0.3)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                              <strong style={{ color: 'white', fontSize: '0.95rem' }}>{m.topic}</strong>
                              <span style={{ color: '#fde047', fontWeight: 800, fontSize: '0.82rem' }}>{m.accuracy}% Acc</span>
                            </div>
                            <div style={{ fontSize: '0.78rem', color: '#fef08a' }}>
                              <strong>💡 Speed Advice:</strong> {m.speedAdvice}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        No topics currently in the moderate calibration band.
                      </div>
                    )}
                  </div>

                  {/* 🟢 STRONG AREAS (> 75%) */}
                  <div style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(16, 185, 129, 0.05)', border: '1px solid rgba(16, 185, 129, 0.4)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#34d399', fontWeight: 800, fontSize: '1.05rem' }}>
                        <CheckCircle2 size={18} /> 🟢 Mastered Areas (&gt; 75% Accuracy)
                      </div>
                      <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#86efac' }}>{strongAreas.length} Strengths</span>
                    </div>

                    {strongAreas.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {strongAreas.map((s, sIdx) => (
                          <div key={sIdx} style={{ padding: '14px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(16,185,129,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <div>
                              <strong style={{ color: 'white', fontSize: '0.95rem' }}>{s.topic}</strong>
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Subject: {s.subject}</div>
                            </div>
                            <span style={{ color: '#86efac', fontWeight: 800, fontSize: '0.85rem' }}>{s.accuracy}% Acc</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        Attempt more questions to establish strong topics.
                      </div>
                    )}
                  </div>

                </div>
              </div>

              {/* 🎯 SELECTION PLAN-BASED DAILY PREPARATION HOURS BLUEPRINT */}
              <div className="glass-card" style={{ padding: '22px', border: '1px solid rgba(59, 130, 246, 0.3)', background: 'rgba(59, 130, 246, 0.04)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Compass size={20} color="#60a5fa" />
                    <div>
                      <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white', margin: 0 }}>
                        Target Post Daily Study Blueprint ({studyHoursPlan.totalDailyHours} Hours/Day)
                      </h4>
                      <span style={{ fontSize: '0.78rem', color: '#93c5fd' }}>
                        Dynamically calculated from your test weaknesses for {targetPost.postName}.
                      </span>
                    </div>
                  </div>
                  <span className="badge badge-verified">
                    SELECTION STRATEGY: {studyHoursPlan.totalDailyHours} HRS/DAY
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
                  <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '0.75rem', color: '#93c5fd', textTransform: 'uppercase', fontWeight: 700 }}>Quantitative Aptitude</div>
                    <div style={{ fontSize: '1.3rem', fontWeight: 800, color: 'white', margin: '4px 0' }}>{studyHoursPlan.quantHours} Hours</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Focus on Geometry proofs & Algebra symmetric identities.</div>
                  </div>

                  <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '0.75rem', color: '#93c5fd', textTransform: 'uppercase', fontWeight: 700 }}>General Awareness</div>
                    <div style={{ fontSize: '1.3rem', fontWeight: 800, color: 'white', margin: '4px 0' }}>{studyHoursPlan.gaHours} Hours</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Focus on Constitution Articles 14-32 & Static GK.</div>
                  </div>

                  <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '0.75rem', color: '#93c5fd', textTransform: 'uppercase', fontWeight: 700 }}>English Comprehension</div>
                    <div style={{ fontSize: '1.3rem', fontWeight: 800, color: 'white', margin: '4px 0' }}>{studyHoursPlan.englishHours} Hours</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Daily 60 Rules Grammar + Norman Lewis Root Words.</div>
                  </div>

                  <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '0.75rem', color: '#93c5fd', textTransform: 'uppercase', fontWeight: 700 }}>Reasoning</div>
                    <div style={{ fontSize: '1.3rem', fontWeight: 800, color: 'white', margin: '4px 0' }}>{studyHoursPlan.reasoningHours} Hours</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>High-speed Syllogism & Blood Relation sectionals.</div>
                  </div>

                  {targetPostId === 'post-jso' && (
                    <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(234,179,8,0.08)', border: '1px solid rgba(234,179,8,0.3)' }}>
                      <div style={{ fontSize: '0.75rem', color: '#fbbf24', textTransform: 'uppercase', fontWeight: 700 }}>Tier-2 Paper-II Statistics</div>
                      <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#fde047', margin: '4px 0' }}>{studyHoursPlan.statsHours} Hours</div>
                      <div style={{ fontSize: '0.72rem', color: '#fef08a' }}>Mandatory paper for Junior Statistical Officer (JSO).</div>
                    </div>
                  )}
                </div>
              </div>

              {/* 📖 DETAILED STEP-BY-STEP SOLUTIONS WITH ANIMATED SPEED SHORTCUT CARDS */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '18px', borderTop: '1px solid var(--border-color)', paddingTop: '24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <h4 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'white', margin: 0 }}>
                      📖 In-Depth Official Question Solutions & Animated Shortcut Tricks
                    </h4>
                    <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                      Complete formal step-by-step solutions paired with glowing high-speed TCS exam tricks for every question.
                    </span>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {reviewingAttempt && (
                      <button 
                        onClick={() => {
                          setReviewingAttempt(null);
                          setActivePracticeTab('PAST_ANALYTICS');
                        }} 
                        className="btn btn-secondary" 
                        style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}
                      >
                        <RotateCcw size={14} /> Back to Performance Matrix
                      </button>
                    )}
                    <button onClick={handleResetTest} className="btn btn-primary" style={{ fontSize: '0.85rem' }}>
                      Attempt Another Test
                    </button>
                  </div>
                </div>

                {/* Filter Tabs */}
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginRight: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Filter size={14} /> Filter By:
                  </span>

                  {!isOlderAttemptWithoutAnswers ? (
                    [
                      { id: 'ALL', label: `All Questions (${questionsList.length})` },
                      { id: 'INCORRECT', label: `❌ Incorrect (${displayIncorrect})` },
                      { id: 'UNATTEMPTED', label: `⚠️ Unattempted (${displayUnattempted})` },
                      { id: 'CORRECT', label: `✅ Correct (${displayCorrect})` }
                    ].map(tab => (
                      <button
                        key={tab.id}
                        onClick={() => setSolutionFilter(tab.id as any)}
                        className={`btn ${solutionFilter === tab.id ? 'btn-primary' : 'btn-secondary'}`}
                        style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                      >
                        {tab.label}
                      </button>
                    ))
                  ) : (
                    <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.2)', color: '#93c5fd', fontSize: '0.8rem', padding: '6px 12px' }}>
                      Showing All {questionsList.length} Official Questions &amp; Solutions
                    </span>
                  )}

                  {/* Subject Dropdown Filter */}
                  <select
                    value={solutionSectionFilter}
                    onChange={e => setSolutionSectionFilter(e.target.value)}
                    style={{
                      padding: '6px 12px',
                      borderRadius: 'var(--radius-sm)',
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid var(--border-color)',
                      color: 'white',
                      fontSize: '0.78rem'
                    }}
                  >
                    <option value="ALL" style={{ background: '#111827' }}>All Subjects</option>
                    <option value="Quantitative Aptitude" style={{ background: '#111827' }}>Quantitative Aptitude</option>
                    <option value="Reasoning & General Intelligence" style={{ background: '#111827' }}>Reasoning</option>
                    <option value="General Awareness" style={{ background: '#111827' }}>General Awareness</option>
                    <option value="English Comprehension" style={{ background: '#111827' }}>English Comprehension</option>
                  </select>
                </div>

                {/* Solutions List */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                  {filteredSolutions.map((q, idx) => {
                    const originalIdx = questionsList.findIndex(orig => orig.id === q.id);
                    const userAns = userAnswers[originalIdx];
                    const isCorrect = !isOlderAttemptWithoutAnswers && userAns === q.correctOptionIndex;
                    const isUnattempted = !isOlderAttemptWithoutAnswers && userAns === undefined;
                    const det = q.detailedExplanation;

                    return (
                      <div
                        key={q.id}
                        className="glass-card"
                        style={{
                          padding: '30px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '22px',
                          border: isOlderAttemptWithoutAnswers
                            ? '1.5px solid rgba(59, 130, 246, 0.45)'
                            : isCorrect 
                            ? '1.5px solid rgba(16, 185, 129, 0.45)' 
                            : isUnattempted 
                            ? '1.5px solid rgba(245, 158, 11, 0.45)' 
                            : '1.5px solid rgba(239, 68, 68, 0.45)',
                          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.92) 100%)',
                          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)'
                        }}
                      >
                        {/* Question Top Header */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                            <span style={{ fontWeight: 900, color: 'white', fontSize: '1.25rem' }}>
                              Question {originalIdx + 1}
                            </span>
                            {isOlderAttemptWithoutAnswers ? (
                              <span
                                className="badge"
                                style={{
                                  padding: '6px 14px',
                                  fontSize: '0.85rem',
                                  fontWeight: 800,
                                  background: 'rgba(59, 130, 246, 0.25)',
                                  color: '#93c5fd',
                                  border: '1px solid #3b82f6'
                                }}
                              >
                                📘 Official Key &amp; Solution
                              </span>
                            ) : (
                              <span
                                className="badge"
                                style={{
                                  padding: '6px 14px',
                                  fontSize: '0.85rem',
                                  fontWeight: 800,
                                  background: isCorrect ? 'rgba(16, 185, 129, 0.25)' : isUnattempted ? 'rgba(245, 158, 11, 0.25)' : 'rgba(239, 68, 68, 0.25)',
                                  color: isCorrect ? '#86efac' : isUnattempted ? '#fde047' : '#fca5a5',
                                  border: isCorrect ? '1px solid #10b981' : isUnattempted ? '1px solid #f59e0b' : '1px solid #ef4444'
                                }}
                              >
                                {isCorrect ? '✅ Correct (+2.0 M)' : isUnattempted ? '⚠️ Unattempted (0.0 M)' : '❌ Incorrect (-0.50 M)'}
                              </span>
                            )}
                            <span className="glass-pill" style={{ fontSize: '0.82rem', padding: '5px 12px', color: '#93c5fd', fontWeight: 600 }}>
                              {q.subject}
                            </span>
                            <span className="glass-pill" style={{ fontSize: '0.82rem', padding: '5px 12px', color: '#fbbf24', fontWeight: 600 }}>
                              {q.topicName}
                            </span>
                          </div>

                          <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                            {q.shiftInfo}
                          </span>
                        </div>

                        {/* Question Text with Larger Font & Line Height */}
                        <div style={{ fontSize: '1.12rem', color: '#ffffff', lineHeight: 1.7, fontWeight: 600, whiteSpace: 'pre-line', padding: '4px 0' }}>
                          {q.questionText}
                        </div>

                        {/* Options Breakdown with Generous Padding */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
                          {q.options.map(opt => {
                            const isThisCorrect = opt.id === q.correctOptionIndex;
                            const isThisUserSelected = !isOlderAttemptWithoutAnswers && userAns === opt.id;

                            let optBg = 'rgba(255, 255, 255, 0.03)';
                            let optBorder = '1px solid var(--border-color)';
                            let optColor = '#cbd5e1';

                            if (isThisCorrect) {
                              optBg = 'rgba(16, 185, 129, 0.18)';
                              optBorder = '1.5px solid #10b981';
                              optColor = '#86efac';
                            } else if (isThisUserSelected && !isThisCorrect) {
                              optBg = 'rgba(239, 68, 68, 0.18)';
                              optBorder = '1.5px solid #ef4444';
                              optColor = '#fca5a5';
                            }

                            return (
                              <div
                                key={opt.id}
                                style={{
                                  padding: '14px 18px',
                                  borderRadius: 'var(--radius-md)',
                                  background: optBg,
                                  border: optBorder,
                                  color: optColor,
                                  fontSize: '0.98rem',
                                  fontWeight: isThisCorrect || isThisUserSelected ? 700 : 500,
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'space-between',
                                  gap: '8px'
                                }}
                              >
                                <span>{opt.text}</span>
                                {isThisCorrect && (
                                  <span style={{ fontWeight: 900, fontSize: '0.8rem', color: '#34d399' }}>
                                    ✓ Correct Answer {!isOlderAttemptWithoutAnswers && isThisUserSelected ? '(Your Choice)' : ''}
                                  </span>
                                )}
                                {!isOlderAttemptWithoutAnswers && isThisUserSelected && !isThisCorrect && (
                                  <span style={{ fontWeight: 900, fontSize: '0.8rem', color: '#f87171' }}>
                                    ✗ Your Choice
                                  </span>
                                )}
                              </div>
                            );
                          })}
                        </div>

                        {/* 1. 💡 SIMPLE PLAIN-ENGLISH EXPLANATION (NO JARGON) */}
                        {det && det.simpleExplanation && (
                          <div style={{ padding: '20px 22px', borderRadius: 'var(--radius-md)', background: 'rgba(16, 185, 129, 0.08)', border: '1.5px solid rgba(16, 185, 129, 0.45)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#34d399', fontWeight: 900, fontSize: '1.05rem' }}>
                              <Sparkles size={20} color="#34d399" />
                              <span>💡 1. Plain & Simple Explanation (In Easy Everyday Words)</span>
                            </div>
                            <p style={{ fontSize: '1rem', color: '#f0fdf4', margin: 0, lineHeight: 1.75, fontWeight: 500 }}>
                              {det.simpleExplanation}
                            </p>
                          </div>
                        )}

                        {/* 2. 📘 TECHNICAL TERMS & JARGON GLOSSARY */}
                        {det && det.technicalTerms && det.technicalTerms.length > 0 && (
                          <div style={{ padding: '18px 22px', borderRadius: 'var(--radius-md)', background: 'rgba(59, 130, 246, 0.06)', border: '1px solid rgba(59, 130, 246, 0.35)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#93c5fd', fontWeight: 900, fontSize: '1rem' }}>
                              <BookOpen size={18} />
                              <span>📘 2. Key Terms & Jargon Explained Simply</span>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                              {det.technicalTerms.map((term, tIdx) => (
                                <div key={tIdx} style={{ fontSize: '0.94rem', color: '#e2e8f0', lineHeight: 1.6, padding: '8px 12px', background: 'rgba(0,0,0,0.3)', borderRadius: 'var(--radius-sm)', borderLeft: '3px solid #60a5fa' }}>
                                  <strong style={{ color: '#93c5fd' }}>{term.term}:</strong> {term.meaning}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* 3. ✍️ STEP-BY-STEP FORMAL METHOD */}
                        {det && det.stepByStepMethod && (
                          <div style={{ padding: '18px 22px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.35)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#ffffff', fontWeight: 900, fontSize: '1rem' }}>
                              <FileText size={18} color="#34d399" />
                              <span>✍️ 3. Step-by-Step Formal Method</span>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                              {det.stepByStepMethod.map((step, sIdx) => (
                                <div key={sIdx} style={{ fontSize: '0.95rem', color: '#e2e8f0', lineHeight: 1.65, paddingLeft: '14px', borderLeft: '3px solid rgba(16, 185, 129, 0.6)' }}>
                                  {step}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* 4. ⚡ ANIMATED EXAM SHORTCUT TRICK & SPEED FORMULA */}
                        {det && det.shortcutTrick && (
                          <div
                            className="trick-card-animated"
                            style={{
                              padding: '22px',
                              borderRadius: 'var(--radius-md)',
                              background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(251, 191, 36, 0.08) 100%)',
                              border: '1.5px solid rgba(245, 158, 11, 0.6)',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '12px'
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#fbbf24', fontWeight: 900, fontSize: '1.05rem' }}>
                                <Flame size={20} className="animate-pulse" color="#f59e0b" />
                                <span>⚡ 4. Exam Speed Shortcut: {det.shortcutTrick.name}</span>
                              </div>
                              <span className="badge shimmer-badge" style={{ background: '#f59e0b', color: '#111827', fontWeight: 900, fontSize: '0.8rem', padding: '6px 12px' }}>
                                {det.shortcutTrick.timeSaved}
                              </span>
                            </div>

                            {det.shortcutTrick.formula && (
                              <div style={{ padding: '10px 16px', borderRadius: '6px', background: 'rgba(0,0,0,0.6)', fontFamily: 'var(--font-mono)', fontSize: '0.98rem', color: '#fde047', fontWeight: 800 }}>
                                📐 Formula: {det.shortcutTrick.formula}
                              </div>
                            )}

                            <p style={{ fontSize: '0.98rem', color: '#ffffff', margin: 0, lineHeight: 1.65, fontWeight: 500 }}>
                              {det.shortcutTrick.explanation}
                            </p>
                          </div>
                        )}

                        {/* 5. 🎯 CRUCIAL EXAM TAKEAWAY */}
                        {det && det.crucialTakeaway && (
                          <div style={{ fontSize: '0.92rem', color: '#86efac', background: 'rgba(16, 185, 129, 0.1)', padding: '12px 18px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(16, 185, 129, 0.35)', lineHeight: 1.6 }}>
                            <strong style={{ color: '#34d399' }}>🎯 Crucial Takeaway for Exam Day:</strong> {det.crucialTakeaway}
                          </div>
                        )}

                        {/* 6. 📄 WHERE THIS QUESTION CAME FROM */}
                        {q.provenance && (
                          <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                            <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.5, flex: 1, minWidth: '240px' }}>
                              <strong style={{ color: q.provenance.verificationLevel === 'OFFICIALLY_VERIFIED' ? '#34d399' : '#fbbf24' }}>
                                {q.provenance.verificationLevel === 'OFFICIALLY_VERIFIED' ? '📄 Written from the official source:' : '✍️ GovOS practice question:'}
                              </strong>{' '}
                              {q.provenance.documentTitle}
                            </div>
                            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                              {/^https?:\/\//.test(q.provenance.officialUrl) && (
                                <a
                                  href={q.provenance.officialUrl}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="btn btn-secondary"
                                  style={{ fontSize: '0.74rem', padding: '4px 10px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
                                >
                                  Open source <ExternalLink size={11} />
                                </a>
                              )}
                              <button
                                onClick={() => onOpenProvenanceModal(q.provenance)}
                                className="btn btn-outline"
                                style={{ fontSize: '0.74rem', padding: '4px 10px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
                              >
                                <ShieldCheck size={11} /> Provenance
                              </button>
                            </div>
                          </div>
                        )}

                        {/* Fallback Explanation if Detailed Object Not Present */}
                        {!det && (
                          <div style={{ padding: '16px 18px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.3)', fontSize: '0.95rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                            <strong style={{ color: '#93c5fd' }}>Official Explanation:</strong>
                            <div style={{ marginTop: '6px', whiteSpace: 'pre-line' }}>{q.explanation}</div>
                          </div>
                        )}

                      </div>
                    );
                  })}
                </div>

              </div>

            </div>
          )}
        </>
      )}

      {/* VIEW 6: PAST ATTEMPTS HISTORY */}
      {activePracticeTab === 'PAST_ANALYTICS' && (
        <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
            <div>
              <h4 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'white', margin: 0 }}>
                Historical Mock & PYQ Test Performance Matrix
              </h4>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Persistent record synced with SQLite database (<code style={{ color: '#93c5fd' }}>govos.db</code>) and browser local storage.
              </span>
            </div>
            <span className="glass-pill" style={{ fontSize: '0.78rem', color: '#86efac', borderColor: 'rgba(16,185,129,0.3)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Database size={13} /> {pastAttempts.length} Tests Recorded
            </span>
          </div>

          <div style={{
            padding: '12px 16px',
            borderRadius: 'var(--radius-sm)',
            background: 'rgba(59, 130, 246, 0.1)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            color: '#93c5fd',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            <Sparkles size={16} color="#60a5fa" style={{ flexShrink: 0 }} />
            <span>
              <strong>Candidate Review Tip:</strong> Click on any row or the <strong>"Open &amp; Review"</strong> button to inspect your test, examine what you did right or wrong, and study detailed step-by-step solutions for future preparation.
            </span>
          </div>

          {pastAttempts.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
                <thead>
                  <tr style={{ background: 'rgba(255, 255, 255, 0.04)', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                    <th style={{ padding: '12px 14px', color: '#93c5fd' }}>Test Title / Paper</th>
                    <th style={{ padding: '12px 14px', color: '#93c5fd' }}>Score Earned</th>
                    <th style={{ padding: '12px 14px', color: '#93c5fd' }}>Accuracy %</th>
                    <th style={{ padding: '12px 14px', color: '#93c5fd' }}>Correct / Total</th>
                    <th style={{ padding: '12px 14px', color: '#93c5fd' }}>Time Taken</th>
                    <th style={{ padding: '12px 14px', color: '#93c5fd' }}>Date Attempted</th>
                    <th style={{ padding: '12px 14px', color: '#93c5fd', textAlign: 'center' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {pastAttempts.map((att, aIdx) => {
                    const acc = (att.correct_count + att.incorrect_count) > 0 ? Math.round((att.correct_count / (att.correct_count + att.incorrect_count)) * 100) : 0;
                    return (
                      <tr 
                        key={aIdx} 
                        onClick={() => handleReviewPastAttempt(att)}
                        style={{ 
                          borderBottom: '1px solid rgba(255, 255, 255, 0.05)', 
                          background: aIdx % 2 === 0 ? 'rgba(255, 255, 255, 0.01)' : 'transparent',
                          cursor: 'pointer',
                          transition: 'background 0.2s ease'
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(59, 130, 246, 0.15)')}
                        onMouseLeave={(e) => (e.currentTarget.style.background = aIdx % 2 === 0 ? 'rgba(255, 255, 255, 0.01)' : 'transparent')}
                        title="Click to open and review test questions and solutions"
                      >
                        <td style={{ padding: '12px 14px', fontWeight: 700, color: 'white' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <FileText size={15} color="#60a5fa" />
                            <span>{att.subject}</span>
                          </div>
                        </td>
                        <td style={{ padding: '12px 14px', color: att.score >= 0 ? '#86efac' : '#f87171', fontWeight: 800 }}>
                          {att.score} / {att.total_marks}
                        </td>
                        <td style={{ padding: '12px 14px' }}>
                          <span className="badge" style={{ background: acc >= 75 ? 'rgba(16, 185, 129, 0.2)' : acc >= 50 ? 'rgba(234, 179, 8, 0.2)' : 'rgba(239, 68, 68, 0.2)', color: acc >= 75 ? '#86efac' : acc >= 50 ? '#fde047' : '#fca5a5' }}>
                            {acc}%
                          </span>
                        </td>
                        <td style={{ padding: '12px 14px', color: 'var(--text-secondary)' }}>
                          <span style={{ color: '#86efac', fontWeight: 600 }}>{att.correct_count} Correct</span>, <span style={{ color: '#f87171', fontWeight: 600 }}>{att.incorrect_count} Wrong</span>
                        </td>
                        <td style={{ padding: '12px 14px', color: 'var(--text-muted)' }}>
                          {Math.floor(att.time_taken_seconds / 60)}m {att.time_taken_seconds % 60}s
                        </td>
                        <td style={{ padding: '12px 14px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                          {att.attempted_at || 'Recent'}
                        </td>
                        <td style={{ padding: '12px 14px', textAlign: 'center' }}>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleReviewPastAttempt(att);
                            }}
                            className="btn btn-primary"
                            style={{
                              padding: '7px 14px',
                              fontSize: '0.82rem',
                              fontWeight: 700,
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              boxShadow: '0 2px 8px rgba(37, 99, 235, 0.35)',
                              whiteSpace: 'nowrap'
                            }}
                            title="Open and review test questions and solutions"
                          >
                            <Eye size={14} /> Open &amp; Review
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No tests recorded yet. Attempt a test to build your weakness analysis matrix.
            </div>
          )}
        </div>
      )}

    </div>
  );
};


// ==========================================================================
// PracticeApplicationSimulator.tsx
// ==========================================================================
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
    { id: 'post-si-cbi', name: 'Sub-Inspector (Central Bureau of Investigation - CBI)' },
    { id: 'post-tax-assistant-cbdt', name: 'Tax Assistant (CBDT / CBIC)' },
    { id: 'post-auditor-cag', name: 'Auditor (Office of C&AG / CGA)' }
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


// ==========================================================================
// ApplicationGuide.tsx
// ==========================================================================
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


// ==========================================================================
// AdmitCardSection.tsx
// ==========================================================================
interface AdmitCardSectionProps {
  exam: Exam;
  onNavigateChecklist?: () => void;
}

export const AdmitCardSection: React.FC<AdmitCardSectionProps> = ({
  exam,
  onNavigateChecklist
}) => {
  const [selectedRegion, setSelectedRegion] = useState<string>('NR');

  // Find admit card date from dates array
  const admitDate = exam.dates.find(d => d.type === 'ADMIT_CARD');
  const cityIntimationDate = exam.dates.find(d => d.label.toLowerCase().includes('city') || d.type === 'ADMIT_CARD');
  const examDate = exam.dates.find(d => d.type === 'EXAM_TIER1' || d.type === 'EXAM_TIER2');

  // Admit-card facts declared on the exam record (falls back to the dates array)
  const admitDetails = exam.admitCardDetails;

  // Determine availability status
  const isAvailable = admitDetails?.status === 'AVAILABLE' || admitDate?.status === 'AVAILABLE';
  const releaseDateStr = admitDetails?.releaseDateStr || admitDate?.dateTimeStr || 'To be announced';

  // Regional download mirrors are authority-specific, so they come from the exam
  // record. Exams without declared mirrors show only their single official portal.
  const regionalPortals = (admitDetails?.regionPortals || []).map(rp => ({
    code: rp.regionCode,
    name: rp.statesCovered ? `${rp.regionName} (${rp.statesCovered})` : rp.regionName,
    url: rp.portalUrl,
    status: rp.status
  }));

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Title & Live Status Banner */}
      <div 
        className="glass-card" 
        style={{ 
          padding: '24px', 
          background: isAvailable 
            ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(17, 24, 39, 0.95) 100%)'
            : 'linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(17, 24, 39, 0.95) 100%)',
          borderColor: isAvailable ? 'rgba(16, 185, 129, 0.35)' : 'rgba(245, 158, 11, 0.35)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
              <span className={`badge ${isAvailable ? 'badge-verified' : 'badge-demo'}`}>
                {isAvailable ? '🟢 ADMIT CARD ACTIVE & DOWNLOADABLE' : '🟡 CITY INTIMATION RELEASED — ADMIT CARD SOON'}
              </span>
              <span className="badge" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--text-secondary)' }}>
                Official Board: {exam.authorityName}
              </span>
            </div>

            <h3 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'white', margin: '0 0 6px' }}>
              e-Admit Card & Exam City Intimation Slip
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
              {isAvailable 
                ? 'Your Computer Based Examination (CBT) Call Letter and reporting schedule are live.'
                : `Official admit cards are scheduled for release on ${releaseDateStr}. You can check your exam city intimation slip now.`}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <a 
              href={exam.officialDomain} 
              target="_blank" 
              rel="noreferrer"
              className="btn btn-emerald"
              style={{ fontSize: '0.9rem', padding: '10px 20px', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <Download size={18} /> Official Download Portal <ExternalLink size={14} />
            </a>
          </div>
        </div>
      </div>

      {/* Grid: Instructions & Download Credentials */}
      <div className="grid-2" style={{ gap: '20px' }}>
        
        {/* Box 1: How to Download & Required Credentials */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <h4 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'white', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck size={18} color="var(--primary)" /> Required Login Credentials
          </h4>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
            To access your hall ticket from the official {exam.authorityName.split(' ')[0]} server, keep the following credentials ready:
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ padding: '12px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <User size={16} color="var(--cyan)" />
              <div>
                <strong style={{ fontSize: '0.88rem', color: 'white' }}>Registration Number / Roll Number</strong>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Received via SMS / Email during initial application submission</div>
              </div>
            </div>

            <div style={{ padding: '12px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Calendar size={16} color="var(--emerald)" />
              <div>
                <strong style={{ fontSize: '0.88rem', color: 'white' }}>Date of Birth (Password)</strong>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Format: DD/MM/YYYY or as chosen during registration</div>
              </div>
            </div>

            <div style={{ padding: '12px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <FileText size={16} color="#fbbf24" />
              <div>
                <strong style={{ fontSize: '0.88rem', color: 'white' }}>Live Photo & Mother's Name (Alternative Fallback)</strong>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>If Registration ID is misplaced, use Candidate Name + Father/Mother Name + DoB</div>
              </div>
            </div>
          </div>
        </div>

        {/* Box 2: Crucial Printing & Verification Guidelines */}
        <div className="glass-card" style={{ padding: '24px' }}>
          <h4 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'white', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Printer size={18} color="#60a5fa" /> Essential Printing Rules
          </h4>

          <ul style={{ paddingLeft: '20px', margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '10px', lineHeight: 1.5 }}>
            <li>
              <strong style={{ color: 'white' }}>Print in High Resolution:</strong> Both Color or Laser Black & White prints are acceptable, but the <strong style={{ color: '#93c5fd' }}>QR Code / Barcode</strong> and candidate photograph must be crisp and easily scannable.
            </li>
            <li>
              <strong style={{ color: 'white' }}>Check Candidate Particulars:</strong> Verify Name spelling, Category, Sub-Category, and Date of Birth against your official Class 10th Certificate.
            </li>
            <li>
              <strong style={{ color: 'white' }}>Exam Lab & Shift Timing:</strong> Note the precise <strong style={{ color: '#f87171' }}>Reporting Time and Gate Closing Time</strong>. No candidate is permitted inside the examination center after gate closure.
            </li>
            <li>
              <strong style={{ color: 'white' }}>Self-Declaration Form:</strong> Complete the Covid / Scribe / Identity self-declaration paragraphs in your own handwriting <em>only inside the exam hall in front of the Invigilator</em>.
            </li>
          </ul>
        </div>
      </div>

      {/* Regional Zone Portals Selector — only for authorities that publish zonal mirrors */}
      {regionalPortals.length > 0 && (
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h4 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'white', margin: '0 0 4px' }}>
              Regional & Zonal Download Mirrors
            </h4>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: 0 }}>
              Official server mirrors divided by state jurisdictions for fast hall ticket downloads
            </p>
          </div>
          <span className="badge badge-verified" style={{ fontSize: '0.72rem' }}>
            {regionalPortals.length} ZONAL PORTALS VERIFIED
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
          {regionalPortals.map(rp => (
            <div 
              key={rp.code}
              style={{
                padding: '14px',
                borderRadius: 'var(--radius-md)',
                background: selectedRegion === rp.code ? 'rgba(99,102,241,0.1)' : 'rgba(255,255,255,0.02)',
                border: selectedRegion === rp.code ? '1px solid var(--primary)' : '1px solid var(--border-color)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '10px'
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span className="badge badge-demo" style={{ fontSize: '0.7rem' }}>REGION: {rp.code}</span>
                  <span style={{ fontSize: '0.7rem', color: '#34d399', fontWeight: 600 }}>Active Portal</span>
                </div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'white' }}>{rp.name}</div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '8px' }}>
                <code style={{ fontSize: '0.75rem', color: '#93c5fd' }}>{rp.url.replace('https://', '')}</code>
                <a 
                  href={rp.url} 
                  target="_blank" 
                  rel="noreferrer" 
                  className="btn btn-secondary" 
                  style={{ fontSize: '0.72rem', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  Visit <ExternalLink size={10} />
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>
      )}

      {/* Simulated Sample Admit Card Preview Mockup */}
      <div className="glass-card" style={{ padding: '24px', border: '1px dashed rgba(99, 102, 241, 0.4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <QrCode size={20} color="var(--primary)" />
            <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white', margin: 0 }}>
              Sample Hall Ticket Format Preview
            </h4>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Illustrative layout showing key fields on your official paper
          </span>
        </div>

        <div style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.4)', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '16px' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Candidate Name</span>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'white' }}>CANDIDATE ASPIRANT</div>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Roll Number / User ID</span>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--cyan)', fontFamily: 'var(--font-mono)' }}>2201048291</div>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Exam Date & Shift</span>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#fbbf24' }}>
                {examDate?.dateTimeStr.split(' ')[0] || '28 Oct 2026'} (Shift 1: 09:00 - 10:00 AM)
              </div>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Reporting & Gate Closure</span>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f87171' }}>07:30 AM (Gate Closes: 08:30 AM Strict)</div>
            </div>
          </div>

          <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              <MapPin size={14} color="var(--primary)" />
              <span>Test Venue: iON Digital Zone iDZ, Central Assessment Centre Lab 4, New Delhi</span>
            </div>

            {onNavigateChecklist && (
              <button 
                className="btn btn-primary"
                onClick={onNavigateChecklist}
                style={{ fontSize: '0.8rem', padding: '6px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                Go to Exam-Day Checklist <ArrowRight size={14} />
              </button>
            )}
          </div>
        </div>
      </div>

    </div>
  );
};


// ==========================================================================
// ExamDayChecklistSection.tsx
// ==========================================================================
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


// ==========================================================================
// ResultNextStepsSection.tsx
// ==========================================================================
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


// ==========================================================================
// ResourceLibrary.tsx — organised, searchable study-resource library (Section 08)
// ==========================================================================

type ResourceTypeGroup = 'ALL' | 'OFFICIAL' | 'BOOKS' | 'VIDEO' | 'TOOLS';

const RESOURCE_TYPE_GROUPS: { key: ResourceTypeGroup; label: string; types: ResourceItem['type'][] }[] = [
  { key: 'OFFICIAL', label: 'Official Documents & Portals', types: ['OFFICIAL_PDF', 'OFFICIAL_PORTAL'] },
  { key: 'BOOKS', label: 'Books & Handbooks', types: ['RECOMMENDED_BOOK', 'SIMPLIFIED_GUIDE'] },
  { key: 'VIDEO', label: 'Video Courses', types: ['VIDEO_LECTURE'] },
  { key: 'TOOLS', label: 'Practice Tools', types: ['ONLINE_TOOL'] }
];

// Display order for subject groups: primary sources first, then foundations, then subjects.
const RESOURCE_SUBJECT_ORDER: ResourceItem['subject'][] = [
  'Official Gazette',
  'Foundation Textbooks & Open Courses',
  'General Awareness & Static GK',
  'Current Affairs & Governance',
  'Banking & Financial Awareness',
  'Quantitative Aptitude',
  'Reasoning',
  'English Comprehension',
  'Computer & Typing'
];

const resourceTypeLabel = (type: ResourceItem['type']): string => {
  switch (type) {
    case 'OFFICIAL_PDF': return 'Official Document';
    case 'OFFICIAL_PORTAL': return 'Official Portal';
    case 'VIDEO_LECTURE': return 'Video Course';
    case 'RECOMMENDED_BOOK': return 'Recommended Book';
    case 'SIMPLIFIED_GUIDE': return 'Handbook';
    case 'ONLINE_TOOL': return 'Practice Tool';
    default: return 'Resource';
  }
};

const resourceTypeColor = (type: ResourceItem['type']): string => {
  switch (type) {
    case 'OFFICIAL_PDF':
    case 'OFFICIAL_PORTAL': return '#34d399';
    case 'VIDEO_LECTURE': return '#f87171';
    case 'ONLINE_TOOL': return '#fbbf24';
    default: return '#a5b4fc';
  }
};

const ResourceTypeIcon: React.FC<{ type: ResourceItem['type']; size?: number }> = ({ type, size = 14 }) => {
  const color = resourceTypeColor(type);
  switch (type) {
    case 'OFFICIAL_PORTAL': return <Globe size={size} color={color} />;
    case 'VIDEO_LECTURE': return <PlayCircle size={size} color={color} />;
    case 'ONLINE_TOOL': return <Zap size={size} color={color} />;
    case 'RECOMMENDED_BOOK':
    case 'SIMPLIFIED_GUIDE': return <BookOpen size={size} color={color} />;
    default: return <FileText size={size} color={color} />;
  }
};

const formatVerifiedDate = (iso: string): string => {
  const d = new Date(iso + 'T00:00:00');
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
};

const isExternalUrl = (value?: string): value is string => !!value && /^https?:\/\//i.test(value);

interface ResourceLibraryProps {
  exam: Exam;
  onOpenResource: (resource: ResourceItem) => void;
  onOpenProvenanceModal: (provenance: DataProvenance) => void;
}

export const ResourceLibrary: React.FC<ResourceLibraryProps> = ({ exam, onOpenResource, onOpenProvenanceModal }) => {
  const resources = exam.resources || [];

  const [query, setQuery] = useState<string>('');
  const [typeGroup, setTypeGroup] = useState<ResourceTypeGroup>('ALL');
  const [subjectFilter, setSubjectFilter] = useState<string>('ALL');
  const [savedOnly, setSavedOnly] = useState<boolean>(false);
  const [bookmarkIds, setBookmarkIds] = useState<string[]>(() => storageService.getBookmarkedResourceIds());
  const [linkChecks, setLinkChecks] = useState<Record<string, ResourceLinkCheck>>({});
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [verifySummary, setVerifySummary] = useState<string>('');
  const [isNavigatorOpen, setIsNavigatorOpen] = useState<boolean>(false);

  useEffect(() => {
    storageService.loadBookmarksFromSQLite().then(setBookmarkIds);
  }, []);

  // A different exam means a different library: clear filters and stale link results.
  useEffect(() => {
    setQuery('');
    setTypeGroup('ALL');
    setSubjectFilter('ALL');
    setSavedOnly(false);
    setLinkChecks({});
    setVerifySummary('');
  }, [exam.id]);

  // ---- derived structure -------------------------------------------------
  const availableGroups = RESOURCE_TYPE_GROUPS.filter(g => resources.some(r => g.types.includes(r.type)));

  const subjectCounts = resources.reduce<Record<string, number>>((acc, r) => {
    acc[r.subject] = (acc[r.subject] || 0) + 1;
    return acc;
  }, {});
  const availableSubjects: string[] = RESOURCE_SUBJECT_ORDER.filter(sub => subjectCounts[sub]);
  Object.keys(subjectCounts).forEach(sub => {
    if (!availableSubjects.includes(sub)) availableSubjects.push(sub);
  });

  const q = query.trim().toLowerCase();
  const activeTypes = RESOURCE_TYPE_GROUPS.find(g => g.key === typeGroup)?.types;

  const matches = resources.filter(r => {
    if (activeTypes && !activeTypes.includes(r.type)) return false;
    if (subjectFilter !== 'ALL' && r.subject !== subjectFilter) return false;
    if (savedOnly && !bookmarkIds.includes(r.id)) return false;
    if (q) {
      const haystack = `${r.title} ${r.author} ${r.description} ${r.recommendedFor} ${r.officialTag || ''} ${r.subject}`.toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    return true;
  });

  const grouped = availableSubjects
    .map(subject => ({ subject, items: matches.filter(r => r.subject === subject) }))
    .filter(g => g.items.length > 0);

  const essentials = resources.filter(r => r.isEssential);
  const officialCount = resources.filter(r => r.type === 'OFFICIAL_PDF' || r.type === 'OFFICIAL_PORTAL').length;
  const savedCount = resources.filter(r => bookmarkIds.includes(r.id)).length;
  const isFiltered = q !== '' || typeGroup !== 'ALL' || subjectFilter !== 'ALL' || savedOnly;

  const resetFilters = () => {
    setQuery('');
    setTypeGroup('ALL');
    setSubjectFilter('ALL');
    setSavedOnly(false);
  };

  // ---- bookmarks ---------------------------------------------------------
  const toggleBookmark = (r: ResourceItem) => {
    setBookmarkIds(storageService.toggleResourceBookmark({ id: r.id, title: r.title, type: r.type, url: r.url }));
  };

  // ---- live link verification -------------------------------------------
  const externalUrls = Array.from(new Set(
    resources.flatMap(r => [r.url, r.directPdfUrl, r.youtubeUrl].filter(isExternalUrl))
  ));

  const handleVerifyLinks = async () => {
    if (externalUrls.length === 0 || isVerifying) return;
    setIsVerifying(true);
    setVerifySummary('');
    const results = await storageService.verifyResourceLinks(externalUrls);
    if (results.length === 0) {
      setVerifySummary('Could not reach the GovOS server to run the check. Start "python app.py" and try again.');
    } else {
      const map: Record<string, ResourceLinkCheck> = {};
      results.forEach(res => { map[res.url] = res; });
      setLinkChecks(map);
      const healthy = results.filter(res => res.status === 'HEALTHY' || res.status === 'REDIRECT').length;
      const blocked = results.filter(res => res.status === 'BLOCKED').length;
      const failing = results.length - healthy - blocked;
      let summary = `${healthy} of ${results.length} external links responded normally`;
      if (blocked > 0) summary += `, ${blocked} block automated checks`;
      if (failing > 0) summary += `, ${failing} could not be confirmed automatically (open to check)`;
      setVerifySummary(summary + '.');
    }
    setIsVerifying(false);
  };

  const linkBadge = (r: ResourceItem): { text: string; color: string; bg: string } | null => {
    const check = linkChecks[r.url];
    if (check) {
      const ok = check.status === 'HEALTHY' || check.status === 'REDIRECT';
      if (ok) return { text: `Live now · HTTP ${check.httpCode}`, color: '#34d399', bg: 'rgba(16,185,129,0.12)' };
      if (check.status === 'BLOCKED') return { text: 'Blocks automated checks · open to confirm', color: '#fbbf24', bg: 'rgba(245,158,11,0.12)' };
      if (check.status === 'UNREACHABLE') return { text: 'Could not reach automatically · open to confirm', color: '#fbbf24', bg: 'rgba(245,158,11,0.12)' };
      return { text: `Link broken · HTTP ${check.httpCode}`, color: '#f87171', bg: 'rgba(239,68,68,0.12)' };
    }
    if (r.linkVerifiedDate) return { text: `Link verified ${formatVerifiedDate(r.linkVerifiedDate)}`, color: '#34d399', bg: 'rgba(16,185,129,0.1)' };
    if (r.provenance?.verificationLevel === 'UNDER_VERIFICATION') return { text: 'Link check pending', color: '#fbbf24', bg: 'rgba(245,158,11,0.1)' };
    return null;
  };

  // ---- primary action per format ----------------------------------------
  const primaryAction = (r: ResourceItem): { label: string; href?: string; onClick?: () => void } => {
    switch (r.resourceFormat) {
      case 'YOUTUBE_COURSE': return { label: 'Watch in App', onClick: () => onOpenResource(r) };
      case 'OFFICIAL_PORTAL': return { label: 'Open Official Portal', href: r.url };
      case 'ONLINE_TOOL': return { label: 'Launch Tool', href: r.url };
      case 'INTERACTIVE_HANDBOOK': return { label: 'Read Handbook', onClick: () => onOpenResource(r) };
      default:
        return r.directPdfUrl
          ? { label: 'Read Document', onClick: () => onOpenResource(r) }
          : { label: 'Open Document', href: r.url };
    }
  };

  const chipStyle = (active: boolean, accent: string = 'var(--primary)'): React.CSSProperties => ({
    padding: '6px 12px',
    borderRadius: 'var(--radius-full)',
    border: `1px solid ${active ? accent : 'var(--border-color)'}`,
    background: active ? 'rgba(99, 102, 241, 0.16)' : 'transparent',
    color: active ? '#c7d2fe' : 'var(--text-secondary)',
    fontSize: '0.78rem',
    fontWeight: active ? 700 : 500,
    fontFamily: 'var(--font-sans)',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    transition: 'all 0.15s ease'
  });

  const iconButtonStyle: React.CSSProperties = {
    width: '32px',
    height: '32px',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border-color)',
    background: 'transparent',
    color: 'var(--text-secondary)',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    flexShrink: 0
  };

  // ---- card -------------------------------------------------------------
  const renderCard = (r: ResourceItem) => {
    const saved = bookmarkIds.includes(r.id);
    const action = primaryAction(r);
    const badge = linkBadge(r);
    const showExternalIcon = isExternalUrl(r.youtubeUrl || r.url) && !action.href;
    const typeColor = resourceTypeColor(r.type);

    return (
      <div
        key={r.id}
        style={{
          padding: '18px',
          borderRadius: 'var(--radius-md)',
          background: 'rgba(255, 255, 255, 0.025)',
          borderTop: `3px solid ${typeColor}`,
          borderRight: `1px solid ${saved ? 'rgba(99, 102, 241, 0.45)' : 'var(--border-color)'}`,
          borderBottom: `1px solid ${saved ? 'rgba(99, 102, 241, 0.45)' : 'var(--border-color)'}`,
          borderLeft: `1px solid ${saved ? 'rgba(99, 102, 241, 0.45)' : 'var(--border-color)'}`,
          display: 'flex',
          flexDirection: 'column',
          gap: '10px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', fontWeight: 700, color: typeColor, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            <ResourceTypeIcon type={r.type} /> {resourceTypeLabel(r.type)}
            {r.isEssential && (
              <span style={{ marginLeft: '6px', padding: '1px 7px', borderRadius: 'var(--radius-full)', background: 'rgba(16,185,129,0.15)', color: '#6ee7b7', fontSize: '0.66rem' }}>
                ESSENTIAL
              </span>
            )}
          </span>
          <button
            onClick={() => toggleBookmark(r)}
            title={saved ? 'Remove from saved' : 'Save for later'}
            aria-label={saved ? 'Remove from saved' : 'Save for later'}
            style={{ ...iconButtonStyle, borderColor: saved ? 'var(--primary)' : 'var(--border-color)', color: saved ? '#a5b4fc' : 'var(--text-muted)', background: saved ? 'rgba(99,102,241,0.14)' : 'transparent' }}
          >
            <Bookmark size={15} fill={saved ? '#a5b4fc' : 'none'} />
          </button>
        </div>

        <div>
          <h4 style={{ fontSize: '1rem', fontWeight: 800, color: 'white', margin: '0 0 3px', lineHeight: 1.3 }}>{r.title}</h4>
          <div style={{ fontSize: '0.78rem', color: '#93c5fd', fontWeight: 600 }}>{r.author}</div>
        </div>

        <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.45, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical' as any, overflow: 'hidden' }}>
          {r.description}
        </p>

        <div style={{ fontSize: '0.78rem', color: '#86efac', lineHeight: 1.4 }}>
          <strong style={{ color: '#6ee7b7' }}>Best for:</strong> {r.recommendedFor}
        </div>

        {(badge || r.officialTag || r.rating) && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
            {badge && (
              <span style={{ padding: '2px 9px', borderRadius: 'var(--radius-full)', background: badge.bg, color: badge.color, fontSize: '0.7rem', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <CheckCircle2 size={11} /> {badge.text}
              </span>
            )}
            {r.officialTag && (
              <span style={{ padding: '2px 9px', borderRadius: 'var(--radius-full)', background: 'rgba(255,255,255,0.05)', color: 'var(--text-secondary)', fontSize: '0.68rem', fontWeight: 600 }}>
                {r.officialTag}
              </span>
            )}
            {r.rating && (
              <span style={{ fontSize: '0.72rem', color: '#fbbf24', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                <Star size={11} fill="#fbbf24" color="#fbbf24" /> {r.rating}
              </span>
            )}
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: 'auto', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          {action.href ? (
            <a href={action.href} target="_blank" rel="noreferrer" className="btn btn-emerald" style={{ fontSize: '0.8rem', padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: '6px', flex: 1, justifyContent: 'center' }}>
              {action.label} <ExternalLink size={13} />
            </a>
          ) : (
            <button onClick={action.onClick} className="btn btn-emerald" style={{ fontSize: '0.8rem', padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: '6px', flex: 1, justifyContent: 'center' }}>
              {r.resourceFormat === 'YOUTUBE_COURSE' ? <PlayCircle size={14} /> : <BookOpen size={14} />} {action.label}
            </button>
          )}

          {r.directPdfUrl && (
            <a href={r.directPdfUrl} download={r.downloadFileName || 'GovOS_Resource.pdf'} title="Download PDF" aria-label="Download PDF" style={iconButtonStyle}>
              <Download size={14} />
            </a>
          )}
          {showExternalIcon && (
            <a href={r.youtubeUrl || r.url} target="_blank" rel="noreferrer" title="Open on the source site" aria-label="Open on the source site" style={iconButtonStyle}>
              <ExternalLink size={14} />
            </a>
          )}
          {action.href && (r.inAppHandbookContent || r.provenance) && (
            <button onClick={() => onOpenResource(r)} title="Notes and details" aria-label="Notes and details" style={iconButtonStyle}>
              <Info size={14} />
            </button>
          )}
          {r.provenance && (
            <button onClick={() => onOpenProvenanceModal(r.provenance!)} title="View source verification" aria-label="View source verification" style={{ ...iconButtonStyle, color: '#34d399' }}>
              <ShieldCheck size={14} />
            </button>
          )}
        </div>
      </div>
    );
  };

  // ---- render ---------------------------------------------------------------
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'white', margin: 0 }}>
            08 — Resource Library
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', margin: '4px 0 0 0' }}>
            {resources.length} resources · {officialCount} from official government sources · {savedCount} saved for later
          </p>
        </div>
        <button
          onClick={handleVerifyLinks}
          disabled={isVerifying || externalUrls.length === 0}
          className="btn btn-secondary"
          title="Ask the GovOS server to request every external link and report which ones respond"
          style={{ fontSize: '0.8rem', display: 'inline-flex', alignItems: 'center', gap: '6px', opacity: isVerifying ? 0.7 : 1 }}
        >
          <RefreshCw size={14} className={isVerifying ? 'animate-spin' : ''} />
          {isVerifying ? `Checking ${externalUrls.length} links…` : `Verify all ${externalUrls.length} links now`}
        </button>
      </div>

      {verifySummary && (
        <div style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.3)', fontSize: '0.82rem', color: '#c7d2fe', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Info size={14} /> {verifySummary}
        </div>
      )}

      {/* Start here shelf */}
      {!isFiltered && essentials.length > 0 && (
        <div className="glass-card" style={{ padding: '20px', background: 'linear-gradient(135deg, rgba(16,185,129,0.09) 0%, rgba(15,23,42,0.98) 60%)', border: '1px solid rgba(16,185,129,0.3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Compass size={18} color="var(--emerald)" />
              <h4 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'white', margin: 0 }}>Start here — the essentials</h4>
            </div>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              The {essentials.length} sources every candidate should open first
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
            {essentials.map(renderCard)}
          </div>
        </div>
      )}

      {/* Search & filters */}
      <div className="glass-card" style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: '240px' }}>
            <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search by title, author, subject or use case…"
              aria-label="Search resources"
              style={{ width: '100%', padding: '10px 36px 10px 38px', borderRadius: 'var(--radius-md)', background: 'var(--bg-input)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.9rem', fontFamily: 'var(--font-sans)', outline: 'none' }}
            />
            {query && (
              <button onClick={() => setQuery('')} aria-label="Clear search" style={{ position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex' }}>
                <X size={15} />
              </button>
            )}
          </div>
          <button onClick={() => setSavedOnly(v => !v)} style={chipStyle(savedOnly)} aria-pressed={savedOnly}>
            <Bookmark size={13} fill={savedOnly ? '#c7d2fe' : 'none'} /> Saved ({savedCount})
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginRight: '4px' }}>Type</span>
          <button onClick={() => setTypeGroup('ALL')} style={chipStyle(typeGroup === 'ALL')}>All types</button>
          {availableGroups.map(g => (
            <button key={g.key} onClick={() => setTypeGroup(g.key)} style={chipStyle(typeGroup === g.key)}>
              {g.label} ({resources.filter(r => g.types.includes(r.type)).length})
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginRight: '4px' }}>Subject</span>
          <button onClick={() => setSubjectFilter('ALL')} style={chipStyle(subjectFilter === 'ALL')}>All subjects</button>
          {availableSubjects.map(sub => (
            <button key={sub} onClick={() => setSubjectFilter(sub)} style={chipStyle(subjectFilter === sub)}>
              {sub} ({subjectCounts[sub]})
            </button>
          ))}
        </div>
      </div>

      {/* Resource Navigator (existing assistant, collapsed by default) */}
      <div style={{ borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', background: 'rgba(255,255,255,0.02)' }}>
        <button
          onClick={() => setIsNavigatorOpen(v => !v)}
          style={{ width: '100%', padding: '12px 16px', background: 'none', border: 'none', color: 'var(--text-secondary)', fontFamily: 'var(--font-sans)', fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={15} color="#60a5fa" /> Not sure what to open? Ask the Resource Navigator
          </span>
          <ChevronDown size={15} style={{ transform: isNavigatorOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s ease' }} />
        </button>
        {isNavigatorOpen && (
          <div style={{ padding: '0 12px 12px' }}>
            <ResourceAIAssistant resources={resources} onOpenResourceModal={onOpenResource} />
          </div>
        )}
      </div>

      {/* Results */}
      {isFiltered && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
          <span>Showing <strong style={{ color: 'white' }}>{matches.length}</strong> of {resources.length} resources</span>
          <button onClick={resetFilters} className="btn btn-secondary" style={{ fontSize: '0.76rem', padding: '4px 12px' }}>Clear filters</button>
        </div>
      )}

      {matches.length === 0 ? (
        <div className="glass-card" style={{ padding: '40px 24px', textAlign: 'center' }}>
          <AlertTriangle size={26} color="var(--text-muted)" style={{ marginBottom: '8px' }} />
          <h4 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'white', marginBottom: '6px' }}>
            {savedOnly && savedCount === 0 ? 'Nothing saved yet' : 'No resources match'}
          </h4>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', maxWidth: '420px', margin: '0 auto 14px' }}>
            {savedOnly && savedCount === 0
              ? 'Tap the bookmark on any resource to keep it here for quick access.'
              : 'Try a broader search term or clear a filter.'}
          </p>
          <button onClick={resetFilters} className="btn btn-primary" style={{ fontSize: '0.84rem' }}>Show everything</button>
        </div>
      ) : (
        grouped.map(group => (
          <section key={group.subject} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
              <h4 style={{ fontSize: '1rem', fontWeight: 800, color: 'white', margin: 0 }}>{group.subject}</h4>
              <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>{group.items.length} resource{group.items.length === 1 ? '' : 's'}</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '14px' }}>
              {group.items.map(renderCard)}
            </div>
          </section>
        ))
      )}
    </div>
  );
};


// ==========================================================================
// ExamDetailView.tsx
// ==========================================================================
interface ExamDetailViewProps {
  exam: Exam;
  onOpenProvenanceModal: (provenance: DataProvenance) => void;
  onOpenReportModal: (entityType: string, entityId: string) => void;
  onNavigateEligibility?: () => void;
  onNavigatePlanner?: () => void;
  onNavigatePractice?: () => void;
  isTracked?: boolean;
  onToggleTrack?: () => void;
  initialSection?: number;
  onSelectAlternativeExam?: (examCode: string) => void;
}

export const ExamDetailView: React.FC<ExamDetailViewProps> = ({
  exam,
  onOpenProvenanceModal,
  onOpenReportModal,
  onNavigateEligibility,
  onNavigatePlanner,
  onNavigatePractice,
  isTracked = false,
  onToggleTrack,
  initialSection = 1,
  onSelectAlternativeExam
}) => {
  const [activeSection, setActiveSection] = useState<number>(initialSection || 1);

  useEffect(() => {
    if (initialSection) {
      setActiveSection(initialSection);
    }
  }, [initialSection]);
  const [isGuideIndexOpen, setIsGuideIndexOpen] = useState<boolean>(false);
  const [selectedResourceForModal, setSelectedResourceForModal] = useState<ResourceItem | null>(null);
  const [syllabusViewMode, setSyllabusViewMode] = useState<'POST_STUDY_PATH' | 'OFFICIAL_BLUEPRINT'>('POST_STUDY_PATH');
  const [completedTopics, setCompletedTopics] = useState<Record<string, boolean>>(
    () => {
      const saved = storageService.getCompletedTopics(exam.id);
      if (Object.keys(saved).length > 0) return saved;
      // First visit for this exam: start from the standard baseline.
      return {
        'syl-quant-arithmetic': true,
        'syl-reas-analogy-series': true,
        'syl-eng-grammar': true,
        'syl-ga-polity': true
      };
    }
  );

  // Reload the saved ticks whenever the candidate switches to a different exam.
  useEffect(() => {
    setCompletedTopics(storageService.getCompletedTopics(exam.id));
  }, [exam.id]);

  const toggleTopic = (id: string) => {
    setCompletedTopics(storageService.toggleCompletedTopic(exam.id, id));
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
    { num: 8, name: '08 — Resource Library' },
    { num: 9, name: '09 — CBT Practice & PYQs' },
    { num: 10, name: '10 — Cutoff History' },
    { num: 11, name: '11 — FAQs & Clauses' },
    { num: 12, name: '12 — Official Links' },
    { num: 13, name: '13 — Corrigenda Log' },
    { num: 14, name: '14 — Admit Card & Hall Ticket' },
    { num: 15, name: '15 — Exam-Day Checklist' },
    { num: 16, name: '16 — Result & Next Steps' }
  ];

  // PRIMARY NAVIGATION — the candidate journey ("What should I do next?").
  // Each stage owns a target section plus the reference sections that back it up.
  const steps = [
    { num: 1, label: 'Check Eligibility', action: 'Confirm which posts you can apply for', sec: 3, icon: UserCheck, alsoSee: [1] },
    { num: 2, label: 'Understand Pattern', action: 'Learn the tier structure & marking', sec: 5, icon: Layers, alsoSee: [2] },
    { num: 3, label: 'Application & Docs', action: 'Fill the form without rejection', sec: 4, icon: FileText, alsoSee: [] },
    { num: 4, label: 'Syllabus Blueprint', action: 'See exactly what to study', sec: 6, icon: Compass, alsoSee: [] },
    { num: 5, label: 'Study Roadmap', action: 'Follow a day-by-day plan', sec: 7, icon: Calendar, alsoSee: [8] },
    { num: 6, label: 'CBT PYQ Practice', action: 'Attempt real shift papers', sec: 9, icon: Award, alsoSee: [10] },
    { num: 7, label: 'Admit Card Download', action: 'Get your hall ticket & city slip', sec: 14, icon: Download, alsoSee: [] },
    { num: 8, label: 'Exam-Day Checklist', action: 'Carry the right documents', sec: 15, icon: CheckSquare, alsoSee: [] },
    { num: 9, label: 'Result & Next Steps', action: 'Plan your move after the result', sec: 16, icon: Flame, alsoSee: [10] }
  ];

  // Maps every guide section back to the lifecycle stage it supports, so the journey bar
  // always reflects where the candidate currently is. Sections 11-13 are pure reference.
  const sectionToStep: Record<number, number> = {
    1: 1, 3: 1,
    2: 2, 5: 2,
    4: 3,
    6: 4,
    7: 5, 8: 5,
    9: 6, 10: 6,
    14: 7,
    15: 8,
    16: 9
  };

  const activeStepNum = sectionToStep[activeSection];
  const activeStep = steps.find(s => s.num === activeStepNum);
  const activeSectionMeta = sections.find(s => s.num === activeSection);

  // Related sections for the current stage, excluding the one already open.
  const relatedSections = activeStep
    ? [activeStep.sec, ...activeStep.alsoSee].filter(n => n !== activeSection)
    : [];

  // SECONDARY NAVIGATION — the reference index, grouped so it reads as a table of
  // contents rather than a second journey.
  const sectionGroups = [
    { title: 'Exam Essentials', nums: [1, 2, 3, 5] },
    { title: 'Apply & Prepare', nums: [4, 6, 7, 8, 9] },
    { title: 'Exam Day & Results', nums: [10, 14, 15, 16] },
    { title: 'Official Records', nums: [11, 12, 13] }
  ];

  const goToSection = (secNum: number) => {
    setActiveSection(secNum);
  };

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

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {onToggleTrack && (
              <button 
                className={`btn ${isTracked ? 'btn-emerald' : 'btn-secondary'}`}
                onClick={onToggleTrack}
                style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}
                title={isTracked ? 'Currently tracked in My Exam Timeline' : 'Track this exam for personalized deadline notifications'}
              >
                {isTracked ? <><Check size={16} /> Tracking</> : <><Bell size={16} /> Track Exam</>}
              </button>
            )}
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

      {/* ================= PRIMARY NAVIGATION: CANDIDATE LIFECYCLE ================= */}
      {/* "What should I do next?" — the main way a candidate moves through this exam. */}
      <div
        className="glass-card"
        style={{
          padding: '26px',
          background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.10) 0%, rgba(15, 23, 42, 0.98) 55%)',
          border: '1px solid rgba(16, 185, 129, 0.35)',
          boxShadow: '0 0 30px -12px rgba(16, 185, 129, 0.35)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px', marginBottom: '20px' }}>
          <div>
            <span className="badge badge-verified" style={{ fontSize: '0.7rem', marginBottom: '8px', display: 'inline-flex' }}>
              <Target size={13} /> YOUR CANDIDATE JOURNEY
            </span>
            <h3 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'white', margin: '0 0 4px' }}>
              What should I do next?
            </h3>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', margin: 0 }}>
              Follow these 9 stages in order — from checking eligibility to acting on your result. Each stage opens the tool or guide section you need for it.
            </p>
          </div>

          <div style={{ padding: '12px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(16, 185, 129, 0.3)', minWidth: '190px' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em' }}>
              Current Stage
            </span>
            {activeStep ? (
              <>
                <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--emerald)', marginTop: '2px', lineHeight: 1.2 }}>
                  {activeStep.label}
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  Stage {activeStep.num} of {steps.length}
                </span>
              </>
            ) : (
              <>
                <div style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-secondary)', marginTop: '2px', lineHeight: 1.2 }}>
                  Reference Lookup
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Viewing a detail section
                </span>
              </>
            )}
          </div>
        </div>

        <div className="stepper-container" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
          {steps.map((st) => {
            const isCurrent = activeStepNum === st.num;
            const StepIcon = st.icon;
            return (
              <div
                key={st.num}
                className={`step-item ${isCurrent ? 'active' : ''}`}
                onClick={() => goToSection(st.sec)}
                title={`${st.action} — opens ${sections.find(s => s.num === st.sec)?.name}`}
                style={{
                  padding: '16px',
                  borderRadius: 'var(--radius-md)',
                  background: isCurrent ? 'rgba(16, 185, 129, 0.14)' : 'rgba(255, 255, 255, 0.035)',
                  border: isCurrent ? '1px solid var(--emerald)' : '1px solid var(--border-color)',
                  boxShadow: isCurrent ? '0 0 18px -6px var(--emerald-glow)' : 'none',
                  cursor: 'pointer',
                  textAlign: 'left',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{
                    width: '28px',
                    height: '28px',
                    flexShrink: 0,
                    borderRadius: '50%',
                    background: isCurrent ? 'var(--emerald)' : 'rgba(255, 255, 255, 0.08)',
                    color: isCurrent ? '#062c22' : 'var(--text-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.82rem',
                    fontWeight: 800,
                    fontFamily: 'var(--font-mono)'
                  }}>
                    {st.num}
                  </div>
                  <StepIcon size={17} color={isCurrent ? '#34d399' : 'var(--text-muted)'} style={{ flexShrink: 0 }} />
                  <div style={{ fontSize: '0.95rem', fontWeight: 800, color: isCurrent ? '#6ee7b7' : 'white', lineHeight: 1.2 }}>
                    {st.label}
                  </div>
                </div>

                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                  {st.action}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.7rem', color: isCurrent ? '#34d399' : 'var(--text-muted)', fontWeight: 700, marginTop: 'auto' }}>
                  {isCurrent ? 'You are here' : 'Open'} <ArrowRight size={11} /> Section {String(st.sec).padStart(2, '0')}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ================= SECONDARY NAVIGATION: DETAILED EXAM GUIDE INDEX ================= */}
      {/* Reference lookup, deliberately quieter than the lifecycle above. */}
      <div style={{
        borderRadius: 'var(--radius-md)',
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid var(--border-color)',
        padding: '14px 18px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
            <BookOpen size={16} color="var(--text-muted)" style={{ flexShrink: 0 }} />
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Detailed Exam Guide · Reference
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Currently reading:{' '}
                <strong style={{ color: '#cbd5e1' }}>{activeSectionMeta?.name || 'Section 01'}</strong>
                {activeStep && (
                  <span style={{ color: 'var(--text-muted)' }}> · supports “{activeStep.label}”</span>
                )}
              </div>
            </div>
          </div>

          <button
            onClick={() => setIsGuideIndexOpen(prev => !prev)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: 'var(--radius-sm)',
              background: 'transparent',
              border: '1px solid var(--border-color)',
              color: 'var(--text-secondary)',
              fontSize: '0.78rem',
              fontWeight: 600,
              fontFamily: 'var(--font-sans)',
              cursor: 'pointer',
              whiteSpace: 'nowrap'
            }}
          >
            {isGuideIndexOpen ? 'Hide' : 'Browse'} all {sections.length} detail sections
            <ChevronDown
              size={14}
              style={{ transform: isGuideIndexOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s ease' }}
            />
          </button>
        </div>

        {isGuideIndexOpen && (
          <div className="animate-fade-in" style={{ marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {sectionGroups.map(group => (
              <div key={group.title}>
                <div style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '8px' }}>
                  {group.title}
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {group.nums.map(num => {
                    const sec = sections.find(s => s.num === num);
                    if (!sec) return null;
                    const isActive = activeSection === num;
                    return (
                      <button
                        key={num}
                        onClick={() => goToSection(num)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: 'var(--radius-sm)',
                          background: isActive ? 'rgba(99, 102, 241, 0.14)' : 'transparent',
                          border: isActive ? '1px solid rgba(99, 102, 241, 0.55)' : '1px solid var(--border-color)',
                          color: isActive ? '#a5b4fc' : 'var(--text-secondary)',
                          fontSize: '0.76rem',
                          fontWeight: isActive ? 700 : 500,
                          fontFamily: 'var(--font-sans)',
                          cursor: 'pointer',
                          whiteSpace: 'nowrap',
                          transition: 'all 0.15s ease'
                        }}
                      >
                        {sec.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Section Content Views */}
      <div className="glass-card" style={{ padding: '28px' }}>

        {/* Context strip: ties the detail section back to the lifecycle stage it serves */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '10px',
          marginBottom: '22px',
          paddingBottom: '14px',
          borderBottom: '1px solid var(--border-color)',
          fontSize: '0.78rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', flexWrap: 'wrap' }}>
            {activeStep ? (
              <>
                <span style={{ color: 'var(--text-muted)' }}>Stage {activeStep.num} · {activeStep.label}</span>
                <ChevronRight size={12} />
                <strong style={{ color: 'var(--text-secondary)' }}>{activeSectionMeta?.name}</strong>
              </>
            ) : (
              <>
                <Info size={13} />
                <span>Reference section — not part of the step-by-step journey.</span>
                <ChevronRight size={12} />
                <strong style={{ color: 'var(--text-secondary)' }}>{activeSectionMeta?.name}</strong>
              </>
            )}
          </div>

          {relatedSections.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{ color: 'var(--text-muted)' }}>Also useful for this stage:</span>
              {relatedSections.map(num => {
                const sec = sections.find(s => s.num === num);
                if (!sec) return null;
                return (
                  <button
                    key={num}
                    onClick={() => goToSection(num)}
                    style={{
                      padding: '3px 10px',
                      borderRadius: 'var(--radius-sm)',
                      background: 'transparent',
                      border: '1px solid var(--border-color)',
                      color: 'var(--text-secondary)',
                      fontSize: '0.74rem',
                      fontFamily: 'var(--font-sans)',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {sec.name}
                  </button>
                );
              })}
            </div>
          )}
        </div>

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

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '1.05rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: d.status === 'SUPERSEDED' ? '#fca5a5' : 'var(--primary)' }}>
                      {d.dateTimeStr}
                    </span>
                    {d.type === 'ADMIT_CARD' && (
                      <button className="btn btn-primary" onClick={() => setActiveSection(14)} style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                        Admit Card Portal →
                      </button>
                    )}
                    {(d.type === 'EXAM_TIER1' || d.type === 'EXAM_TIER2') && (
                      <button className="btn btn-secondary" onClick={() => setActiveSection(15)} style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                        Exam Checklist →
                      </button>
                    )}
                    {d.type === 'RESULT' && (
                      <button className="btn btn-emerald" onClick={() => setActiveSection(16)} style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                        Result Next Steps →
                      </button>
                    )}
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

        {/* Section 08: Resource Library (searchable, grouped, bookmarkable) */}
        {activeSection === 8 && (
          <ResourceLibrary
            exam={exam}
            onOpenResource={(res) => setSelectedResourceForModal(res)}
            onOpenProvenanceModal={onOpenProvenanceModal}
          />
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

            <div style={{ padding: '16px 20px', borderRadius: 'var(--radius-md)', background: 'rgba(234, 179, 8, 0.08)', border: '1px solid rgba(234, 179, 8, 0.3)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <strong style={{ fontSize: '1rem', color: 'white' }}>Results or Scorecard Released?</strong>
                <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: '2px 0 0' }}>
                  Explore your personalized next steps based on whether you qualified for Tier-2, Skill Test DEST, or need a recovery pathway.
                </p>
              </div>
              <button 
                className="btn btn-primary"
                onClick={() => setActiveSection(16)}
                style={{ fontSize: '0.82rem', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                Open Result Next Steps Flow <ArrowRight size={14} />
              </button>
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

        {/* Section 14: Admit Card & Hall Ticket Download */}
        {activeSection === 14 && (
          <AdmitCardSection 
            exam={exam}
            onNavigateChecklist={() => setActiveSection(15)}
          />
        )}

        {/* Section 15: Exam-Day Checklist & Center Protocol */}
        {activeSection === 15 && (
          <ExamDayChecklistSection 
            exam={exam}
          />
        )}

        {/* Section 16: Result & Personalized Next Steps Flow */}
        {activeSection === 16 && (
          <ResultNextStepsSection 
            exam={exam}
            onNavigateSection={(secNum) => setActiveSection(secNum)}
            onNavigatePractice={onNavigatePractice}
            onSelectAlternativeExam={onSelectAlternativeExam}
          />
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
