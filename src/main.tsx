// GovOS entry point: application shell, global modals and React root.

import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import {
  BookOpen,
  CheckCircle2,
  ExternalLink,
  FileText,
  Flag,
  Quote,
  ShieldCheck,
  X
} from 'lucide-react';
import {
  CandidateNotification,
  DataProvenance,
  Exam,
  NotificationPreference
} from './types';
import {
  ALL_EXAMS,
  SSC_CGL_EXAM
} from './data';
import {
  storageService
} from './services';
import {
  AdminVerificationPanel,
  AIAssistant,
  EligibilityCalculator,
  ExamCalendar,
  ExamCompare,
  ExamDetailView,
  ExamFinder,
  Header,
  NotificationCenterModal,
  NotificationPreferencesModal,
  PracticeEngine,
  PreparationPlanner
} from './ui';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'FINDER' | 'ELIGIBILITY' | 'EXAM_DETAIL' | 'PLANNER' | 'PRACTICE' | 'COMPARE' | 'CALENDAR' | 'AI_ASSISTANT' | 'ADMIN'>('FINDER');
  const [selectedExam, setSelectedExam] = useState<Exam>(SSC_CGL_EXAM);
  
  // Tracked Exams & Notifications State
  const [trackedExamIds, setTrackedExamIds] = useState<string[]>(() => storageService.getTrackedExams());
  const [notifications, setNotifications] = useState<CandidateNotification[]>(() => storageService.getNotifications());
  const [notificationPreferences, setNotificationPreferences] = useState<NotificationPreference>(() => storageService.getNotificationPreferences());
  const [isNotificationsModalOpen, setIsNotificationsModalOpen] = useState<boolean>(false);
  const [isPreferencesModalOpen, setIsPreferencesModalOpen] = useState<boolean>(false);

  // Modals state
  const [provenanceModalData, setProvenanceModalData] = useState<DataProvenance | null>(null);
  const [reportModalData, setReportModalData] = useState<{ open: boolean; entityType: string; entityId: string } | null>(null);
  const [reportSubmitted, setReportSubmitted] = useState<boolean>(false);
  const [reportDelivered, setReportDelivered] = useState<boolean>(true);
  const [reportDescription, setReportDescription] = useState<string>('');

  // Initial load and sync with SQLite
  useEffect(() => {
    const initNotificationsAndTimeline = async () => {
      // 1. Sync tracked exams from SQLite
      const remoteTracked = await storageService.loadTrackedExamsFromSQLite();
      setTrackedExamIds(remoteTracked);

      // 2. Sync notification preferences from SQLite
      const remotePrefs = await storageService.loadNotificationPreferencesFromSQLite();
      setNotificationPreferences(remotePrefs);

      // 3. Generate initial personalized notifications for tracked exams
      const generated = storageService.generatePersonalizedNotificationsForTrackedExams(ALL_EXAMS);
      setNotifications(generated);

      // 4. Retry any accuracy reports queued while the server was unreachable
      storageService.flushPendingReports();
    };

    initNotificationsAndTimeline();
  }, []);

  const handleToggleTrackExam = async (examId: string) => {
    const updated = await storageService.toggleTrackExam(examId);
    setTrackedExamIds(updated);
    // Regenerate notifications scoped strictly to newly tracked exams
    const regenerated = storageService.generatePersonalizedNotificationsForTrackedExams(ALL_EXAMS);
    setNotifications(regenerated);
  };

  const handleMarkNotificationAsRead = async (id: string) => {
    await storageService.markNotificationAsRead(id);
    setNotifications(storageService.getNotifications());
  };

  const handleClearAllNotifications = async () => {
    await storageService.clearAllNotifications();
    setNotifications([]);
  };

  const handleSavePreferences = async (newPrefs: NotificationPreference) => {
    await storageService.saveNotificationPreferences(newPrefs);
    setNotificationPreferences(newPrefs);
    const regenerated = storageService.generatePersonalizedNotificationsForTrackedExams(ALL_EXAMS);
    setNotifications(regenerated);
  };

  const handleDispatchTestAlert = (testNotif: CandidateNotification) => {
    const current = storageService.getNotifications();
    const updated = [testNotif, ...current];
    storageService.saveNotifications(updated);
    setNotifications(updated);
  };

  const handleNotificationAction = (notif: CandidateNotification) => {
    const targetExam = ALL_EXAMS.find(e => e.id === notif.examId) || ALL_EXAMS[0];
    setSelectedExam(targetExam);
    
    if (notif.actionType === 'CALENDAR' || notif.actionType === 'TIMELINE') {
      setActiveTab('CALENDAR');
    } else {
      setActiveTab('EXAM_DETAIL');
    }

    setIsNotificationsModalOpen(false);
  };

  const handleSelectExam = (exam: Exam) => {
    setSelectedExam(exam);
    setActiveTab('EXAM_DETAIL');
  };

  const handleOpenProvenance = (provenance: DataProvenance) => {
    setProvenanceModalData(provenance);
  };

  const handleOpenReport = (entityType: string, entityId: string) => {
    setReportModalData({ open: true, entityType, entityId });
    setReportSubmitted(false);
    setReportDescription('');
  };

  const handleSendReport = async () => {
    if (!reportModalData) return;
    const result = await storageService.submitReport({
      entityType: reportModalData.entityType,
      entityId: reportModalData.entityId,
      description: reportDescription
    });
    setReportDelivered(result.delivered);
    setReportSubmitted(true);
    setTimeout(() => {
      setReportModalData(null);
    }, 2200);
  };

  const unreadCount = notifications.filter(n => !n.isRead).length;

  return (
    <div className="app-container">
      {/* Top Header */}
      <Header 
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        selectedExamTitle={selectedExam.title}
        unreadCount={unreadCount}
        trackedCount={trackedExamIds.length}
        onOpenNotifications={() => setIsNotificationsModalOpen(true)}
        onOpenTimeline={() => setActiveTab('CALENDAR')}
      />

      {/* View Render */}
      <main style={{ paddingBottom: '60px' }}>
        {activeTab === 'FINDER' && (
          <ExamFinder 
            onSelectExam={handleSelectExam}
            onNavigateEligibility={() => setActiveTab('ELIGIBILITY')}
            trackedExamIds={trackedExamIds}
            onToggleTrackExam={handleToggleTrackExam}
          />
        )}

        {activeTab === 'ELIGIBILITY' && (
          <EligibilityCalculator 
            onSelectExam={handleSelectExam}
            onOpenProvenanceModal={handleOpenProvenance}
          />
        )}

        {activeTab === 'EXAM_DETAIL' && (
          <ExamDetailView 
            exam={selectedExam}
            onOpenProvenanceModal={handleOpenProvenance}
            onOpenReportModal={handleOpenReport}
            onNavigateEligibility={() => setActiveTab('ELIGIBILITY')}
            onNavigatePlanner={() => setActiveTab('PLANNER')}
            onNavigatePractice={() => setActiveTab('PRACTICE')}
            isTracked={trackedExamIds.includes(selectedExam.id)}
            onToggleTrack={() => handleToggleTrackExam(selectedExam.id)}
          />
        )}

        {activeTab === 'PLANNER' && (
          <PreparationPlanner 
            exam={selectedExam}
          />
        )}

        {activeTab === 'PRACTICE' && (
          <PracticeEngine 
            exam={selectedExam}
            onOpenProvenanceModal={handleOpenProvenance}
          />
        )}

        {activeTab === 'COMPARE' && (
          <ExamCompare 
            onSelectExam={handleSelectExam}
          />
        )}

        {activeTab === 'CALENDAR' && (
          <ExamCalendar 
            onSelectExam={handleSelectExam}
            trackedExamIds={trackedExamIds}
            onToggleTrackExam={handleToggleTrackExam}
            onOpenPreferences={() => setIsPreferencesModalOpen(true)}
          />
        )}

        {activeTab === 'AI_ASSISTANT' && (
          <AIAssistant 
            onOpenProvenanceModal={handleOpenProvenance}
          />
        )}

        {activeTab === 'ADMIN' && (
          <AdminVerificationPanel 
            onOpenProvenanceModal={handleOpenProvenance}
          />
        )}
      </main>

      {/* Field Provenance & Gazette Citation Modal */}
      {provenanceModalData && (
        <div className="modal-overlay" onClick={() => setProvenanceModalData(null)}>
          <div className="modal-content animate-fade-in" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '640px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <ShieldCheck size={26} color="var(--emerald)" />
                <h3 style={{ fontSize: '1.25rem', fontWeight: 800 }}>Field Provenance & Gazette Citation</h3>
              </div>
              <button 
                onClick={() => setProvenanceModalData(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={22} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '0.95rem' }}>
              <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.3)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span className="badge badge-verified">
                  {provenanceModalData.verificationLevel}
                </span>
                <span className={`taxonomy-tag taxonomy-${provenanceModalData.taxonomyType.toLowerCase()}`}>
                  TAXONOMY: {provenanceModalData.taxonomyType}
                </span>
              </div>

              <div>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Source Document Title:</span>
                <div style={{ fontWeight: 700, color: 'white', marginTop: '2px' }}>{provenanceModalData.documentTitle}</div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Official Page Number:</span>
                  <div style={{ fontWeight: 700, color: 'var(--primary)', fontFamily: 'var(--font-mono)' }}>Page {provenanceModalData.pageNumber || '1'}</div>
                </div>

                <div>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Clause / Section Reference:</span>
                  <div style={{ fontWeight: 700, color: 'var(--primary)', fontFamily: 'var(--font-mono)' }}>{provenanceModalData.clauseNumber || 'Section 1.1'}</div>
                </div>
              </div>

              {/* Direct Quoted Excerpt from Official Gazette */}
              {provenanceModalData.excerptText && (
                <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#93c5fd', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Quote size={14} /> Official Gazette Legal Excerpt
                  </span>
                  <div style={{ fontSize: '0.88rem', color: '#e2e8f0', lineHeight: 1.5, fontStyle: 'italic' }}>
                    "{provenanceModalData.excerptText}"
                  </div>
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Official Publication Date:</span>
                  <div>{provenanceModalData.publishedDate}</div>
                </div>

                <div>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>GovOS Audit Timestamp:</span>
                  <div>{provenanceModalData.verifiedDate}</div>
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Audited & Verified By:</span>
                <div style={{ fontWeight: 600, color: 'var(--emerald)' }}>{provenanceModalData.verifiedBy}</div>
              </div>

              <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button className="btn btn-secondary" onClick={() => setProvenanceModalData(null)}>
                  Close Audit
                </button>
                <a 
                  href={provenanceModalData.officialUrl || 'https://ssc.gov.in'} 
                  target="_blank" 
                  rel="noreferrer" 
                  className="btn btn-emerald" 
                  style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  Open Official Notices Portal <ExternalLink size={16} />
                </a>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* User Report Incorrect Information Modal */}
      {reportModalData && (
        <div className="modal-overlay" onClick={() => setReportModalData(null)}>
          <div className="modal-content animate-fade-in" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Flag size={24} color="var(--rose)" />
                <h3 style={{ fontSize: '1.25rem', fontWeight: 800 }}>Report Incorrect or Outdated Information</h3>
              </div>
              <button 
                onClick={() => setReportModalData(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={22} />
              </button>
            </div>

            {!reportSubmitted ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                  Help maintain platform trust. Your report will be immediately queued for human admin verification against official government sources.
                </p>

                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                    Describe Issue / Outdated Data
                  </label>
                  <textarea 
                    rows={4}
                    value={reportDescription}
                    onChange={(e) => setReportDescription(e.target.value)}
                    placeholder="e.g. The application deadline for SSC CGL was extended to 27 Sep via new notice..."
                    style={{
                      width: '100%',
                      padding: '12px',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--bg-input)',
                      border: '1px solid var(--border-color)',
                      color: 'white',
                      fontSize: '0.95rem',
                      outline: 'none'
                    }}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                  <button className="btn btn-secondary" onClick={() => setReportModalData(null)}>Cancel</button>
                  <button 
                    className="btn btn-emerald" 
                    onClick={handleSendReport}
                    disabled={!reportDescription.trim()}
                    style={{ opacity: reportDescription.trim() ? 1 : 0.5, cursor: reportDescription.trim() ? 'pointer' : 'not-allowed' }}
                  >
                    Submit Issue Report
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ padding: '24px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
                <CheckCircle2 size={48} color={reportDelivered ? 'var(--emerald)' : 'var(--amber)'} />
                <h4 style={{ fontSize: '1.2rem', fontWeight: 800 }}>
                  {reportDelivered ? 'Report Submitted to Admin Queue' : 'Report Saved — Will Sync Shortly'}
                </h4>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  {reportDelivered
                    ? 'Thank you for keeping GovOS authoritative and accurate!'
                    : 'The verification server is unreachable right now. Your report is stored on this device and will be sent automatically the next time GovOS connects.'}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Candidate Notification Center Drawer/Modal */}
      <NotificationCenterModal 
        isOpen={isNotificationsModalOpen}
        onClose={() => setIsNotificationsModalOpen(false)}
        notifications={notifications}
        onMarkAsRead={handleMarkNotificationAsRead}
        onClearAll={handleClearAllNotifications}
        onOpenPreferences={() => {
          setIsNotificationsModalOpen(false);
          setIsPreferencesModalOpen(true);
        }}
        onNotificationAction={handleNotificationAction}
      />

      {/* Candidate Notification Preferences Modal */}
      <NotificationPreferencesModal 
        isOpen={isPreferencesModalOpen}
        onClose={() => setIsPreferencesModalOpen(false)}
        preferences={notificationPreferences}
        onSavePreferences={handleSavePreferences}
        onDispatchTestAlert={handleDispatchTestAlert}
      />

    </div>
  );
};


// ==========================================================================
// React root
// ==========================================================================
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
