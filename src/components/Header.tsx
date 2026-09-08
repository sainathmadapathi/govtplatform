import React from 'react';
import { ShieldCheck, Search, Compass, CheckCircle2, Calendar, Scale, Award, Terminal, BookOpen, Bell, Sparkles } from 'lucide-react';

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
