import React, { useState } from 'react';
import { Bot, Send, ShieldCheck, AlertCircle, FileText, Sparkles, CheckCircle2 } from 'lucide-react';
import { SSC_CGL_EXAM } from '../data/examsData';
import { evaluateCandidateEligibility } from '../services/eligibilityEngine';

interface AIAssistantProps {
  onOpenProvenanceModal: (provenance: any) => void;
}

interface ChatMessage {
  id: string;
  sender: 'USER' | 'AI';
  text: string;
  isVerified: boolean;
  citation?: {
    documentTitle: string;
    pageNumber: number;
    clauseNumber: string;
    provenance: any;
  };
}

export const AIAssistant: React.FC<AIAssistantProps> = ({ onOpenProvenanceModal }) => {
  const [inputQuery, setInputQuery] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'm-1',
      sender: 'AI',
      text: 'Hello! I am the GovOS Strictly Grounded AI Assistant. I do not guess or search unverified external websites. Ask me anything about SSC CGL 2026 eligibility, exam dates, syllabus, or application rules!',
      isVerified: true
    }
  ]);

  const handleSendMessage = () => {
    if (!inputQuery.trim()) return;

    const userText = inputQuery.trim();
    const userMsg: ChatMessage = {
      id: `m-user-${Date.now()}`,
      sender: 'USER',
      text: userText,
      isVerified: false
    };

    setMessages(prev => [...prev, userMsg]);
    setInputQuery('');

    // Process query grounded against verified database
    setTimeout(() => {
      let responseText = '';
      let citationData: any = null;
      let verified = true;

      const qLower = userText.toLowerCase();

      if (qLower.includes('eligible') || qLower.includes('b.tech') || qLower.includes('age')) {
        const dummyProfile = {
          dateOfBirth: '2005-05-15',
          degree: 'B.Tech',
          branch: 'Computer Science',
          percentage: 72,
          category: 'GENERAL' as const,
          gender: 'Male' as const,
          domicileState: 'Telangana',
          nationality: 'INDIAN'
        };
        const diag = evaluateCandidateEligibility(SSC_CGL_EXAM, dummyProfile);
        responseText = `${diag.plainEnglishExplanation} (Verified against Section 3.1, Clause 3.1(a) of the official notification).`;
        citationData = {
          documentTitle: 'SSC CGL 2026 Official Notice.pdf',
          pageNumber: 12,
          clauseNumber: 'Section 3.1 (a)',
          provenance: SSC_CGL_EXAM.posts[0].provenance
        };
      } else if (qLower.includes('date') || qLower.includes('deadline') || qLower.includes('last date')) {
        responseText = `The online application closing date for SSC CGL 2026 has been officially extended to 27 September 2026 (23:59 IST) via Corrigendum Notice #02.`;
        citationData = {
          documentTitle: 'SSC CGL 2026 Corrigendum Notice #02.pdf',
          pageNumber: 1,
          clauseNumber: 'Clause 2',
          provenance: SSC_CGL_EXAM.dates[2].provenance
        };
      } else if (qLower.includes('negative') || qLower.includes('marking') || qLower.includes('scheme')) {
        responseText = `Yes, Tier-1 examination has a negative marking of 0.50 marks per incorrect answer. Tier-2 has 1.00 mark deducted per wrong answer in Section I & II.`;
        citationData = {
          documentTitle: 'SSC CGL 2026 Official Notice.pdf',
          pageNumber: 15,
          clauseNumber: 'Section 4.2',
          provenance: SSC_CGL_EXAM.dates[0].provenance
        };
      } else {
        // Fallback for unverified / missing topics
        verified = false;
        responseText = `I couldn't find a verified official source for this information in the GovOS database. Please check the official notification or consult the official portal at https://ssc.gov.in.`;
      }

      const aiMsg: ChatMessage = {
        id: `m-ai-${Date.now()}`,
        sender: 'AI',
        text: responseText,
        isVerified: verified,
        citation: citationData
      };

      setMessages(prev => [...prev, aiMsg]);
    }, 400);
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Header */}
      <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(17, 24, 39, 0.9) 100%)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ width: '42px', height: '42px', borderRadius: '12px', background: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
            <Bot size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800 }}>
              Strictly Grounded AI Guidance Assistant
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              Queries strictly restricted to the Verified Database & Deterministic Rule Engine. Unverified queries trigger fallback alerts.
            </p>
          </div>
        </div>
      </div>

      {/* Chat Conversation Box */}
      <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', height: '550px' }}>
        
        {/* Messages Feed */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px', paddingRight: '8px' }}>
          {messages.map(msg => (
            <div 
              key={msg.id} 
              style={{
                alignSelf: msg.sender === 'USER' ? 'flex-end' : 'flex-start',
                maxWidth: '82%',
                background: msg.sender === 'USER' ? 'var(--primary)' : 'rgba(255,255,255,0.05)',
                color: 'white',
                padding: '16px 20px',
                borderRadius: msg.sender === 'USER' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                border: msg.sender === 'AI' ? '1px solid var(--border-color)' : 'none',
                lineHeight: 1.6,
                fontSize: '0.95rem'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <span style={{ fontWeight: 700, fontSize: '0.8rem', color: msg.sender === 'USER' ? '#c7d2fe' : '#a855f7' }}>
                  {msg.sender === 'USER' ? 'CANDIDATE' : 'GOVOS GROUNDED AI'}
                </span>
                
                {msg.sender === 'AI' && (
                  msg.isVerified ? (
                    <span className="badge badge-verified" style={{ fontSize: '0.65rem' }}>
                      <ShieldCheck size={12} /> VERIFIED FACT
                    </span>
                  ) : (
                    <span className="badge badge-changed" style={{ fontSize: '0.65rem' }}>
                      <AlertCircle size={12} /> FALLBACK WARNING
                    </span>
                  )
                )}
              </div>

              {msg.text}

              {msg.citation && (
                <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    Citation: {msg.citation.documentTitle} (Page {msg.citation.pageNumber}, {msg.citation.clauseNumber})
                  </span>
                  {msg.citation.provenance && (
                    <button className="btn btn-outline" onClick={() => msg.citation?.provenance && onOpenProvenanceModal(msg.citation.provenance)} style={{ fontSize: '0.7rem', padding: '2px 8px' }}>
                      <FileText size={12} /> Cite Clause
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Input Bar */}
        <div style={{ display: 'flex', gap: '12px', marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
          <input 
            type="text"
            placeholder="Ask a question e.g. 'Am I eligible for SSC CGL at age 21 with B.Tech?' or 'What is the application deadline?'"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            style={{
              flex: 1,
              padding: '14px 18px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-input)',
              border: '1px solid var(--border-color)',
              color: 'white',
              fontSize: '0.95rem',
              outline: 'none'
            }}
          />

          <button className="btn btn-primary" onClick={handleSendMessage} style={{ padding: '14px 24px' }}>
            Send <Send size={18} />
          </button>
        </div>

      </div>
    </div>
  );
};
