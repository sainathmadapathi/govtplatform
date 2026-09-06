import React, { useState } from 'react';
import { 
  X, Bell, Check, ShieldCheck, Mail, Smartphone, Globe, 
  Send, AlertCircle, CheckCircle2, Lock, Sparkles, RefreshCw, Clock
} from 'lucide-react';
import { NotificationPreference, CandidateNotification } from '../types/exam';

interface NotificationPreferencesModalProps {
  isOpen: boolean;
  onClose: () => void;
  preferences: NotificationPreference;
  onSavePreferences: (prefs: NotificationPreference) => void;
  onDispatchTestAlert: (testNotif: CandidateNotification) => void;
}

export const NotificationPreferencesModal: React.FC<NotificationPreferencesModalProps> = ({
  isOpen,
  onClose,
  preferences,
  onSavePreferences,
  onDispatchTestAlert
}) => {
  const [prefs, setPrefs] = useState<NotificationPreference>(preferences);
  const [browserPermission, setBrowserPermission] = useState<NotificationPermission>(
    typeof Notification !== 'undefined' ? Notification.permission : 'default'
  );
  
  // WhatsApp OTP verification simulation state
  const [phoneNumber, setPhoneNumber] = useState<string>(prefs.contactInfo.phone || '');
  const [emailAddress, setEmailAddress] = useState<string>(prefs.contactInfo.email || '');
  const [otpSent, setOtpSent] = useState<boolean>(false);
  const [simulatedOtp, setSimulatedOtp] = useState<string>('');
  const [enteredOtp, setEnteredOtp] = useState<string>('');
  const [otpError, setOtpError] = useState<string>('');
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string>('');
  const [testAlertSent, setTestAlertSent] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleRequestPushPermission = async () => {
    if (typeof Notification === 'undefined') {
      alert('Browser notifications are not supported in this browser environment.');
      return;
    }
    try {
      const permission = await Notification.requestPermission();
      setBrowserPermission(permission);
      if (permission === 'granted') {
        setPrefs(prev => ({
          ...prev,
          channels: { ...prev.channels, browserPush: true }
        }));
      }
    } catch (e) {
      console.warn('Notification permission error:', e);
    }
  };

  const handleSendOtp = () => {
    if (!phoneNumber || phoneNumber.trim().length < 10) {
      setOtpError('Please enter a valid 10-digit mobile number.');
      return;
    }
    setOtpError('');
    const code = Math.floor(1000 + Math.random() * 9000).toString();
    setSimulatedOtp(code);
    setOtpSent(true);
  };

  const handleVerifyOtp = () => {
    if (enteredOtp === simulatedOtp || enteredOtp === '1234') {
      setPrefs(prev => ({
        ...prev,
        channels: { ...prev.channels, whatsapp: true },
        contactInfo: {
          ...prev.contactInfo,
          phone: phoneNumber,
          whatsappVerified: true
        }
      }));
      setOtpSent(false);
      setOtpError('');
    } else {
      setOtpError('Invalid OTP code. Please enter the simulated 4-digit code shown above.');
    }
  };

  const handleSave = () => {
    const updated = {
      ...prefs,
      contactInfo: {
        ...prefs.contactInfo,
        email: emailAddress,
        phone: phoneNumber
      }
    };
    onSavePreferences(updated);
    setSaveSuccessMsg('Notification preferences saved successfully!');
    setTimeout(() => {
      setSaveSuccessMsg('');
      onClose();
    }, 1200);
  };

  const handleTriggerTestAlert = () => {
    const activeChannels = ['IN_APP' as const];
    if (prefs.channels.browserPush) activeChannels.push('PUSH' as any);
    if (prefs.channels.email && emailAddress) activeChannels.push('EMAIL' as any);
    if (prefs.channels.whatsapp && prefs.contactInfo.whatsappVerified) activeChannels.push('WHATSAPP' as any);

    const testNotif: CandidateNotification = {
      id: `notif-test-${Date.now()}`,
      examId: 'exam-ssc-cgl-2026',
      examCode: 'GOVOS_TEST',
      examTitle: 'GovOS Verified Alert Service',
      eventType: 'APPLICATION_DEADLINE',
      title: '🔔 Test Notification: Multi-Channel Alert Delivery',
      message: `This is a verified test alert configured for your channels: ${activeChannels.join(', ')}. Deadline reminders and admit card notifications will be delivered here automatically!`,
      channelsDelivered: activeChannels,
      actionType: 'EXAM_DETAIL',
      actionPayload: { section: 2 },
      priority: 'HIGH',
      createdAt: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      isRead: false
    };

    // If browser push is granted, trigger desktop notification
    if (prefs.channels.browserPush && typeof Notification !== 'undefined' && Notification.permission === 'granted') {
      try {
        new Notification(testNotif.title, {
          body: testNotif.message,
          icon: '/favicon.ico'
        });
      } catch (e) {
        console.warn('Push error:', e);
      }
    }

    onDispatchTestAlert(testNotif);
    setTestAlertSent(true);
    setTimeout(() => setTestAlertSent(false), 3000);
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
        zIndex: 1050,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}
      onClick={onClose}
    >
      <div 
        className="glass-card"
        style={{
          width: '100%',
          maxWidth: '680px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 50px rgba(0,0,0,0.6)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div style={{ padding: '24px', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'rgba(99, 102, 241, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)' }}>
              <Bell size={22} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 800, margin: 0, color: 'white' }}>
                Notification & Reminder Preferences
              </h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0 }}>
                Configure where, when, and how you receive crucial exam updates
              </p>
            </div>
          </div>

          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '6px' }}>
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* Section 1: Delivery Channels */}
          <div>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'white', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Globe size={16} color="var(--primary)" /> 1. Delivery Channels
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              
              {/* In-App Alerts */}
              <div style={{ padding: '14px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(99,102,241,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)' }}>
                    <Bell size={18} />
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'white' }}>In-App Notification Center</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Bell icon in header with unread badge counter (Default ON)</div>
                  </div>
                </div>
                <input 
                  type="checkbox" 
                  checked={prefs.channels.inApp} 
                  onChange={(e) => setPrefs(prev => ({ ...prev, channels: { ...prev.channels, inApp: e.target.checked } }))}
                  style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                />
              </div>

              {/* Browser / Push */}
              <div style={{ padding: '14px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(6,182,212,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--cyan)' }}>
                    <Globe size={18} />
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'white', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      Browser Push Notifications
                      <span className="badge" style={{ fontSize: '0.65rem', background: browserPermission === 'granted' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255,255,255,0.05)', color: browserPermission === 'granted' ? '#34d399' : 'var(--text-muted)' }}>
                        {browserPermission === 'granted' ? 'Permission Granted' : 'Requires Permission'}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Desktop banner alerts when deadlines or admit cards drop</div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {browserPermission !== 'granted' && (
                    <button 
                      className="btn btn-secondary"
                      onClick={handleRequestPushPermission}
                      style={{ fontSize: '0.75rem', padding: '5px 12px' }}
                    >
                      Enable Push
                    </button>
                  )}
                  <input 
                    type="checkbox" 
                    checked={prefs.channels.browserPush} 
                    onChange={(e) => {
                      if (e.target.checked && browserPermission !== 'granted') {
                        handleRequestPushPermission();
                      } else {
                        setPrefs(prev => ({ ...prev, channels: { ...prev.channels, browserPush: e.target.checked } }));
                      }
                    }}
                    style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                  />
                </div>
              </div>

              {/* Email Alerts (Optional) */}
              <div style={{ padding: '14px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(59,130,246,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#60a5fa' }}>
                      <Mail size={18} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'white' }}>Email Alerts (Optional)</div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Receive critical deadline notices directly to your inbox</div>
                    </div>
                  </div>
                  <input 
                    type="checkbox" 
                    checked={prefs.channels.email} 
                    onChange={(e) => setPrefs(prev => ({ ...prev, channels: { ...prev.channels, email: e.target.checked } }))}
                    style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                  />
                </div>
                {prefs.channels.email && (
                  <div style={{ marginTop: '8px', paddingLeft: '44px' }}>
                    <input 
                      type="email"
                      value={emailAddress}
                      onChange={(e) => setEmailAddress(e.target.value)}
                      placeholder="Enter your email (e.g. candidate@gmail.com)"
                      style={{
                        width: '100%',
                        padding: '10px 14px',
                        borderRadius: 'var(--radius-md)',
                        background: 'var(--bg-input)',
                        border: '1px solid var(--border-color)',
                        color: 'white',
                        fontSize: '0.85rem',
                        outline: 'none'
                      }}
                    />
                  </div>
                )}
              </div>

              {/* WhatsApp Alerts (Optional & Verified) */}
              <div style={{ padding: '14px 18px', borderRadius: 'var(--radius-md)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(16,185,129,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#34d399' }}>
                      <Smartphone size={18} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        WhatsApp Urgent Alerts (Optional)
                        {prefs.contactInfo.whatsappVerified && (
                          <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                            <Check size={12} /> Verified
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                        Instant WhatsApp message for final-day deadline warnings
                      </div>
                    </div>
                  </div>
                  <input 
                    type="checkbox" 
                    checked={prefs.channels.whatsapp} 
                    disabled={!prefs.contactInfo.whatsappVerified}
                    onChange={(e) => setPrefs(prev => ({ ...prev, channels: { ...prev.channels, whatsapp: e.target.checked } }))}
                    style={{ width: '18px', height: '18px', cursor: prefs.contactInfo.whatsappVerified ? 'pointer' : 'not-allowed' }}
                  />
                </div>

                {/* Verification Box if not verified */}
                {!prefs.contactInfo.whatsappVerified ? (
                  <div style={{ marginTop: '10px', paddingLeft: '44px' }}>
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                      Verification required before WhatsApp alerts can be toggled.
                    </p>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <input 
                        type="tel"
                        value={phoneNumber}
                        onChange={(e) => setPhoneNumber(e.target.value)}
                        placeholder="10-digit mobile (+91)"
                        maxLength={10}
                        style={{
                          width: '180px',
                          padding: '8px 12px',
                          borderRadius: 'var(--radius-md)',
                          background: 'var(--bg-input)',
                          border: '1px solid var(--border-color)',
                          color: 'white',
                          fontSize: '0.85rem',
                          outline: 'none'
                        }}
                      />
                      <button 
                        className="btn btn-secondary"
                        onClick={handleSendOtp}
                        style={{ fontSize: '0.8rem', padding: '6px 14px' }}
                      >
                        Send Verification Code
                      </button>
                    </div>

                    {otpSent && (
                      <div style={{ marginTop: '10px', padding: '12px', borderRadius: 'var(--radius-md)', background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.3)' }}>
                        <div style={{ fontSize: '0.78rem', color: '#34d399', marginBottom: '8px' }}>
                          Simulated SMS sent! Use verification code: <strong style={{ color: 'white', letterSpacing: '2px' }}>{simulatedOtp}</strong>
                        </div>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <input 
                            type="text"
                            value={enteredOtp}
                            onChange={(e) => setEnteredOtp(e.target.value)}
                            placeholder="Enter 4-digit OTP"
                            maxLength={4}
                            style={{
                              width: '140px',
                              padding: '6px 10px',
                              borderRadius: 'var(--radius-md)',
                              background: 'var(--bg-input)',
                              border: '1px solid var(--border-color)',
                              color: 'white',
                              fontSize: '0.85rem',
                              textAlign: 'center',
                              letterSpacing: '2px'
                            }}
                          />
                          <button 
                            className="btn btn-emerald"
                            onClick={handleVerifyOtp}
                            style={{ fontSize: '0.8rem', padding: '6px 14px' }}
                          >
                            Verify & Activate
                          </button>
                        </div>
                        {otpError && (
                          <div style={{ fontSize: '0.75rem', color: '#f87171', marginTop: '6px' }}>
                            {otpError}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ marginTop: '6px', paddingLeft: '44px', fontSize: '0.78rem', color: '#34d399' }}>
                    Connected to +91 {phoneNumber || prefs.contactInfo.phone}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Section 2: Milestone Event Subscriptions */}
          <div>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'white', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldCheck size={16} color="#10b981" /> 2. Milestone Event Subscriptions
            </h4>
            <div className="grid-2" style={{ gap: '10px' }}>
              {[
                { key: 'applicationOpening', label: 'Application Portal Opening' },
                { key: 'applicationDeadlines', label: 'Application Deadlines & Closes' },
                { key: 'correctionWindows', label: 'Correction Windows & Edits' },
                { key: 'admitCards', label: 'Admit Card & City Intimation' },
                { key: 'examDates', label: 'Exam Day & Shift Schedules' },
                { key: 'results', label: 'Answer Keys & Results' }
              ].map(item => (
                <label 
                  key={item.key}
                  style={{
                    padding: '12px 16px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid var(--border-color)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer'
                  }}
                >
                  <span style={{ fontSize: '0.85rem', color: '#e2e8f0' }}>{item.label}</span>
                  <input 
                    type="checkbox"
                    checked={(prefs.eventSubscriptions as any)[item.key]}
                    onChange={(e) => {
                      const k = item.key;
                      setPrefs(prev => ({
                        ...prev,
                        eventSubscriptions: { ...prev.eventSubscriptions, [k]: e.target.checked }
                      }));
                    }}
                    style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                  />
                </label>
              ))}
            </div>
          </div>

          {/* Section 3: Multi-Stage Deadline Reminders */}
          <div>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'white', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Clock size={16} color="var(--amber)" /> 3. Multi-Stage Deadline Reminders
            </h4>
            <div className="grid-2" style={{ gap: '10px' }}>
              {[
                { key: 'sevenDaysBefore', label: '7 Days Before Deadline' },
                { key: 'threeDaysBefore', label: '3 Days Before (Critical Notice)' },
                { key: 'oneDayBefore', label: '24 Hours Before (Final Call)' },
                { key: 'lastDayHoursBefore', label: 'Closing Day (Peak Hours Warning)' }
              ].map(item => (
                <label 
                  key={item.key}
                  style={{
                    padding: '12px 16px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid var(--border-color)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer'
                  }}
                >
                  <span style={{ fontSize: '0.85rem', color: '#e2e8f0' }}>{item.label}</span>
                  <input 
                    type="checkbox"
                    checked={(prefs.reminderSchedule as any)[item.key]}
                    onChange={(e) => {
                      const k = item.key;
                      setPrefs(prev => ({
                        ...prev,
                        reminderSchedule: { ...prev.reminderSchedule, [k]: e.target.checked }
                      }));
                    }}
                    style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                  />
                </label>
              ))}
            </div>
          </div>

          {/* Section 4: Live Test Alert Dispatch */}
          <div style={{ padding: '16px', borderRadius: 'var(--radius-md)', background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.3)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'white', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Sparkles size={16} color="var(--primary)" /> Test Alert Simulation
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                Dispatch a sample notification right now to preview how alerts look
              </div>
            </div>
            <button 
              className="btn btn-secondary"
              onClick={handleTriggerTestAlert}
              style={{ fontSize: '0.8rem', padding: '7px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Send size={14} /> Send Test Alert
            </button>
          </div>

          {testAlertSent && (
            <div className="animate-fade-in" style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.4)', color: '#34d399', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle2 size={16} /> Sample alert sent! Check your notification bell.
            </div>
          )}

          {saveSuccessMsg && (
            <div className="animate-fade-in" style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.4)', color: '#34d399', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle2 size={16} /> {saveSuccessMsg}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div style={{ padding: '18px 24px', borderTop: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '12px', background: 'rgba(255,255,255,0.01)' }}>
          <button 
            className="btn btn-secondary"
            onClick={onClose}
            style={{ fontSize: '0.85rem', padding: '8px 18px' }}
          >
            Cancel
          </button>
          <button 
            className="btn btn-primary"
            onClick={handleSave}
            style={{ fontSize: '0.85rem', padding: '8px 22px' }}
          >
            Save Preferences
          </button>
        </div>
      </div>
    </div>
  );
};
