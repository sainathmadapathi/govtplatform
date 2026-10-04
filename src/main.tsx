// GovOS entry point: application shell, global modals and React root.

import React, { useEffect, useMemo, useState, useRef } from 'react';
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
  NotificationPreference,
  ResourceItem,
  SyllabusRevision,
  ExamFactOverlay
} from './types';
import {
  ALL_EXAMS,
  SSC_CGL_EXAM
} from './data';
import {
  applySyllabusRevisions,
  applyExamOverlays,
  examOverlayService,
  examRegistryService,
  getExamUniverse,
  storageService,
  syllabusLiveService
} from './services';

import {
  AdminVerificationPanel,
  AIAssistant,
  assistantDestination,
  notificationDestination,
  GovOSTab,
  EligibilityCalculator,
  ExamCalendar,
  ExamCompare,
  EvidencePanel,
  ExamDetailView,
  ExamFinder,
  Header,
  MyExams,
  NotificationCenterModal,
  NotificationPreferencesModal,
  ExamPracticeRouter,
  PreparationPlanner,
  ResourceLibrary,
  ResourceReaderModal,
  installRevealObserver,
  installSmoothWheel,
  useReplayOnChange
} from './ui';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<GovOSTab>('FINDER');

  // Motion (presentation only): card reveals as they enter the viewport, a lerped wheel, and a short entrance
  // whenever the view changes. Each is a no-op under prefers-reduced-motion. See ANIMATION_REVERSE_ENGINEERING.md.
  const viewRef = useRef<HTMLElement>(null);
  useReplayOnChange(viewRef, activeTab, 'view-enter');
  useEffect(() => {
    const root = document.getElementById('root');
    const stopReveal = root ? installRevealObserver(root) : () => undefined;
    const stopWheel = installSmoothWheel();
    return () => { stopReveal(); stopWheel(); };
  }, []);
  /** Guide section to open when something deep-links into the Exam Guide (1-16). */
  const [examSection, setExamSection] = useState<number>(1);
  const [resourceForReader, setResourceForReader] = useState<ResourceItem | null>(null);

  /**
   * The exam the candidate is working inside - the context every exam-scoped feature reads.
   * Restored from the last session, so reopening GovOS lands where they left off.
   */
  const [selectedExam, setSelectedExam] = useState<Exam>(() => {
    const savedId = storageService.getCurrentExamId();
    return ALL_EXAMS.find(e => e.id === savedId) || SSC_CGL_EXAM;
  });

  /**
   * Runtime exam registry (Phase 3): machine-acquired exams served by the engine. The exam
   * universe every finder, shelf and notification reads is authored ∪ runtime; the authored
   * register stands alone if the server cannot be reached. A saved current exam that lives in
   * the registry is restored once the registry has loaded.
   */
  const [registryExams, setRegistryExams] = useState<Exam[]>([]);
  /** An exam an alert or the saved session names that GovOS does not hold: said, never replaced by another. */
  const [examNotice, setExamNotice] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    examRegistryService.loadWithStatus().then(({ exams: found, status }) => {
      if (cancelled || status === 'SUPERSEDED') return;
      setRegistryExams(found);
      const savedId = storageService.getCurrentExamId();
      if (savedId && !ALL_EXAMS.some(e => e.id === savedId)) {
        const restored = found.find(e => e.id === savedId);
        if (restored) setSelectedExam(restored);
        // Not silently another exam: say the saved one is not here, and why, as far as GovOS can tell.
        else setExamNotice(status === 'FAILED'
          ? `The exam you last opened (${savedId}) is held on the GovOS server, which could not be reached. Nothing else was opened in its place; reload to try again.`
          : `The exam you last opened (${savedId}) is no longer in GovOS's register. No other exam was opened in its place.`);
      }
    });
    return () => { cancelled = true; };
  }, []);
  const examUniverse = useMemo(() => getExamUniverse(ALL_EXAMS, registryExams), [registryExams]);

  /**
   * Every navigation request goes through here.
   *
   * Practice, Resources and the Study Roadmap used to be top-level tabs as well as sections
   * of the exam they describe. They now live only inside the exam, so a request for one of
   * those tabs is translated into the exam page at the matching section. The tab ids stay
   * part of GovOSTab, which keeps every existing assistant action, notification and button
   * working without a rewrite.
   */
  const EXAM_SCOPED_TABS: Partial<Record<GovOSTab, number>> = {
    PRACTICE: 9,    // Practice & PYQs
    RESOURCES: 8,   // Resources
    PLANNER: 7      // Study Roadmap
  };

  const navigate = (tab: GovOSTab, section?: number, examId?: string) => {
    // An assistant action names the exam its answer was about: open that exam, not the one open now.
    const destination = assistantDestination({ tab, section, examId }, selectedExam, examUniverse);
    if (!destination) {
      console.warn(`[GovOS] An action for exam "${examId}" was not followed: that exam is not in the register.`);
      setExamNotice(`That link refers to an exam GovOS does not hold (${examId}). Nothing was opened.`);
      return;
    }
    if (destination.exam.id !== selectedExam.id) {
      setSelectedExam(destination.exam);
      storageService.setCurrentExamId(destination.exam.id);
    }
    const movedTo = EXAM_SCOPED_TABS[tab];
    if (movedTo !== undefined) {
      setExamSection(section || movedTo);
      setActiveTab('EXAM_DETAIL');
    } else {
      if (section) setExamSection(section);
      setActiveTab(tab);
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  /** Used by the assistant's "take me there" buttons. */
  const handleAssistantNavigate = navigate;

  /**
   * The syllabus a candidate sees is the register's seed plus whatever a verifier has
   * applied since, read from the server. Re-read when the exam changes and whenever the
   * exam page is entered, so a revision applied in the Trust Panel shows without a reload.
   */
  const [syllabusRevisions, setSyllabusRevisions] = useState<SyllabusRevision[]>([]);
  const [syllabusReadCount, setSyllabusReadCount] = useState<number>(0);
  useEffect(() => {
    let cancelled = false;
    // A failed read keeps what was applied (applySyllabusRevisions only ever applies this exam's own):
    // a network blip used to set this to [] and silently put the unrevised syllabus back on the page.
    syllabusLiveService.revisionsOrNull(selectedExam.id).then(found => {
      if (!cancelled && found !== null) setSyllabusRevisions(found);
    });
    return () => { cancelled = true; };
  }, [selectedExam.id, activeTab, syllabusReadCount]);

  /** Canonical fact overlays (Phase 1) */
  const [examOverlays, setExamOverlays] = useState<ExamFactOverlay[]>([]);
  useEffect(() => {
    let cancelled = false;
    examOverlayService.getOverlaysOrNull(selectedExam.id).then(found => {
      if (!cancelled && found !== null) setExamOverlays(found);
    });
    return () => { cancelled = true; };
  }, [selectedExam.id, activeTab]);

  /** The exam every exam-scoped feature is handed: identity from the register, syllabus as revised, plus canonical fact overlays. */
  const liveExam = useMemo(() => {
    const withSyllabus = applySyllabusRevisions(selectedExam, syllabusRevisions);
    return applyExamOverlays(withSyllabus, examOverlays);
  }, [selectedExam, syllabusRevisions, examOverlays]);

  
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
  const reportSendingRef = useRef<boolean>(false);
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
      const generated = storageService.generatePersonalizedNotificationsForTrackedExams(getExamUniverse(ALL_EXAMS));
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
    const regenerated = storageService.generatePersonalizedNotificationsForTrackedExams(getExamUniverse(ALL_EXAMS));
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
    const regenerated = storageService.generatePersonalizedNotificationsForTrackedExams(getExamUniverse(ALL_EXAMS));
    setNotifications(regenerated);
  };

  const handleDispatchTestAlert = (testNotif: CandidateNotification) => {
    const current = storageService.getNotifications();
    const updated = [testNotif, ...current];
    storageService.saveNotifications(updated);
    setNotifications(updated);
  };

  /**
   * A notification is always about one exam, so it opens that exam at the section it names.
   * actionPayload.section was already being written by the generator and ignored here; it is
   * honoured now, with a sensible section per action type as the fallback.
   */
  const handleNotificationAction = (notif: CandidateNotification) => {
    // The exam the alert names, or nothing: it used to open the register's first exam (SSC CGL) for an alert
    // whose exam GovOS no longer holds.
    const destination = notificationDestination(notif, examUniverse);
    setIsNotificationsModalOpen(false);
    if (!destination) {
      setExamNotice(`This alert refers to an exam GovOS does not hold (${notif.examId || 'no exam named'}). Nothing was opened.`);
      return;
    }
    setSelectedExam(destination.exam);
    storageService.setCurrentExamId(destination.exam.id);
    navigate('EXAM_DETAIL', destination.section, destination.exam.id);
  };

  const handleSelectExam = (exam: Exam) => {
    setSelectedExam(exam);
    storageService.setCurrentExamId(exam.id);
    // A different exam opens at its own overview, not at whichever section was last read.
    setExamSection(1);
    setActiveTab('EXAM_DETAIL');
    storageService.recordInteraction({
      type: 'VIEW',
      examId: exam.id
    });
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
    // One report per send: a second click while the first is on its way used to file it twice.
    if (!reportModalData || reportSendingRef.current) return;
    reportSendingRef.current = true;
    let result: { delivered: boolean };
    try {
      result = await storageService.submitReport({
        entityType: reportModalData.entityType,
        entityId: reportModalData.entityId,
        description: reportDescription
      });
    } finally {
      reportSendingRef.current = false;
    }
    setReportDelivered(result.delivered);
    setReportSubmitted(true);
    setTimeout(() => {
      setReportModalData(null);
    }, 2200);
  };

  const unreadCount = notifications.filter(n => !n.isRead).length;

  return (
    <div className="app-container" style={activeTab === 'EXAM_DETAIL' ? { paddingBottom: '12px' } : undefined}>
      {/* Top Header */}
      <Header 
        activeTab={activeTab}
        setActiveTab={navigate}
        selectedExamTitle={selectedExam.title}
        unreadCount={unreadCount}
        trackedCount={trackedExamIds.length}
        onOpenNotifications={() => setIsNotificationsModalOpen(true)}
        onOpenTimeline={() => setActiveTab('CALENDAR')}
      />

      {examNotice && (
        <div role="alert" data-exam-notice="unresolved" style={{ margin: '0 auto 12px', maxWidth: '1200px', padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'var(--amber-soft)', border: '1px solid var(--border-color)', color: 'var(--text-primary)', fontSize: '0.86rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
          <span>{examNotice}</span>
          <button className="btn btn-secondary" onClick={() => setExamNotice(null)} style={{ fontSize: '0.78rem', padding: '4px 10px', flexShrink: 0 }}>Dismiss</button>
        </div>
      )}

      {/* View Render */}
      <main ref={viewRef} style={{ paddingBottom: activeTab === 'EXAM_DETAIL' ? '0' : '60px' }}>
        {activeTab === 'FINDER' && (
          <ExamFinder
            exams={examUniverse}
            onOpenProvenanceModal={handleOpenProvenance}
            onNavigate={navigate}
            onSelectExam={handleSelectExam}
            onNavigateEligibility={() => setActiveTab('ELIGIBILITY')}
            trackedExamIds={trackedExamIds}
            onToggleTrackExam={handleToggleTrackExam}
          />
        )}

        {activeTab === 'ELIGIBILITY' && (
          <EligibilityCalculator
            exam={liveExam}
            onSelectExam={handleSelectExam}
            onOpenProvenanceModal={handleOpenProvenance}
          />
        )}

        {activeTab === 'EXAM_DETAIL' && (
          <ExamDetailView
            // One exam, one page: a switch while the page is open (a notification, the registry restoring
            // the saved exam) mounts the next exam's page fresh at the section asked for. Each section also
            // resets or reloads its own exam-scoped state on a switch, so this is not the only guard.
            key={selectedExam.id}
            exam={liveExam}
            onSyllabusOpened={() => setSyllabusReadCount(n => n + 1)}
            onBackHome={() => navigate('FINDER')}
            onAskAI={() => navigate('AI_ASSISTANT')}
            initialSection={examSection}
            onOpenProvenanceModal={handleOpenProvenance}
            onOpenReportModal={handleOpenReport}
            onNavigateEligibility={() => setActiveTab('ELIGIBILITY')}
            onNavigatePlanner={() => setActiveTab('PLANNER')}
            onNavigatePractice={() => setActiveTab('PRACTICE')}
            isTracked={trackedExamIds.includes(selectedExam.id)}
            onToggleTrack={() => handleToggleTrackExam(selectedExam.id)}
          />
        )}

        {/* PLANNER / PRACTICE / RESOURCES now live inside the exam page (sections 07, 09, 08)
            and navigate() sends every request there. These renders stay as a safety net, so a
            path that sets the tab directly still shows the real feature rather than a blank
            screen - they mount the very same components the exam page mounts. */}
        {activeTab === 'PLANNER' && (
          <PreparationPlanner
            exam={liveExam}
          />
        )}

        {/* The safety-net tab goes through the same router as sections 09 and 17, so no two
            entry points can disagree about which engine an exam gets. */}
        {activeTab === 'PRACTICE' && (
          <ExamPracticeRouter
            exam={liveExam}
            onOpenProvenanceModal={handleOpenProvenance}
          />
        )}

        {activeTab === 'RESOURCES' && (
          <ResourceLibrary
            exam={liveExam}
            showSectionNumber={false}
            onOpenResource={(res) => setResourceForReader(res)}
            onOpenProvenanceModal={handleOpenProvenance}
          />
        )}

        {activeTab === 'MY_EXAMS' && (
          <MyExams
            exams={examUniverse}
            trackedExamIds={trackedExamIds}
            // The exam the candidate last opened, as stored -- not the shell's starting exam, which is SSC CGL
            // for someone who has opened nothing and would put it on their shelf uninvited.
            currentExamId={storageService.getCurrentExamId()}
            onSelectExam={handleSelectExam}
            onToggleTrackExam={handleToggleTrackExam}
            onFindExams={() => navigate('FINDER')}
          />
        )}

        {activeTab === 'COMPARE' && (
          <ExamCompare 
            onSelectExam={handleSelectExam}
          />
        )}

        {/* Cross-exam calendar. A single exam's own timeline is section 02 of that exam. */}
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
            exam={liveExam}
            onOpenProvenanceModal={handleOpenProvenance}
            onNavigate={handleAssistantNavigate}
          />
        )}

        {activeTab === 'ADMIN' && (
          <AdminVerificationPanel 
            onOpenProvenanceModal={handleOpenProvenance}
          />
        )}
      </main>

      {/* Resource reader / video player, opened from the Resources tab */}
      {resourceForReader && (
        <ResourceReaderModal
          resource={resourceForReader}
          onClose={() => setResourceForReader(null)}
        />
      )}

      {/* Evidence: one panel for every cited fact on every exam */}
      {provenanceModalData && (
        <div className="modal-overlay" onClick={() => setProvenanceModalData(null)}>
          <div className="modal-content animate-fade-in" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '640px' }}>
            <EvidencePanel provenance={provenanceModalData} onClose={() => setProvenanceModalData(null)} />
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
                      color: 'var(--text-primary)',
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
