import React, { useState } from 'react';
import { Calendar, Clock, Flame, CheckCircle2, ChevronRight, Sparkles, BookOpen } from 'lucide-react';
import { Exam } from '../types/exam';

interface PreparationPlannerProps {
  exam: Exam;
}

export const PreparationPlanner: React.FC<PreparationPlannerProps> = ({ exam }) => {
  const [duration, setDuration] = useState<'30' | '90' | '180'>('90');
  const [dailyHours, setDailyHours] = useState<number>(4);
  const [level, setLevel] = useState<'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED'>('BEGINNER');

  const plans = {
    '30': [
      { month: 'Phase 1 (Days 1-10)', focus: 'High-Weightage Core Topics', tasks: ['Complete Percentage & Ratio', 'Coding-Decoding practice', 'Grammar Rules & Error Spotting'] },
      { month: 'Phase 2 (Days 11-20)', focus: 'Intense Topic Practice', tasks: ['Algebra & Geometry Basics', 'Syllogism & Venn Diagrams', 'Polity & Constitution Articles'] },
      { month: 'Phase 3 (Days 21-30)', focus: 'Full-Length Mocks & Revision', tasks: ['Take 1 Mock Test daily', 'Analyze weak areas', 'Revise Current Affairs'] }
    ],
    '90': [
      { month: 'Month 1 (Days 1-30)', focus: 'Foundation & Concepts', tasks: ['Complete Quant Arithmetic', 'Reasoning Logical Concepts', 'Vocabulary & Reading Comprehension', 'Polity & History NCERT'] },
      { month: 'Month 2 (Days 31-60)', focus: 'Advanced Topics & Practice', tasks: ['Algebra, Geometry & Mensuration', 'Non-Verbal Reasoning', 'Cloze Test & Sentence Improvement', 'Geography & Science'] },
      { month: 'Month 3 (Days 61-90)', focus: 'Mock Test Series & Speed', tasks: ['Take 2 Full Mocks per week', 'Sectional Speed Tests', 'Final Revision of PYQs'] }
    ],
    '180': [
      { month: 'Month 1-2', focus: 'Comprehensive Foundation', tasks: ['Thorough coverage of all 4 subjects', 'NCERT History, Polity, Geography', 'Daily 30 Quant practice questions'] },
      { month: 'Month 3-4', focus: 'Topic Mastery & PYQs', tasks: ['Solve 5 years of SSC CGL PYQs', 'Advanced Tier-2 Mathematics', 'Computer Proficiency Modules'] },
      { month: 'Month 5-6', focus: 'Full Mock Simulator & Final Polish', tasks: ['30 Full-Length Mocks', 'Weak Area Remediation', 'Speed & Accuracy Optimization'] }
    ]
  };

  const currentPlan = plans[duration];

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* Header Banner */}
      <div className="glass-card" style={{ padding: '28px', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(17, 24, 39, 0.9) 100%)', borderColor: 'rgba(99, 102, 241, 0.3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '8px' }}>
          <div style={{ width: '42px', height: '42px', borderRadius: '12px', background: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
            <Calendar size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800 }}>
              Personalized Preparation Engine & Study Roadmap
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              Tailored preparation plan generated for {exam.title}
            </p>
          </div>
        </div>
      </div>

      {/* Control Card */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '16px' }}>Configure Your Preparation Schedule</h3>
        
        <div className="grid-3">
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              Target Duration
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className={`btn ${duration === '30' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setDuration('30')} style={{ flex: 1, fontSize: '0.8rem' }}>30 Days</button>
              <button className={`btn ${duration === '90' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setDuration('90')} style={{ flex: 1, fontSize: '0.8rem' }}>90 Days</button>
              <button className={`btn ${duration === '180' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setDuration('180')} style={{ flex: 1, fontSize: '0.8rem' }}>6 Months</button>
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              Daily Study Capacity
            </label>
            <select value={dailyHours} onChange={(e) => setDailyHours(Number(e.target.value))} style={{ width: '100%', padding: '10px', borderRadius: 'var(--radius-md)', background: 'var(--bg-input)', border: '1px solid var(--border-color)', color: 'white' }}>
              <option value={2}>2 Hours / Day (Part-time)</option>
              <option value={4}>4 Hours / Day (Regular)</option>
              <option value={6}>6 Hours / Day (Dedicated)</option>
              <option value={8}>8+ Hours / Day (Full-time)</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              Starting Preparation Level
            </label>
            <select value={level} onChange={(e) => setLevel(e.target.value as any)} style={{ width: '100%', padding: '10px', borderRadius: 'var(--radius-md)', background: 'var(--bg-input)', border: '1px solid var(--border-color)', color: 'white' }}>
              <option value="BEGINNER">Beginner (First Attempt)</option>
              <option value="INTERMEDIATE">Intermediate (Syllabus 50% Done)</option>
              <option value="ADVANCED">Advanced (Revision & Mocks)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Generated Roadmap Timeline */}
      <div className="glass-card" style={{ padding: '28px' }}>
        <h3 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles color="var(--emerald)" size={20} /> Customized Preparation Schedule ({duration} Days Plan)
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {currentPlan.map((phase, idx) => (
            <div key={idx} style={{ padding: '20px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--primary)' }}>
                  {phase.month}
                </span>
                <span className="badge badge-verified">
                  Focus: {phase.focus}
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {phase.tasks.map((task, tIdx) => (
                  <div key={tIdx} style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.9rem', color: '#e2e8f0' }}>
                    <CheckCircle2 size={16} color="var(--emerald)" />
                    {task}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
};
