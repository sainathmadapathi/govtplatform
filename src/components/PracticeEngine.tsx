import React, { useState, useEffect } from 'react';
import { 
  Award, Clock, CheckCircle2, XCircle, HelpCircle, ShieldCheck, RefreshCw, 
  ChevronRight, ChevronLeft, Bookmark, BarChart2, CheckSquare, RotateCcw, Flame,
  FileText, Target, Zap, BookOpen, AlertTriangle, TrendingUp, Calendar, Compass, 
  Database, Play, Pause, List, Sparkles, Sliders, Check, ArrowRight
} from 'lucide-react';
import { Exam, PracticeQuestion, DataProvenance } from '../types/exam';
import { storageService, MockAttemptRecord } from '../services/storageService';
import { ALL_POST_STUDY_PATHS } from '../data/postStudyPathsData';
import { 
  OFFICIAL_10_MOCK_PAPERS, 
  SUBJECT_MOCK_TESTS, 
  TOPIC_DRILL_TESTS, 
  MockPaper, 
  CustomTestConfig, 
  generateCustomMockTest 
} from '../data/mockPapersData';

interface PracticeEngineProps {
  exam: Exam;
  onOpenProvenanceModal: (provenance: DataProvenance) => void;
}

export const PracticeEngine: React.FC<PracticeEngineProps> = ({ exam, onOpenProvenanceModal }) => {
  // Navigation & Modes
  const [activePracticeTab, setActivePracticeTab] = useState<'PAPERS_LIST' | 'SUBJECT_TESTS' | 'TOPIC_DRILLS' | 'AI_GENERATOR' | 'ACTIVE_TEST' | 'PAST_ANALYTICS'>('PAPERS_LIST');
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
  
  // AI Test Generator State
  const [genSubjects, setGenSubjects] = useState<string[]>(['Quantitative Aptitude', 'Reasoning & General Intelligence', 'English Comprehension', 'General Awareness']);
  const [genNumQuestions, setGenNumQuestions] = useState<number>(25);
  const [genDifficulty, setGenDifficulty] = useState<'EASY' | 'MEDIUM' | 'HARD' | 'ADAPTIVE'>('MEDIUM');
  const [genFocusGoal, setGenFocusGoal] = useState<'GENERAL' | 'WEAK_AREAS' | 'SPEED_BOOSTER' | 'PRE_EXAM'>('WEAK_AREAS');
  
  // Past Attempts History & Target Post
  const [pastAttempts, setPastAttempts] = useState<MockAttemptRecord[]>(() => storageService.getMockAttempts());
  const targetPostId = storageService.getTargetPost();
  const targetPost = ALL_POST_STUDY_PATHS[targetPostId] || ALL_POST_STUDY_PATHS['post-aso-css'];

  const questionsList = selectedPaper.questions;

  // Filtered by current section tab if viewing specific section
  const sectionQuestions = activeSection === 'ALL'
    ? questionsList
    : questionsList.filter(q => q.subject === activeSection);

  const currentQ = questionsList[currentIdx] || questionsList[0];

  // Timer Effect (Only ticks if test is started, not submitted, and not paused)
  useEffect(() => {
    let interval: any = null;
    if (isTestStarted && !isSubmittedTest && !isTimerPaused && timerSeconds > 0) {
      interval = setInterval(() => {
        setTimerSeconds(prev => (prev > 0 ? prev - 1 : 0));
      }, 1000);
    } else if (timerSeconds === 0 && isTestStarted && !isSubmittedTest) {
      handleSubmitTest(); // Auto-submit on time expiry
    }
    return () => clearInterval(interval);
  }, [isTestStarted, isSubmittedTest, isTimerPaused, timerSeconds]);

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
    setTimerSeconds(paper.durationMinutes * 60);
    setIsTimerPaused(false);
    setCurrentIdx(0);
    setActiveSection('ALL');
    setIsTestStarted(true);
    setActivePracticeTab('ACTIVE_TEST');
  };

  const handleResetTest = () => {
    setUserAnswers({});
    setMarkedForReview({});
    setIsSubmittedTest(false);
    setIsTestStarted(false);
    setTimerSeconds(3600);
    setCurrentIdx(0);
    setActivePracticeTab('PAPERS_LIST');
  };

  const handleToggleGenSubject = (subj: string) => {
    if (genSubjects.includes(subj)) {
      if (genSubjects.length > 1) {
        setGenSubjects(genSubjects.filter(s => s !== subj));
      }
    } else {
      setGenSubjects([...genSubjects, subj]);
    }
  };

  const handleGenerateAndStartTest = () => {
    const customPaper = generateCustomMockTest({
      selectedSubjects: genSubjects,
      selectedTopics: [],
      numQuestions: genNumQuestions,
      difficulty: genDifficulty,
      focusGoal: genFocusGoal
    });
    handleStartTest(customPaper);
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

  // Classify Weak, Medium, Strong Topics
  const weakAreas: { topic: string; subject: string; accuracy: number; total: number; missed: number }[] = [];
  const mediumAreas: { topic: string; subject: string; accuracy: number; total: number }[] = [];
  const strongAreas: { topic: string; subject: string; accuracy: number; total: number }[] = [];

  Object.entries(subjectPerformance).forEach(([subj, data]) => {
    Object.entries(data.topics).forEach(([top, tData]) => {
      const acc = tData.total > 0 ? (tData.correct / tData.total) * 100 : 0;
      if (acc < 50) {
        weakAreas.push({ topic: top, subject: subj, accuracy: Math.round(acc), total: tData.total, missed: tData.incorrect });
      } else if (acc >= 50 && acc < 75) {
        mediumAreas.push({ topic: top, subject: subj, accuracy: Math.round(acc), total: tData.total });
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
      attempted_at: new Date().toLocaleString()
    };

    // Save to dual persistence (localStorage + SQLite govos.db)
    storageService.saveMockAttempt(newAttempt);
    setPastAttempts(storageService.getMockAttempts());
  };

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* 1. TOP PRACTICE NAVIGATION BAR */}
      <div className="glass-card" style={{ padding: '20px', background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '14px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className="badge badge-demo" style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.4)' }}>
                ⚡ COMPLETE CBT MOCK & AI GENERATOR ECOSYSTEM
              </span>
              <span style={{ fontSize: '0.8rem', color: '#93c5fd', fontWeight: 700 }}>
                • Target: {targetPost.postName}
              </span>
            </div>
            <h3 style={{ fontSize: '1.45rem', fontWeight: 800, color: 'white', margin: 0 }}>
              Mock Tests, Subject Sectionals & AI Test Generator
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', margin: '4px 0 0 0' }}>
              Take full 100-question shift papers, 25-Q sectionals, 15-Q topic drills, or design your own customized test with the AI Test Generator Assistant.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            {isTestStarted && (
              <button onClick={handleResetTest} className="btn btn-secondary" style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <RotateCcw size={14} /> Exit Test
              </button>
            )}
          </div>
        </div>

        {/* 5 Main View Navigation Tabs */}
        <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
          <button
            onClick={() => { setActivePracticeTab('PAPERS_LIST'); setIsTestStarted(false); }}
            className={`btn ${activePracticeTab === 'PAPERS_LIST' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.85rem', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap' }}
          >
            <List size={15} /> 📑 10 Full Shift Papers (100 Qs)
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
            onClick={() => { setActivePracticeTab('AI_GENERATOR'); setIsTestStarted(false); }}
            className={`btn ${activePracticeTab === 'AI_GENERATOR' ? 'btn-emerald' : 'btn-secondary'}`}
            style={{ fontSize: '0.85rem', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap', border: '1px solid #34d399' }}
          >
            <Sparkles size={15} /> 🤖 AI Mock Generator Assistant
          </button>

          <button
            onClick={() => setActivePracticeTab('PAST_ANALYTICS')}
            className={`btn ${activePracticeTab === 'PAST_ANALYTICS' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.85rem', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap' }}
          >
            <BarChart2 size={15} /> 📊 Past Tests History ({pastAttempts.length})
          </button>
        </div>
      </div>

      {/* VIEW 1: 10 FULL SHIFT PAPERS (100 Qs) */}
      {activePracticeTab === 'PAPERS_LIST' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
            <h4 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'white', margin: 0 }}>
              10 Official Full-Length Shift Papers (100 Questions / 200 Marks)
            </h4>
            <span style={{ fontSize: '0.8rem', color: '#86efac' }}>
              60 Minutes Real Exam Clock • 4 Sections Balanced
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px' }}>
            {OFFICIAL_10_MOCK_PAPERS.map((paper, pIdx) => (
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
                  <div><strong style={{ color: '#93c5fd' }}>Questions</strong><div style={{ color: 'white', fontWeight: 700 }}>100 Qs</div></div>
                  <div><strong style={{ color: '#93c5fd' }}>Duration</strong><div style={{ color: 'white', fontWeight: 700 }}>60 Mins</div></div>
                  <div><strong style={{ color: '#93c5fd' }}>Max Marks</strong><div style={{ color: '#86efac', fontWeight: 700 }}>200 Marks</div></div>
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

      {/* VIEW 2: SUBJECT SECTIONALS (25 Qs) */}
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

      {/* VIEW 3: TOPIC DRILLS (15 Qs) */}
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

      {/* VIEW 4: AI MOCK TEST GENERATOR ASSISTANT */}
      {activePracticeTab === 'AI_GENERATOR' && (
        <div className="glass-card" style={{ padding: '28px', display: 'flex', flexDirection: 'column', gap: '22px', border: '1px solid rgba(16, 185, 129, 0.4)', background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(6, 78, 59, 0.2) 100%)' }}>
          <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className="badge badge-verified" style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399' }}>
                <Sparkles size={14} /> AI MOCK TEST GENERATOR ASSISTANT
              </span>
            </div>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'white', margin: 0 }}>
              Design Your Custom Context-Aware Mock Test
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', margin: '4px 0 0 0' }}>
              Configure subjects, question volume, and difficulty. The engine automatically calculates the realistic exam timer calibrated to your selected difficulty level.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
            
            {/* 1. Subjects Selection */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <label style={{ fontSize: '0.88rem', fontWeight: 700, color: '#93c5fd' }}>
                1. Select Target Subjects (Multi-Select):
              </label>
              {[
                'Quantitative Aptitude',
                'Reasoning & General Intelligence',
                'English Comprehension',
                'General Awareness',
                'Computer Proficiency'
              ].map(subj => {
                const isSelected = genSubjects.includes(subj);
                return (
                  <div
                    key={subj}
                    onClick={() => handleToggleGenSubject(subj)}
                    style={{
                      padding: '10px 14px',
                      borderRadius: 'var(--radius-sm)',
                      background: isSelected ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                      border: isSelected ? '1px solid #10b981' : '1px solid var(--border-color)',
                      color: isSelected ? '#86efac' : 'var(--text-secondary)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      fontSize: '0.85rem',
                      fontWeight: isSelected ? 700 : 500
                    }}
                  >
                    <div style={{ width: '18px', height: '18px', borderRadius: '4px', border: isSelected ? '2px solid #10b981' : '2px solid gray', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#10b981', fontSize: '0.75rem', fontWeight: 900 }}>
                      {isSelected ? '✓' : ''}
                    </div>
                    {subj}
                  </div>
                );
              })}
            </div>

            {/* 2. Number of Questions & Focus Goal */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ fontSize: '0.88rem', fontWeight: 700, color: '#93c5fd', display: 'block', marginBottom: '8px' }}>
                  2. Number of Questions:
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                  {[10, 15, 25, 50].map(cnt => (
                    <button
                      key={cnt}
                      onClick={() => setGenNumQuestions(cnt)}
                      className={`btn ${genNumQuestions === cnt ? 'btn-primary' : 'btn-secondary'}`}
                      style={{ fontSize: '0.85rem', padding: '8px', fontWeight: 700 }}
                    >
                      {cnt} Qs
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label style={{ fontSize: '0.88rem', fontWeight: 700, color: '#93c5fd', display: 'block', marginBottom: '8px' }}>
                  3. Difficulty Level:
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                  {[
                    { id: 'EASY', label: '🟢 Easy (Speed Builder)' },
                    { id: 'MEDIUM', label: '🟡 Medium (Standard CGL)' },
                    { id: 'HARD', label: '🔴 Hard (Tier-2 Advanced)' },
                    { id: 'ADAPTIVE', label: '⚡ Adaptive (Mixed)' }
                  ].map(lvl => (
                    <button
                      key={lvl.id}
                      onClick={() => setGenDifficulty(lvl.id as any)}
                      className={`btn ${genDifficulty === lvl.id ? 'btn-emerald' : 'btn-secondary'}`}
                      style={{ fontSize: '0.78rem', padding: '8px 10px', textAlign: 'left', fontWeight: 600 }}
                    >
                      {lvl.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* 3. Intelligent Timer Preview Card */}
            <div style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#93c5fd', fontWeight: 700, fontSize: '0.9rem' }}>
                <Clock size={18} /> Intelligent Timer Calibration
              </div>

              <div style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Based on your selection of <strong>{genNumQuestions} Questions</strong> at <strong>{genDifficulty}</strong> difficulty across {genSubjects.length} subjects:
              </div>

              <div style={{ padding: '12px', borderRadius: 'var(--radius-sm)', background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.75rem', color: '#86efac', textTransform: 'uppercase', fontWeight: 700 }}>Allocated Clock Time</div>
                <div style={{ fontSize: '1.6rem', fontWeight: 900, color: '#34d399', margin: '2px 0' }}>
                  {Math.max(5, Math.ceil((genNumQuestions * (genDifficulty === 'HARD' ? 55 : genDifficulty === 'EASY' ? 28 : 40)) / 60))} Minutes
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  Calibrated for realistic TCS pace & deep accuracy
                </div>
              </div>

              <button
                onClick={handleGenerateAndStartTest}
                className="btn btn-emerald"
                style={{ width: '100%', padding: '12px', fontSize: '0.95rem', fontWeight: 800, marginTop: '4px', boxShadow: '0 4px 16px rgba(16, 185, 129, 0.4)' }}
              >
                <Sparkles size={16} /> Generate & Start Custom Mock
              </button>
            </div>

          </div>
        </div>
      )}

      {/* VIEW 5: ACTIVE TEST & POST-TEST DIAGNOSTIC DASHBOARD */}
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

          {/* TEST QUESTION SCREEN OR POST-TEST DIAGNOSTIC REPORT */}
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
                  <CheckSquare size={16} /> Submit & Analyze Performance
                </button>
              </div>

            </div>
          ) : (

            /* 🎯 POST-TEST INTELLIGENT DIAGNOSTIC DASHBOARD & REMEDIAL RECOMMENDATIONS */
            <div className="glass-card animate-fade-in" style={{ padding: '28px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
              
              {/* Score & Benchmark Banner */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '20px' }}>
                <div>
                  <span className="badge badge-verified" style={{ fontSize: '0.78rem' }}>
                    🎯 TEST COMPLETED & SYNCED TO SQLITE
                  </span>
                  <h3 style={{ fontSize: '1.7rem', fontWeight: 800, color: 'white', margin: '6px 0 2px 0' }}>
                    Diagnostic Analysis & Remedial Recommendations
                  </h3>
                  <div style={{ fontSize: '0.85rem', color: '#93c5fd' }}>
                    Target Post: <strong>{targetPost.postName}</strong> ({targetPost.department})
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  <div style={{ padding: '12px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.72rem', color: '#86efac', textTransform: 'uppercase', fontWeight: 700 }}>Score Earned</div>
                    <div style={{ fontSize: '1.5rem', fontWeight: 900, color: '#34d399' }}>{marksEarned} / {totalPossibleMarks}</div>
                  </div>

                  <div style={{ padding: '12px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.72rem', color: '#93c5fd', textTransform: 'uppercase', fontWeight: 700 }}>Accuracy</div>
                    <div style={{ fontSize: '1.5rem', fontWeight: 900, color: '#60a5fa' }}>{accuracyPercentage}%</div>
                  </div>

                  <div style={{ padding: '12px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.72rem', color: '#fde047', textTransform: 'uppercase', fontWeight: 700 }}>Correct / Total</div>
                    <div style={{ fontSize: '1.5rem', fontWeight: 900, color: '#fbbf24' }}>{correctCount} / {questionsList.length}</div>
                  </div>
                </div>
              </div>

              {/* 🎯 NEW: ADAPTIVE REMEDIAL TESTS RECOMMENDED TO FIX WEAKNESSES */}
              {weakAreas.length > 0 && (
                <div style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(239, 68, 68, 0.06)', border: '1px solid rgba(239, 68, 68, 0.35)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f87171', fontWeight: 800, fontSize: '1.05rem' }}>
                      <Zap size={18} /> 🚀 Recommended Remedial Tests to Fix Your Weaknesses Immediately
                    </div>
                    <span className="badge" style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5' }}>
                      Auto-Generated from Test Mistakes
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
                    {weakAreas.map((w, wIdx) => {
                      const matchedDrill = TOPIC_DRILL_TESTS.find(t => t.subject === w.subject) || TOPIC_DRILL_TESTS[0];
                      return (
                        <div key={wIdx} style={{ padding: '14px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(239,68,68,0.25)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '10px' }}>
                          <div>
                            <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'white' }}>Fix Topic: {w.topic}</div>
                            <div style={{ fontSize: '0.78rem', color: '#fecaca', marginTop: '2px' }}>
                              Current Accuracy: {w.accuracy}% • Missed {w.missed} questions in this test.
                            </div>
                          </div>

                          <button
                            onClick={() => handleStartTest(matchedDrill)}
                            className="btn btn-primary"
                            style={{ fontSize: '0.78rem', padding: '6px 12px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', width: '100%' }}
                          >
                            <Play size={13} /> Start 15-Q Remedial Drill <ArrowRight size={13} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 3-COLUMN WEAK, MEDIUM, STRONG MATRIX */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
                
                {/* 🔴 WEAK AREAS (< 50%) */}
                <div style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(239, 68, 68, 0.04)', border: '1px solid rgba(239, 68, 68, 0.3)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f87171', fontWeight: 800, fontSize: '1rem' }}>
                      <XCircle size={18} /> 🔴 Weak Areas (&lt; 50% Accuracy)
                    </div>
                    <span className="badge" style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5' }}>{weakAreas.length} Topics</span>
                  </div>

                  {weakAreas.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {weakAreas.map((w, wIdx) => (
                        <div key={wIdx} style={{ padding: '12px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(239,68,68,0.2)' }}>
                          <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'white' }}>{w.topic}</div>
                          <div style={{ fontSize: '0.78rem', color: '#fecaca', marginTop: '2px' }}>
                            Subject: {w.subject} • Missed: {w.missed} Qs (Accuracy: {w.accuracy}%)
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ fontSize: '0.85rem', color: '#86efac' }}>
                      🎉 Zero critical weaknesses detected in this session!
                    </div>
                  )}
                </div>

                {/* 🟡 MEDIUM AREAS (50% - 75%) */}
                <div style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(234, 179, 8, 0.04)', border: '1px solid rgba(234, 179, 8, 0.3)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#fbbf24', fontWeight: 800, fontSize: '1rem' }}>
                      <AlertTriangle size={18} /> 🟡 Medium Areas (50% - 75%)
                    </div>
                    <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.2)', color: '#fde047' }}>{mediumAreas.length} Topics</span>
                  </div>

                  {mediumAreas.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {mediumAreas.map((m, mIdx) => (
                        <div key={mIdx} style={{ padding: '12px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(234,179,8,0.2)' }}>
                          <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'white' }}>{m.topic}</div>
                          <div style={{ fontSize: '0.78rem', color: '#fef08a', marginTop: '2px' }}>
                            Subject: {m.subject} • Accuracy: {m.accuracy}%
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      No topics in the medium band.
                    </div>
                  )}
                </div>

                {/* 🟢 STRONG AREAS (> 75%) */}
                <div style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(16, 185, 129, 0.04)', border: '1px solid rgba(16, 185, 129, 0.3)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#34d399', fontWeight: 800, fontSize: '1rem' }}>
                      <CheckCircle2 size={18} /> 🟢 Strong Areas (&gt; 75% Accuracy)
                    </div>
                    <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#86efac' }}>{strongAreas.length} Topics</span>
                  </div>

                  {strongAreas.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {strongAreas.map((s, sIdx) => (
                        <div key={sIdx} style={{ padding: '12px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(16,185,129,0.2)' }}>
                          <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'white' }}>{s.topic}</div>
                          <div style={{ fontSize: '0.78rem', color: '#86efac', marginTop: '2px' }}>
                            Subject: {s.subject} • Accuracy: {s.accuracy}%
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      Complete more questions to establish strong areas.
                    </div>
                  )}
                </div>

              </div>

              {/* 🎯 SELECTION PLAN-BASED DAILY PREPARATION HOURS ALLOCATION */}
              <div className="glass-card" style={{ padding: '22px', border: '1px solid rgba(59, 130, 246, 0.3)', background: 'rgba(59, 130, 246, 0.04)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', marginBottom: '14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Compass size={20} color="#60a5fa" />
                    <div>
                      <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white', margin: 0 }}>
                        Target Post Daily Study Hours Blueprint ({studyHoursPlan.totalDailyHours} Hours/Day)
                      </h4>
                      <span style={{ fontSize: '0.78rem', color: '#93c5fd' }}>
                        Dynamically calculated to bridge your weak areas for {targetPost.postName}.
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

              {/* Question-by-Question Detailed Solutions Review */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white', margin: 0 }}>
                    Detailed Step-by-Step Official Solutions ({questionsList.length} Questions)
                  </h4>
                  <button onClick={handleResetTest} className="btn btn-primary" style={{ fontSize: '0.82rem' }}>
                    Attempt Another Test
                  </button>
                </div>

                {questionsList.slice(0, 25).map((q, idx) => {
                  const userAns = userAnswers[idx];
                  const isCorrect = userAns === q.correctOptionIndex;
                  return (
                    <div key={q.id} style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: isCorrect ? 'rgba(16, 185, 129, 0.03)' : 'rgba(239, 68, 68, 0.03)', border: isCorrect ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(239, 68, 68, 0.25)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 800, color: 'white', fontSize: '0.95rem' }}>Q{idx + 1}.</span>
                          <span className="badge" style={{ background: isCorrect ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)', color: isCorrect ? '#86efac' : '#fca5a5' }}>
                            {userAns === undefined ? 'Unattempted (0 Marks)' : isCorrect ? 'Correct (+2.0 Marks)' : 'Incorrect (-0.50 Marks)'}
                          </span>
                        </div>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{q.shiftInfo}</span>
                      </div>

                      <div style={{ fontSize: '0.95rem', color: 'white' }}>{q.questionText}</div>

                      <div style={{ padding: '12px 14px', borderRadius: 'var(--radius-sm)', background: 'rgba(0,0,0,0.3)', fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                        <strong style={{ color: '#93c5fd' }}>Official Explanation:</strong>
                        <div style={{ marginTop: '4px', whiteSpace: 'pre-line' }}>{q.explanation}</div>
                      </div>
                    </div>
                  );
                })}
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
                  </tr>
                </thead>
                <tbody>
                  {pastAttempts.map((att, aIdx) => {
                    const acc = (att.correct_count + att.incorrect_count) > 0 ? Math.round((att.correct_count / (att.correct_count + att.incorrect_count)) * 100) : 0;
                    return (
                      <tr key={aIdx} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', background: aIdx % 2 === 0 ? 'rgba(255, 255, 255, 0.01)' : 'transparent' }}>
                        <td style={{ padding: '12px 14px', fontWeight: 700, color: 'white' }}>{att.subject}</td>
                        <td style={{ padding: '12px 14px', color: att.score >= 0 ? '#86efac' : '#f87171', fontWeight: 800 }}>
                          {att.score} / {att.total_marks}
                        </td>
                        <td style={{ padding: '12px 14px' }}>
                          <span className="badge" style={{ background: acc >= 75 ? 'rgba(16, 185, 129, 0.2)' : acc >= 50 ? 'rgba(234, 179, 8, 0.2)' : 'rgba(239, 68, 68, 0.2)', color: acc >= 75 ? '#86efac' : acc >= 50 ? '#fde047' : '#fca5a5' }}>
                            {acc}%
                          </span>
                        </td>
                        <td style={{ padding: '12px 14px', color: 'var(--text-secondary)' }}>
                          <span style={{ color: '#86efac' }}>{att.correct_count} Correct</span>, <span style={{ color: '#f87171' }}>{att.incorrect_count} Wrong</span>
                        </td>
                        <td style={{ padding: '12px 14px', color: 'var(--text-muted)' }}>
                          {Math.floor(att.time_taken_seconds / 60)}m {att.time_taken_seconds % 60}s
                        </td>
                        <td style={{ padding: '12px 14px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                          {att.attempted_at || 'Recent'}
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
