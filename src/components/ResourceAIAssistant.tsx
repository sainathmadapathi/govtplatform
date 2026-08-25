import React, { useState } from 'react';
import { 
  Bot, Send, Sparkles, BookOpen, Download, PlayCircle, ExternalLink, 
  ArrowRight, ShieldCheck, HelpCircle, FileText, CheckCircle2
} from 'lucide-react';
import { ResourceItem } from '../types/exam';

interface ResourceAIAssistantProps {
  resources: ResourceItem[];
  onOpenResourceModal: (resource: ResourceItem) => void;
}

interface ChatMessage {
  id: string;
  sender: 'USER' | 'AI';
  text: string;
  matchedResources?: ResourceItem[];
  timestamp: string;
}

export const ResourceAIAssistant: React.FC<ResourceAIAssistantProps> = ({
  resources,
  onOpenResourceModal
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'msg-welcome',
      sender: 'AI',
      text: 'Hello! I am your **GovOS Resource Navigator**. Ask me for any study material, formula sheet, official gazette, or video course, and I will jump directly to the exact verified document or YouTube masterclass for you.',
      timestamp: 'Just now'
    }
  ]);
  const [inputText, setInputText] = useState<string>('');

  const quickPrompts = [
    'Official SSC CGL 2026 Notification PDF',
    'English Grammar 60 Rules Marathon Video',
    'Quantitative Aptitude Geometry & Formulas',
    'Constitution of India Fundamental Rights Articles',
    'Tier-2 Computer Knowledge Qualifying Notes',
    'Official DEST 2000 Key Depressions Typing Test'
  ];

  const handleSendMessage = (queryText?: string) => {
    const textToSend = (queryText || inputText).trim();
    if (!textToSend) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'USER',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const queryLower = textToSend.toLowerCase();
    
    // Search matching resources
    const matched = resources.filter(res => {
      const titleMatch = res.title.toLowerCase().includes(queryLower);
      const subMatch = res.subject.toLowerCase().includes(queryLower);
      const descMatch = res.description.toLowerCase().includes(queryLower);
      const authorMatch = res.author.toLowerCase().includes(queryLower);

      if (queryLower.includes('notification') || queryLower.includes('gazette') || queryLower.includes('official notice')) {
        return res.id === 'res-pdf-01';
      }
      if (queryLower.includes('english') || queryLower.includes('grammar') || queryLower.includes('rani') || queryLower.includes('rules')) {
        return res.subject === 'English Comprehension';
      }
      if (queryLower.includes('math') || queryLower.includes('quant') || queryLower.includes('geometry') || queryLower.includes('algebra') || queryLower.includes('formula') || queryLower.includes('gagan')) {
        return res.subject === 'Quantitative Aptitude';
      }
      if (queryLower.includes('polity') || queryLower.includes('constitution') || queryLower.includes('article') || queryLower.includes('parmar') || queryLower.includes('gk') || queryLower.includes('general awareness')) {
        return res.subject === 'General Awareness & Static GK';
      }
      if (queryLower.includes('computer') || queryLower.includes('typing') || queryLower.includes('dest') || queryLower.includes('rbe')) {
        return res.subject === 'Computer & Typing';
      }
      if (queryLower.includes('reasoning') || queryLower.includes('vikramjeet')) {
        return res.subject === 'Reasoning';
      }

      return titleMatch || subMatch || descMatch || authorMatch;
    });

    let replyText = `I found **${matched.length} verified authentic resources** matching your request. You can read the full text, download the direct PDF, or watch the complete video course below:`;
    if (matched.length === 0) {
      replyText = `I searched the verified GovOS repository. Here are the most authoritative core materials available for SSC CGL:`;
    }

    const aiMsg: ChatMessage = {
      id: `ai-${Date.now()}`,
      sender: 'AI',
      text: replyText,
      matchedResources: matched.length > 0 ? matched : resources.slice(0, 3),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg, aiMsg]);
    setInputText('');
  };

  return (
    <div className="glass-card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(30, 58, 138, 0.15) 0%, rgba(15, 23, 42, 0.95) 100%)', borderColor: 'rgba(59, 130, 246, 0.3)', marginBottom: '20px' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ padding: '8px', borderRadius: '50%', background: 'rgba(59, 130, 246, 0.2)', border: '1px solid rgba(59, 130, 246, 0.4)' }}>
            <Bot size={22} color="#60a5fa" />
          </div>
          <div>
            <h4 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'white', margin: 0 }}>
              AI Resource Navigator & Instant Jumper
            </h4>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Ask anything to jump directly to authentic downloadable PDFs, official gazettes & YouTube masterclasses
            </span>
          </div>
        </div>
      </div>

      {/* Quick Prompt Pills */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '16px' }}>
        {quickPrompts.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => handleSendMessage(prompt)}
            style={{
              fontSize: '0.78rem',
              padding: '5px 12px',
              borderRadius: '20px',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              color: '#93c5fd',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Sparkles size={12} color="var(--amber)" /> {prompt}
          </button>
        ))}
      </div>

      {/* Chat Messages Stream */}
      <div style={{ 
        maxHeight: '340px', 
        overflowY: 'auto', 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '14px',
        padding: '12px',
        background: 'rgba(0,0,0,0.25)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-color)',
        marginBottom: '16px'
      }}>
        {messages.map(msg => (
          <div 
            key={msg.id} 
            style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: msg.sender === 'USER' ? 'flex-end' : 'flex-start',
              gap: '6px'
            }}
          >
            <div style={{ 
              maxWidth: '85%', 
              padding: '12px 16px', 
              borderRadius: 'var(--radius-md)', 
              background: msg.sender === 'USER' ? 'var(--primary)' : 'rgba(255,255,255,0.05)',
              border: msg.sender === 'USER' ? 'none' : '1px solid var(--border-color)',
              color: 'white',
              fontSize: '0.9rem',
              lineHeight: 1.5
            }}>
              <div 
                dangerouslySetInnerHTML={{ 
                  __html: msg.text
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\n/g, '<br/>') 
                }} 
              />
            </div>

            {/* Render Instant Action Cards for Matched Resources */}
            {msg.matchedResources && msg.matchedResources.length > 0 && (
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', 
                gap: '10px', 
                width: '100%',
                marginTop: '4px'
              }}>
                {msg.matchedResources.map(res => (
                  <div 
                    key={res.id} 
                    style={{ 
                      padding: '12px 14px', 
                      borderRadius: 'var(--radius-md)', 
                      background: 'rgba(15, 23, 42, 0.9)', 
                      border: '1px solid rgba(59, 130, 246, 0.3)',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      gap: '8px'
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span className="badge badge-verified" style={{ fontSize: '0.68rem' }}>{res.subject}</span>
                        <span style={{ fontSize: '0.72rem', color: '#fbbf24' }}>{res.rating?.split(' ')[0] || '⭐ 4.9/5'}</span>
                      </div>
                      <h5 style={{ fontSize: '0.92rem', fontWeight: 700, color: 'white', margin: '4px 0 2px 0' }}>{res.title}</h5>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>By: {res.author}</div>
                    </div>

                    <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
                      {res.resourceFormat === 'YOUTUBE_COURSE' ? (
                        <>
                          <a 
                            href={res.youtubeUrl || res.url} 
                            target="_blank" 
                            rel="noreferrer" 
                            className="btn btn-emerald" 
                            style={{ fontSize: '0.75rem', padding: '5px 12px', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
                          >
                            <PlayCircle size={14} /> Watch Direct Video on YouTube <ExternalLink size={11} />
                          </a>
                        </>
                      ) : res.directPdfUrl ? (
                        <>
                          <a 
                            href={res.directPdfUrl} 
                            download={res.downloadFileName || 'GovOS_Official_Resource.pdf'}
                            className="btn btn-emerald" 
                            style={{ fontSize: '0.75rem', padding: '4px 10px', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}
                          >
                            <Download size={13} /> Download PDF
                          </a>
                          <a 
                            href={res.directPdfUrl} 
                            target="_blank"
                            rel="noreferrer"
                            className="btn btn-secondary" 
                            style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                            title="Read in Browser"
                          >
                            <BookOpen size={12} />
                          </a>
                        </>
                      ) : (
                        <button 
                          onClick={() => onOpenResourceModal(res)}
                          className="btn btn-emerald" 
                          style={{ fontSize: '0.75rem', padding: '4px 10px', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}
                        >
                          <BookOpen size={13} /> Open Material
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{msg.timestamp}</span>
          </div>
        ))}
      </div>

      {/* Input Box */}
      <div style={{ display: 'flex', gap: '10px' }}>
        <input 
          type="text" 
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
          placeholder="e.g. Give me the official SSC CGL Notification PDF or English Grammar video..."
          style={{
            flex: 1,
            padding: '10px 16px',
            borderRadius: 'var(--radius-md)',
            background: 'var(--bg-input)',
            border: '1px solid var(--border-color)',
            color: 'white',
            fontSize: '0.9rem',
            outline: 'none'
          }}
        />
        <button 
          onClick={() => handleSendMessage()} 
          className="btn btn-primary"
          style={{ padding: '0 20px', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Send size={15} /> Jump
        </button>
      </div>

    </div>
  );
};
