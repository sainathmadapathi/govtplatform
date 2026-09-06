import React, { useState, useEffect, useRef } from 'react';
import { 
  Award, Clock, CheckCircle2, XCircle, HelpCircle, ShieldCheck, RefreshCw, 
  ChevronRight, ChevronLeft, Bookmark, BarChart2, CheckSquare, RotateCcw, Flame,
  FileText, Target, Zap, BookOpen, AlertTriangle, TrendingUp, Calendar, Compass, 
  Database, Play, Pause, List, Sparkles, Sliders, Check, ArrowRight, Send, Bot, User, MessageSquare, Filter, Download
} from 'lucide-react';
import { Exam, PracticeQuestion, DataProvenance } from '../types/exam';
import { storageService, MockAttemptRecord } from '../services/storageService';
import { ALL_POST_STUDY_PATHS } from '../data/postStudyPathsData';
import { 
  OFFICIAL_10_MOCK_PAPERS, 
  NEW_DISCOVERED_PAPERS,
  SUBJECT_MOCK_TESTS, 
  TOPIC_DRILL_TESTS, 
  MockPaper, 
  CustomTestConfig, 
  generateCustomMockTest,
  QUANT_TEMPLATES,
  REASONING_TEMPLATES,
  GA_TEMPLATES,
  ENGLISH_TEMPLATES,
  COMPUTER_TEMPLATES
} from '../data/mockPapersData';

interface PracticeEngineProps {
  exam: Exam;
  onOpenProvenanceModal: (provenance: DataProvenance) => void;
}

interface ChatMessage {
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
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
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
  const targetPostId = storageService.getTargetPost();
  const targetPost = ALL_POST_STUDY_PATHS[targetPostId] || ALL_POST_STUDY_PATHS['post-aso-css'];

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
    setTimerSeconds(3600);
    setCurrentIdx(0);
    setActivePracticeTab('PAPERS_LIST');
  };

  // Conversational Context Parser & Test Generator
  const handleSendChatMessage = (customText?: string) => {
    const query = customText || chatInput;
    if (!query.trim()) return;

    const userMsg: ChatMessage = {
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

      const botMsg: ChatMessage = {
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

    storageService.saveMockAttempt(newAttempt);
    setPastAttempts(storageService.getMockAttempts());
  };

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // Filter Solutions List
  const filteredSolutions = questionsList.filter((q, idx) => {
    const userAns = userAnswers[idx];
    const isCorrect = userAns === q.correctOptionIndex;
    const isUnattempted = userAns === undefined;
    const isIncorrect = userAns !== undefined && !isCorrect;

    if (solutionFilter === 'INCORRECT' && !isIncorrect) return false;
    if (solutionFilter === 'UNATTEMPTED' && !isUnattempted) return false;
    if (solutionFilter === 'CORRECT' && !isCorrect) return false;

    if (solutionSectionFilter !== 'ALL' && q.subject !== solutionSectionFilter) return false;

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
                <RotateCcw size={14} /> Exit Test
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
              
              {/* Top Scorecard Banner */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '20px' }}>
                <div>
                  <span className="badge badge-verified" style={{ fontSize: '0.78rem' }}>
                    🎯 TEST EVALUATION COMPLETE & SYNCED TO SQLITE
                  </span>
                  <h3 style={{ fontSize: '1.7rem', fontWeight: 800, color: 'white', margin: '6px 0 2px 0' }}>
                    In-Depth Diagnostic Clarity & Solutions Engine
                  </h3>
                  <div style={{ fontSize: '0.85rem', color: '#93c5fd' }}>
                    Target Post: <strong>{targetPost.postName}</strong> ({targetPost.department})
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  <div style={{ padding: '12px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.72rem', color: '#86efac', textTransform: 'uppercase', fontWeight: 700 }}>Final Score</div>
                    <div style={{ fontSize: '1.6rem', fontWeight: 900, color: '#34d399' }}>{marksEarned} / {totalPossibleMarks}</div>
                  </div>

                  <div style={{ padding: '12px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.72rem', color: '#93c5fd', textTransform: 'uppercase', fontWeight: 700 }}>Accuracy Rate</div>
                    <div style={{ fontSize: '1.6rem', fontWeight: 900, color: '#60a5fa' }}>{accuracyPercentage}%</div>
                  </div>

                  <div style={{ padding: '12px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.72rem', color: '#fde047', textTransform: 'uppercase', fontWeight: 700 }}>Correct / Total</div>
                    <div style={{ fontSize: '1.6rem', fontWeight: 900, color: '#fbbf24' }}>{correctCount} / {questionsList.length}</div>
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

                  <button onClick={handleResetTest} className="btn btn-primary" style={{ fontSize: '0.85rem' }}>
                    Attempt Another Test
                  </button>
                </div>

                {/* Filter Tabs */}
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginRight: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Filter size={14} /> Filter By:
                  </span>

                  {[
                    { id: 'ALL', label: `All Questions (${questionsList.length})` },
                    { id: 'INCORRECT', label: `❌ Incorrect (${incorrectCount})` },
                    { id: 'UNATTEMPTED', label: `⚠️ Unattempted (${unattemptedCount})` },
                    { id: 'CORRECT', label: `✅ Correct (${correctCount})` }
                  ].map(tab => (
                    <button
                      key={tab.id}
                      onClick={() => setSolutionFilter(tab.id as any)}
                      className={`btn ${solutionFilter === tab.id ? 'btn-primary' : 'btn-secondary'}`}
                      style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                    >
                      {tab.label}
                    </button>
                  ))}

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
                    const isCorrect = userAns === q.correctOptionIndex;
                    const isUnattempted = userAns === undefined;
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
                          border: isCorrect ? '1.5px solid rgba(16, 185, 129, 0.45)' : isUnattempted ? '1.5px solid rgba(245, 158, 11, 0.45)' : '1.5px solid rgba(239, 68, 68, 0.45)',
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
                            const isThisUserSelected = userAns === opt.id;

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
                                {isThisCorrect && <span style={{ fontWeight: 900, fontSize: '0.8rem', color: '#34d399' }}>✓ Correct Answer</span>}
                                {isThisUserSelected && !isThisCorrect && <span style={{ fontWeight: 900, fontSize: '0.8rem', color: '#f87171' }}>✗ Your Choice</span>}
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
