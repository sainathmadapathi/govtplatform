import React, { useState, useEffect } from 'react';
import { 
  Target, ShieldCheck, CheckCircle2, XCircle, AlertTriangle, BookOpen, 
  HelpCircle, Award, Layers, Zap, Clock, FileText, ChevronRight, Download, 
  PlayCircle, ExternalLink, Activity, Eye, Compass, Database, RefreshCw
} from 'lucide-react';
import { PostStudyPath, StudyModuleRequirement, ExcludedModule, RequirementProvenanceType } from '../types/exam';
import { ALL_POST_STUDY_PATHS } from '../data/postStudyPathsData';
import { storageService } from '../services/storageService';

interface PostStudyPathEngineProps {
  onOpenProvenanceModal?: (prov: any) => void;
  onNavigatePractice?: () => void;
}

export const PostStudyPathEngine: React.FC<PostStudyPathEngineProps> = ({
  onOpenProvenanceModal,
  onNavigatePractice
}) => {
  const [selectedPostId, setSelectedPostId] = useState<string>(() => storageService.getTargetPost());
  const [selectedStage, setSelectedStage] = useState<'ALL' | 'TIER_1' | 'TIER_2'>('ALL');
  const [completedModules, setCompletedModules] = useState<Record<string, boolean>>(() => storageService.getCompletedModules());
  const [syncStatus, setSyncStatus] = useState<string>('Local Storage & SQLite Saved');
  const [isSyncing, setIsSyncing] = useState<boolean>(false);

  const currentPath: PostStudyPath = ALL_POST_STUDY_PATHS[selectedPostId] || ALL_POST_STUDY_PATHS['post-aso-css'];

  const handleSelectPost = (postId: string) => {
    setSelectedPostId(postId);
    storageService.setTargetPost(postId);
  };

  const toggleModule = (id: string) => {
    const updated = storageService.toggleCompletedModule(id);
    setCompletedModules({ ...updated });
  };

  const handleManualSync = async () => {
    setIsSyncing(true);
    setSyncStatus('Syncing with govos.db...');
    const result = await storageService.syncAllToSQLite();
    setIsSyncing(false);
    setSyncStatus(result.success ? 'Synced to SQLite (govos.db)' : 'Offline Local Storage Active');
  };

  const getProvenanceBadge = (type: RequirementProvenanceType) => {
    switch (type) {
      case 'OFFICIAL_REQUIREMENT':
        return (
          <span className="badge badge-verified" style={{ fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <ShieldCheck size={12} /> OFFICIAL REQUIREMENT
          </span>
        );
      case 'PREPARATION_TOPIC':
        return (
          <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', fontSize: '0.7rem' }}>
            SYLLABUS TOPIC
          </span>
        );
      case 'RECOMMENDED_PREPARATION':
        return (
          <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', fontSize: '0.7rem' }}>
            RECOMMENDED PREPARATION
          </span>
        );
      case 'OPTIONAL_RESOURCE':
        return (
          <span className="badge" style={{ background: 'rgba(148, 163, 184, 0.15)', color: '#cbd5e1', fontSize: '0.7rem' }}>
            OPTIONAL RESOURCE
          </span>
        );
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* 1. Interactive Target Post Selector Banner */}
      <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className="badge badge-demo" style={{ background: 'rgba(59, 130, 246, 0.2)', color: '#93c5fd', border: '1px solid rgba(59, 130, 246, 0.4)' }}>
                <Compass size={13} /> DYNAMIC POST-SPECIFIC ENGINE
              </span>
              <span style={{ fontSize: '0.8rem', color: '#34d399', fontWeight: 700 }}>
                • Zero Confusion Architecture
              </span>
            </div>
            <h3 style={{ fontSize: '1.45rem', fontWeight: 800, color: 'white', margin: 0 }}>
              What Exactly Should You Study for Your Target Post?
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: '4px 0 0 0' }}>
              Select your desired post below to filter out unneeded modules, isolate mandatory stages, and see your exact preparation path.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="glass-pill" style={{ fontSize: '0.78rem', color: '#86efac', borderColor: 'rgba(16, 185, 129, 0.3)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Database size={13} /> {syncStatus}
            </span>
            <button 
              onClick={handleManualSync}
              disabled={isSyncing}
              className="btn btn-secondary" 
              style={{ fontSize: '0.75rem', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '4px' }}
              title="Sync state between localStorage and SQLite database"
            >
              <RefreshCw size={12} className={isSyncing ? 'animate-spin' : ''} /> {isSyncing ? 'Syncing...' : 'Sync to SQLite'}
            </button>
          </div>
        </div>

        {/* Post Selection Pills */}
        <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '6px' }}>
          {Object.values(ALL_POST_STUDY_PATHS).map(post => {
            const isSelected = post.postId === selectedPostId;
            return (
              <button
                key={post.postId}
                onClick={() => handleSelectPost(post.postId)}
                style={{
                  padding: '10px 16px',
                  borderRadius: 'var(--radius-md)',
                  background: isSelected ? 'var(--primary)' : 'rgba(255, 255, 255, 0.04)',
                  border: isSelected ? '1px solid #60a5fa' : '1px solid var(--border-color)',
                  color: isSelected ? 'white' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '2px',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ fontSize: '0.88rem', fontWeight: 800, color: isSelected ? 'white' : '#f8fafc' }}>
                  {post.postName}
                </div>
                <div style={{ fontSize: '0.72rem', color: isSelected ? '#dbeafe' : 'var(--text-muted)' }}>
                  {post.payLevel} • {post.classification}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 2. Active Post Context Card & Stage Switcher */}
      <div className="glass-card" style={{ padding: '20px', borderLeft: '4px solid var(--primary)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
          <div>
            <div style={{ fontSize: '0.78rem', textTransform: 'uppercase', color: '#93c5fd', fontWeight: 700 }}>
              Active Post Preparation Profile:
            </div>
            <h4 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'white', margin: '2px 0' }}>
              {currentPath.postName} — {currentPath.department}
            </h4>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Cadre: <strong>{currentPath.classification}</strong> | Pay Scale: <strong>{currentPath.payLevel}</strong>
            </div>
          </div>

          {/* Stage Filter Buttons */}
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              onClick={() => setSelectedStage('ALL')}
              className={`btn ${selectedStage === 'ALL' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.82rem', padding: '6px 14px' }}
            >
              Complete Lifecycle
            </button>
            <button
              onClick={() => setSelectedStage('TIER_1')}
              className={`btn ${selectedStage === 'TIER_1' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.82rem', padding: '6px 14px' }}
            >
              Step 1: Tier 1 (Prelims)
            </button>
            <button
              onClick={() => setSelectedStage('TIER_2')}
              className={`btn ${selectedStage === 'TIER_2' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.82rem', padding: '6px 14px' }}
            >
              Step 2: Tier 2 (Mains & Skills)
            </button>
          </div>
        </div>
      </div>

      {/* 3. SECTION 1: COMMON PREPARATION (Required for all posts in this stage) */}
      {(selectedStage === 'ALL' || selectedStage === 'TIER_1') && (
        <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '0.85rem' }}>
                1
              </div>
              <div>
                <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white', margin: 0 }}>
                  STEP 1: Tier 1 Common Preparation (Preliminary Exam)
                </h4>
                <div style={{ fontSize: '0.8rem', color: '#93c5fd' }}>
                  Mandatory Computer Based Examination (100 Questions, 200 Marks, 60 Minutes duration)
                </div>
              </div>
            </div>
            <span className="badge badge-verified" style={{ fontSize: '0.75rem' }}>
              COMMON TO ALL POSTS
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '14px' }}>
            {currentPath.tier1.commonModules.map(mod => {
              const isChecked = !!completedModules[mod.id];
              return (
                <div 
                  key={mod.id}
                  style={{
                    padding: '16px',
                    borderRadius: 'var(--radius-md)',
                    background: isChecked ? 'rgba(16, 185, 129, 0.05)' : 'rgba(255, 255, 255, 0.02)',
                    border: isChecked ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--border-color)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '10px'
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      {getProvenanceBadge(mod.requirementType)}
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Clause: {mod.officialClause}
                      </span>
                    </div>

                    <h5 style={{ fontSize: '1rem', fontWeight: 700, color: 'white', margin: 0 }}>
                      {mod.title}
                    </h5>

                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      <span className="glass-pill" style={{ fontSize: '0.72rem' }}>{mod.questionsCount} Qs ({mod.marks} Marks)</span>
                      <span className="glass-pill" style={{ fontSize: '0.72rem', color: '#f87171' }}>Neg: {mod.negativeMarking}</span>
                    </div>

                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      <strong>High-Yield Core Topics:</strong> {mod.highYieldTopics.join(', ')}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '8px' }}>
                    <button
                      onClick={() => toggleModule(mod.id)}
                      className="btn"
                      style={{
                        padding: '4px 10px',
                        fontSize: '0.75rem',
                        borderRadius: 'var(--radius-sm)',
                        background: isChecked ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255,255,255,0.06)',
                        color: isChecked ? '#34d399' : 'var(--text-secondary)',
                        border: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}
                    >
                      <CheckCircle2 size={13} color={isChecked ? '#34d399' : 'gray'} />
                      {isChecked ? 'Marked Complete' : 'Mark as Studied'}
                    </button>

                    {onOpenProvenanceModal && (
                      <button
                        onClick={() => onOpenProvenanceModal(mod.provenance)}
                        className="btn btn-outline"
                        style={{ padding: '3px 8px', fontSize: '0.72rem' }}
                        title="View Gazette Clause Citation"
                      >
                        Clause Citation
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 4. SECTION 2: TIER 2 MAINS PREPARATION */}
      {(selectedStage === 'ALL' || selectedStage === 'TIER_2') && (
        <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '0.85rem' }}>
                2
              </div>
              <div>
                <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white', margin: 0 }}>
                  STEP 2: Tier 2 Paper-I Mandatory Modules (Mains Exam)
                </h4>
                <div style={{ fontSize: '0.8rem', color: '#86efac' }}>
                  Decides Final Merit (150 Questions, 390 Marks + CKT Computer & DEST Typing)
                </div>
              </div>
            </div>
            <span className="badge badge-verified" style={{ fontSize: '0.75rem' }}>
              MERIT DECIDING STAGE
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '14px' }}>
            {currentPath.tier2.commonModules.map(mod => {
              const isChecked = !!completedModules[mod.id];
              return (
                <div 
                  key={mod.id}
                  style={{
                    padding: '16px',
                    borderRadius: 'var(--radius-md)',
                    background: isChecked ? 'rgba(16, 185, 129, 0.05)' : 'rgba(255, 255, 255, 0.02)',
                    border: isChecked ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--border-color)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '10px'
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      {getProvenanceBadge(mod.requirementType)}
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Clause: {mod.officialClause}
                      </span>
                    </div>

                    <h5 style={{ fontSize: '1rem', fontWeight: 700, color: 'white', margin: 0 }}>
                      {mod.title}
                    </h5>

                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                      <span className="glass-pill" style={{ fontSize: '0.72rem' }}>{mod.questionsCount} Qs ({mod.marks} Marks)</span>
                      <span className="glass-pill" style={{ fontSize: '0.72rem', color: '#f87171' }}>Neg: {mod.negativeMarking}</span>
                    </div>

                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      <strong>High-Yield Core Topics:</strong> {mod.highYieldTopics.join(', ')}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '8px' }}>
                    <button
                      onClick={() => toggleModule(mod.id)}
                      className="btn"
                      style={{
                        padding: '4px 10px',
                        fontSize: '0.75rem',
                        borderRadius: 'var(--radius-sm)',
                        background: isChecked ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255,255,255,0.06)',
                        color: isChecked ? '#34d399' : 'var(--text-secondary)',
                        border: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}
                    >
                      <CheckCircle2 size={13} color={isChecked ? '#34d399' : 'gray'} />
                      {isChecked ? 'Marked Complete' : 'Mark as Studied'}
                    </button>

                    {onOpenProvenanceModal && (
                      <button
                        onClick={() => onOpenProvenanceModal(mod.provenance)}
                        className="btn btn-outline"
                        style={{ padding: '3px 8px', fontSize: '0.72rem' }}
                      >
                        Clause Citation
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 5. SECTION 3: POST-SPECIFIC ADDITIONAL REQUIREMENTS (If Any) */}
      {currentPath.tier2.additionalModules.length > 0 && (
        <div className="glass-card" style={{ padding: '24px', border: '1px solid rgba(234, 179, 8, 0.4)', background: 'rgba(234, 179, 8, 0.03)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: 'rgba(234, 179, 8, 0.2)', color: '#fbbf24', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '0.85rem' }}>
                ⭐
              </div>
              <div>
                <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#fde047', margin: 0 }}>
                  Additional Mandatory Preparation for {currentPath.postName}
                </h4>
                <div style={{ fontSize: '0.8rem', color: '#fef08a' }}>
                  This paper is strictly required for this post in addition to Paper-I
                </div>
              </div>
            </div>
            <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.2)', color: '#fde047' }}>
              POST-SPECIFIC MANDATE
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '14px' }}>
            {currentPath.tier2.additionalModules.map(mod => (
              <div key={mod.id} style={{ padding: '18px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(234, 179, 8, 0.3)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span className="badge badge-verified">{mod.officialClause}</span>
                  <span style={{ fontSize: '0.8rem', color: '#fbbf24', fontWeight: 700 }}>100 Questions • 200 Marks • Negative: -0.50</span>
                </div>
                <h4 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'white', margin: '4px 0' }}>{mod.title}</h4>
                <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', margin: '6px 0 10px 0', lineHeight: 1.5 }}>
                  <strong>Mandatory Topics:</strong> {mod.highYieldTopics.join(', ')}
                </p>
                <div style={{ padding: '10px 14px', borderRadius: 'var(--radius-sm)', background: 'rgba(234, 179, 8, 0.1)', fontSize: '0.82rem', color: '#fef08a' }}>
                  💡 <strong>Preparation Strategy:</strong> {mod.keyTakeaways}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 6. Physical & Medical Standards for Field/Inspector Posts */}
      {currentPath.physicalMedical?.required && (
        <div className="glass-card" style={{ padding: '20px', border: '1px solid rgba(59, 130, 246, 0.4)', background: 'rgba(59, 130, 246, 0.04)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#93c5fd', fontWeight: 800, marginBottom: '10px' }}>
            <Activity size={18} color="#60a5fa" /> Mandatory Physical & Medical Standards for {currentPath.postName}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
            {currentPath.physicalMedical.maleHeightChest && (
              <div style={{ padding: '12px', borderRadius: 'var(--radius-sm)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', fontSize: '0.84rem' }}>
                <strong style={{ color: 'white' }}>Male Measurement Standards:</strong>
                <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>{currentPath.physicalMedical.maleHeightChest}</p>
              </div>
            )}
            {currentPath.physicalMedical.physicalTest && (
              <div style={{ padding: '12px', borderRadius: 'var(--radius-sm)', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', fontSize: '0.84rem' }}>
                <strong style={{ color: 'white' }}>Physical Efficiency Test (PET):</strong>
                <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>{currentPath.physicalMedical.physicalTest}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 7. SECTION 4: 🚫 YOU DON'T NEED TO STUDY (Eliminate Confusion) */}
      <div className="glass-card" style={{ padding: '24px', border: '1px solid rgba(239, 68, 68, 0.3)', background: 'rgba(239, 68, 68, 0.03)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
          <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '0.85rem' }}>
            🚫
          </div>
          <div>
            <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#fca5a5', margin: 0 }}>
              YOU DON'T NEED TO STUDY (Not Required for {currentPath.postName})
            </h4>
            <div style={{ fontSize: '0.8rem', color: '#fecaca' }}>
              Eliminating these unneeded subjects saves you over 100+ hours of wasted preparation time.
            </div>
          </div>
        </div>

        {currentPath.tier2.excludedModules.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '12px' }}>
            {currentPath.tier2.excludedModules.map(ex => (
              <div key={ex.moduleId} style={{ padding: '16px', borderRadius: 'var(--radius-md)', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(239, 68, 68, 0.2)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f87171', fontWeight: 700, fontSize: '0.95rem' }}>
                  <XCircle size={16} /> {ex.moduleName}
                </div>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
                  {ex.reason}
                </p>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Applicable Only To: <span style={{ color: '#93c5fd' }}>{ex.applicableOnlyTo}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-sm)', background: 'rgba(255,255,255,0.02)', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            All standard Paper-I and Paper-II modules are required for Junior Statistical Officer (JSO).
          </div>
        )}
      </div>

    </div>
  );
};
