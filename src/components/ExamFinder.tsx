import React, { useState } from 'react';
import { Search, Compass, ShieldCheck, ChevronRight, Award, ArrowUpRight, Sparkles, Filter } from 'lucide-react';
import { ALL_EXAMS } from '../data/examsData';
import { Exam } from '../types/exam';

interface ExamFinderProps {
  onSelectExam: (exam: Exam) => void;
  onNavigateEligibility: () => void;
}

export const ExamFinder: React.FC<ExamFinderProps> = ({ onSelectExam, onNavigateEligibility }) => {
  const [selectedPersona, setSelectedPersona] = useState<string>('Graduation (Any Stream)');
  const [selectedInterest, setSelectedInterest] = useState<string>('Government Job');
  const [ageInput, setAgeInput] = useState<number>(21);
  const [searchQuery, setSearchQuery] = useState<string>('');

  const personas = [
    'Class 10th Pass',
    'Class 12th (MPC / Science)',
    'Class 12th (Commerce / Arts)',
    'Graduation (Any Stream)',
    'B.Tech / B.E (Engineering)',
    'Postgraduate / Master\'s'
  ];

  const interests = [
    'Government Job',
    'Civil Services & Governance',
    'Banking & Financial Sector',
    'Indian Railways',
    'Defence & Armed Forces',
    'State Public Services'
  ];

  const filteredExams = ALL_EXAMS.filter(exam => {
    const matchesSearch = exam.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          exam.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          exam.authorityName.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* Hero Banner */}
      <div className="glass-card" style={{ padding: '36px', background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.9) 0%, rgba(30, 27, 75, 0.6) 100%)', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: '-50px', right: '-50px', width: '250px', height: '250px', background: 'radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%)', borderRadius: '50%' }} />
        
        <div style={{ maxWidth: '780px', position: 'relative', zIndex: 2 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '6px 14px', borderRadius: '999px', background: 'rgba(99, 102, 241, 0.15)', border: '1px solid rgba(99, 102, 241, 0.3)', marginBottom: '16px' }}>
            <Sparkles size={16} color="#818cf8" />
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#a5b4fc', letterSpacing: '0.02em' }}>
              ONE PLATFORM. EVERY EXAM. ONE CLEAR PATH.
            </span>
          </div>

          <h2 style={{ fontSize: '2.2rem', fontWeight: 800, lineHeight: 1.2, marginBottom: '14px', letterSpacing: '-0.02em' }}>
            Discover Government & Entrance Exams Matched to Your Goal
          </h2>
          
          <p style={{ color: 'var(--text-secondary)', fontSize: '1.05rem', marginBottom: '24px', lineHeight: 1.6 }}>
            Never ask <strong style={{ color: 'white' }}>"What do I do next?"</strong> again. GovOS converts fragmented official government notifications into verified, version-controlled, personalized exam roadmaps.
          </p>

          <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={onNavigateEligibility} style={{ padding: '12px 24px', fontSize: '1rem' }}>
              <ShieldCheck size={20} /> Check My Eligibility Now
            </button>
            
            <button className="btn btn-emerald" onClick={() => onSelectExam(ALL_EXAMS[0])} style={{ padding: '12px 24px', fontSize: '1rem' }}>
              <Award size={20} /> Explore Golden Journey (SSC CGL)
            </button>
          </div>
        </div>
      </div>

      {/* Discovery Filter Engine: "I am a..." + "What do you want?" */}
      <div className="glass-card" style={{ padding: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <Filter size={22} color="var(--primary)" />
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Career & Exam Discovery Engine</h3>
        </div>

        <div className="grid-3" style={{ marginBottom: '24px' }}>
          {/* Step 1: Persona */}
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              1. I am a... (Qualification)
            </label>
            <select 
              value={selectedPersona} 
              onChange={(e) => setSelectedPersona(e.target.value)}
              style={{
                width: '100%',
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-color)',
                color: 'white',
                fontSize: '0.95rem',
                fontFamily: 'var(--font-sans)',
                outline: 'none'
              }}
            >
              {personas.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>

          {/* Step 2: Goal */}
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              2. What do you want? (Field)
            </label>
            <select 
              value={selectedInterest} 
              onChange={(e) => setSelectedInterest(e.target.value)}
              style={{
                width: '100%',
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-color)',
                color: 'white',
                fontSize: '0.95rem',
                fontFamily: 'var(--font-sans)',
                outline: 'none'
              }}
            >
              {interests.map(i => <option key={i} value={i}>{i}</option>)}
            </select>
          </div>

          {/* Step 3: Age */}
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              3. Current Age (Years)
            </label>
            <input 
              type="number"
              value={ageInput}
              onChange={(e) => setAgeInput(Number(e.target.value))}
              min={15}
              max={60}
              style={{
                width: '100%',
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-color)',
                color: 'white',
                fontSize: '0.95rem',
                fontFamily: 'var(--font-sans)',
                outline: 'none'
              }}
            />
          </div>
        </div>

        {/* Search Bar */}
        <div style={{ position: 'relative' }}>
          <Search size={20} color="var(--text-muted)" style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)' }} />
          <input 
            type="text"
            placeholder="Search exam name or authority e.g. SSC CGL, UPSC, IBPS..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '14px 16px 14px 48px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-input)',
              border: '1px solid var(--border-color)',
              color: 'white',
              fontSize: '1rem',
              outline: 'none'
            }}
          />
        </div>
      </div>

      {/* Featured Exams Cards */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '1.3rem', fontWeight: 700 }}>
            Available Examinations ({filteredExams.length})
          </h3>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Showing verified active recruitment cycles
          </span>
        </div>

        <div className="grid-2">
          {filteredExams.map(exam => (
            <div key={exam.id} className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', borderLeft: exam.isGoldenJourney ? '4px solid var(--emerald)' : '1px solid var(--border-color)' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', gap: '8px' }}>
                  <span className="badge badge-verified">
                    <ShieldCheck size={14} /> OFFICIALLY VERIFIED
                  </span>
                  {exam.isGoldenJourney && (
                    <span className="badge badge-demo" style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.4)' }}>
                      🌟 GOLDEN JOURNEY DEMO
                    </span>
                  )}
                  {exam.isDemoData && !exam.isGoldenJourney && (
                    <span className="badge badge-demo">
                      PROTOTYPE DEMO DATA
                    </span>
                  )}
                </div>

                <h4 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '6px' }}>
                  {exam.title}
                </h4>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '14px', fontWeight: 500 }}>
                  Authority: {exam.authorityName}
                </p>

                <p style={{ fontSize: '0.9rem', color: '#d1d5db', lineHeight: 1.5, marginBottom: '18px' }}>
                  {exam.overviewDescription.slice(0, 140)}...
                </p>

                {/* Key attributes pill grid */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '20px' }}>
                  <span className="glass-pill">
                    🎯 Age: 18 - 27 Yrs (Base)
                  </span>
                  <span className="glass-pill">
                    🎓 Graduation
                  </span>
                  <span className="glass-pill" style={{ borderColor: 'rgba(16, 185, 129, 0.3)', color: '#34d399' }}>
                    💰 Pay Level 4 to 8
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Cycle Code: <code style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{exam.code}</code>
                </span>

                <button 
                  className={`btn ${exam.isGoldenJourney ? 'btn-emerald' : 'btn-primary'}`}
                  onClick={() => onSelectExam(exam)}
                  style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                >
                  Explore 14-Section Guide <ChevronRight size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
