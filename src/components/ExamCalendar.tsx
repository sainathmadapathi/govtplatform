import React, { useState } from 'react';
import { Calendar as CalendarIcon, ShieldCheck, Clock, Filter, ChevronRight } from 'lucide-react';
import { ALL_EXAMS } from '../data/examsData';
import { Exam } from '../types/exam';

interface ExamCalendarProps {
  onSelectExam: (exam: Exam) => void;
}

export const ExamCalendar: React.FC<ExamCalendarProps> = ({ onSelectExam }) => {
  const [selectedMonth, setSelectedMonth] = useState<string>('AUG');

  const months = ['AUG', 'SEP', 'OCT', 'NOV', 'DEC'];

  const calendarEvents = [
    { id: 1, month: 'AUG', date: '10 Aug 2026', title: 'SSC CGL 2026 Official Notification Released', authority: 'SSC', type: 'NOTIFICATION', examCode: 'SSC_CGL_2026' },
    { id: 2, month: 'AUG', date: '15 Aug 2026', title: 'SSC CGL 2026 Online Application Window Opens', authority: 'SSC', type: 'APPLICATION_OPEN', examCode: 'SSC_CGL_2026' },
    { id: 3, month: 'AUG', date: '22 Aug 2026', title: 'SSC CGL Corrigendum #02: Application Deadline Extended', authority: 'SSC', type: 'CORRIGENDUM', examCode: 'SSC_CGL_2026' },
    { id: 4, month: 'SEP', date: '27 Sep 2026', title: 'SSC CGL 2026 Final Application Closing Date (23:59 IST)', authority: 'SSC', type: 'APPLICATION_CLOSE', examCode: 'SSC_CGL_2026' },
    { id: 5, month: 'OCT', date: '15 Oct 2026', title: 'SSC CGL Tier 1 Admit Card & City Intimation Release', authority: 'SSC', type: 'ADMIT_CARD', examCode: 'SSC_CGL_2026' },
    { id: 6, month: 'OCT', date: '28 Oct 2026', title: 'SSC CGL 2026 Tier 1 Computer Based Exam Begins', authority: 'SSC', type: 'EXAM', examCode: 'SSC_CGL_2026' },
    { id: 7, month: 'NOV', date: '12 Nov 2026', title: 'SSC CGL Tier 1 Tentative Answer Key & Objection Window', authority: 'SSC', type: 'ANSWER_KEY', examCode: 'SSC_CGL_2026' },
    { id: 8, month: 'DEC', date: '05 Dec 2026', title: 'SSC CGL Tier 1 Official Result Declaration', authority: 'SSC', type: 'RESULT', examCode: 'SSC_CGL_2026' }
  ];

  const filteredEvents = calendarEvents.filter(ev => ev.month === selectedMonth);

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* Header */}
      <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.1) 0%, rgba(17, 24, 39, 0.9) 100%)', borderColor: 'rgba(6, 182, 212, 0.3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--cyan)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
            <CalendarIcon size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800 }}>
              Government Exam Calendar & Recruitment Timeline (2026)
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              Track verified notification dates, application deadlines, admit card releases, and exam windows.
            </p>
          </div>
        </div>
      </div>

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
            {m} 2026
          </button>
        ))}
      </div>

      {/* Timeline List */}
      <div className="glass-card" style={{ padding: '28px' }}>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '20px' }}>
          Scheduled Events for {selectedMonth} 2026 ({filteredEvents.length} Events)
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {filteredEvents.map(ev => (
            <div 
              key={ev.id} 
              style={{ 
                padding: '20px', 
                borderRadius: 'var(--radius-md)', 
                background: 'rgba(255,255,255,0.03)', 
                border: '1px solid var(--border-color)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '16px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(99, 102, 241, 0.15)', border: '1px solid rgba(99, 102, 241, 0.3)', textAlign: 'center', minWidth: '100px' }}>
                  <div style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--primary)' }}>{ev.date}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>VERIFIED</div>
                </div>

                <div>
                  <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white' }}>{ev.title}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                    Authority: {ev.authority} | Event Type: {ev.type}
                  </div>
                </div>
              </div>

              <button 
                className="btn btn-outline"
                onClick={() => {
                  const matched = ALL_EXAMS.find(e => e.code === ev.examCode) || ALL_EXAMS[0];
                  onSelectExam(matched);
                }}
                style={{ fontSize: '0.8rem', padding: '6px 14px' }}
              >
                View Exam Guide <ChevronRight size={14} />
              </button>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
};
