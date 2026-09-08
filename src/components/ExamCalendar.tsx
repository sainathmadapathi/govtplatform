import React, { useState } from 'react';
import { 
  Calendar as CalendarIcon, ShieldCheck, Clock, Filter, 
  ChevronRight, Star, Check, Bell, BellOff, ArrowRight, 
  AlertTriangle, FileText, CheckCircle2, Award, Sparkles, Settings
} from 'lucide-react';
import { ALL_EXAMS } from '../data/examsData';
import { Exam } from '../types/exam';

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
