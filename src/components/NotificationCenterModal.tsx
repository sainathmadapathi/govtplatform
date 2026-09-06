import React, { useState } from 'react';
import { 
  Bell, X, CheckCheck, Trash2, Settings, ExternalLink, 
  AlertTriangle, Clock, Calendar, CheckCircle2, Award, 
  FileText, ArrowRight, ShieldCheck, Smartphone, Mail, Globe
} from 'lucide-react';
import { CandidateNotification, NotificationEventType } from '../types/exam';

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
