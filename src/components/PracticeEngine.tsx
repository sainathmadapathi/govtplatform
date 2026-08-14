import React, { useState, useEffect } from 'react';
import { Award, Clock, CheckCircle2, XCircle, HelpCircle, ShieldCheck, RefreshCw, ChevronRight, BarChart2 } from 'lucide-react';
import { Exam, PracticeQuestion } from '../types/exam';

interface PracticeEngineProps {
  exam: Exam;
  onOpenProvenanceModal: (provenance: any) => void;
}

export const PracticeEngine: React.FC<PracticeEngineProps> = ({ exam, onOpenProvenanceModal }) => {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [isSubmitted, setIsSubmitted] = useState<boolean>(false);
  const [score, setScore] = useState<{ correct: number; incorrect: number }>({ correct: 0, incorrect: 0 });
  const [timerSeconds, setTimerSeconds] = useState<number>(120);

  const questions: PracticeQuestion[] = exam.practiceQuestions;
  const currentQ = questions[currentQuestionIndex] || questions[0];

  useEffect(() => {
    const interval = setInterval(() => {
      setTimerSeconds(prev => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectOption = (idx: number) => {
    if (!isSubmitted) setSelectedOption(idx);
  };

  const handleSubmitAnswer = () => {
    if (selectedOption === null) return;
    setIsSubmitted(true);
    if (selectedOption === currentQ.correctOptionIndex) {
      setScore(prev => ({ ...prev, correct: prev.correct + 1 }));
    } else {
      setScore(prev => ({ ...prev, incorrect: prev.incorrect + 1 }));
    }
  };

  const handleNextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
      setSelectedOption(null);
      setIsSubmitted(false);
    }
  };

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Quiz Top Control Bar */}
      <div className="glass-card" style={{ padding: '20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '38px', height: '38px', borderRadius: '10px', background: 'var(--emerald)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
            <Award size={22} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 800 }}>
              Timed PYQ & Practice Test Engine
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Subject: {currentQ.subject} | Topic: {currentQ.topicName}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '1.1rem', fontWeight: 800, color: '#38bdf8', fontFamily: 'var(--font-mono)', padding: '6px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
            <Clock size={18} /> {formatTimer(timerSeconds)}
          </div>

          <div style={{ display: 'flex', gap: '8px', fontSize: '0.85rem' }}>
            <span className="badge badge-verified">Correct: {score.correct}</span>
            <span className="badge badge-superseded">Wrong: {score.incorrect}</span>
          </div>
        </div>
      </div>

      {/* Main Question Card */}
      <div className="glass-card" style={{ padding: '32px' }}>
        
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
            QUESTION {currentQuestionIndex + 1} OF {questions.length}
          </span>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span className="badge badge-verified">
              {currentQ.questionType === 'OFFICIAL_PYQ' ? `OFFICIAL PYQ (${currentQ.year})` : currentQ.questionType}
            </span>
            {currentQ.provenance && (
              <button className="btn btn-outline" onClick={() => onOpenProvenanceModal(currentQ.provenance)} style={{ fontSize: '0.75rem', padding: '2px 8px' }}>
                <ShieldCheck size={12} /> Source
              </button>
            )}
          </div>
        </div>

        {/* Question Text */}
        <h3 style={{ fontSize: '1.25rem', fontWeight: 700, lineHeight: 1.5, marginBottom: '24px', color: 'white' }}>
          {currentQ.questionText}
        </h3>

        {/* Options List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '28px' }}>
          {currentQ.options.map((opt, idx) => {
            const isSelected = selectedOption === idx;
            const isCorrect = idx === currentQ.correctOptionIndex;
            
            let bg = 'rgba(255,255,255,0.03)';
            let borderColor = 'var(--border-color)';
            
            if (isSelected) {
              bg = 'rgba(99, 102, 241, 0.15)';
              borderColor = 'var(--primary)';
            }
            if (isSubmitted) {
              if (isCorrect) {
                bg = 'rgba(16, 185, 129, 0.15)';
                borderColor = 'var(--emerald)';
              } else if (isSelected && !isCorrect) {
                bg = 'rgba(244, 63, 94, 0.15)';
                borderColor = 'var(--rose)';
              }
            }

            return (
              <div
                key={opt.id}
                onClick={() => handleSelectOption(idx)}
                style={{
                  padding: '16px 20px',
                  borderRadius: 'var(--radius-md)',
                  background: bg,
                  border: `1.5px solid ${borderColor}`,
                  cursor: isSubmitted ? 'default' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '1rem', fontWeight: 500 }}>
                  <span style={{ width: '28px', height: '28px', borderRadius: '50%', background: 'rgba(255,255,255,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.85rem', fontWeight: 700 }}>
                    {String.fromCharCode(65 + idx)}
                  </span>
                  {opt.text}
                </div>

                {isSubmitted && isCorrect && <CheckCircle2 size={22} color="var(--emerald)" />}
                {isSubmitted && isSelected && !isCorrect && <XCircle size={22} color="var(--rose)" />}
              </div>
            );
          })}
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          {!isSubmitted ? (
            <button 
              className="btn btn-primary" 
              onClick={handleSubmitAnswer}
              disabled={selectedOption === null}
              style={{ opacity: selectedOption === null ? 0.5 : 1, padding: '12px 28px' }}
            >
              Submit Answer
            </button>
          ) : (
            <button 
              className="btn btn-emerald" 
              onClick={handleNextQuestion}
              disabled={currentQuestionIndex >= questions.length - 1}
              style={{ opacity: currentQuestionIndex >= questions.length - 1 ? 0.5 : 1, padding: '12px 28px' }}
            >
              Next Question <ChevronRight size={18} />
            </button>
          )}

          {isSubmitted && (
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Question <strong>{currentQuestionIndex + 1}</strong> of <strong>{questions.length}</strong> completed
            </div>
          )}
        </div>

        {/* Solution Explanation Box */}
        {isSubmitted && (
          <div style={{ marginTop: '24px', padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--primary)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <HelpCircle size={16} /> Detailed Solution Explanation
            </h4>
            <p style={{ fontSize: '0.9rem', color: '#e2e8f0', lineHeight: 1.6 }}>
              {currentQ.explanation}
            </p>
          </div>
        )}

      </div>
    </div>
  );
};
