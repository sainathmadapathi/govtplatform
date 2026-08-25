import React, { useState } from 'react';
import { 
  Calendar, Clock, Flame, CheckCircle2, ChevronRight, ChevronDown, 
  Sparkles, BookOpen, Target, CheckSquare, Square, ShieldCheck, Award
} from 'lucide-react';
import { Exam, RoadmapTrack } from '../types/exam';

interface PreparationPlannerProps {
  exam: Exam;
}

export const PreparationPlanner: React.FC<PreparationPlannerProps> = ({ exam }) => {
  const tracks = exam.roadmapTracks || [];
  const [selectedTrackId, setSelectedTrackId] = useState<string>(tracks[0]?.id || 'TRACK_90_DAYS');
  const [expandedPhase, setExpandedPhase] = useState<number>(1);
  const [completedGoals, setCompletedGoals] = useState<Record<string, boolean>>({});

  const currentTrack: RoadmapTrack = tracks.find(t => t.id === selectedTrackId) || tracks[0];

  const toggleGoal = (goalKey: string) => {
    setCompletedGoals(prev => ({ ...prev, [goalKey]: !prev[goalKey] }));
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
