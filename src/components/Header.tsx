import React from 'react';
import { ShieldCheck, Search, Compass, CheckCircle2, Calendar, Scale, Award, Terminal, BookOpen } from 'lucide-react';

interface HeaderProps {
  activeTab: 'FINDER' | 'ELIGIBILITY' | 'EXAM_DETAIL' | 'PLANNER' | 'PRACTICE' | 'COMPARE' | 'CALENDAR' | 'AI_ASSISTANT' | 'ADMIN';
  setActiveTab: (tab: 'FINDER' | 'ELIGIBILITY' | 'EXAM_DETAIL' | 'PLANNER' | 'PRACTICE' | 'COMPARE' | 'CALENDAR' | 'AI_ASSISTANT' | 'ADMIN') => void;
  selectedExamTitle?: string;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab, selectedExamTitle }) => {
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
            <BookOpen size={16} /> 14-Section Guide {selectedExamTitle && `(${selectedExamTitle.split(' ')[0]})`}
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
            onClick={() => setActiveTab('CALENDAR')}
            style={{ fontSize: '0.85rem', padding: '8px 14px' }}
          >
            <Calendar size={16} /> Calendar
          </button>

          <button 
            className={`btn ${activeTab === 'ADMIN' ? 'btn-emerald' : 'btn-secondary'}`}
            onClick={() => setActiveTab('ADMIN')}
            style={{ fontSize: '0.85rem', padding: '8px 14px' }}
          >
            <Terminal size={16} /> Trust Panel
          </button>
        </nav>
      </div>
    </header>
  );
};
