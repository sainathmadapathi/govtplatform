import React, { useState } from 'react';
import { 
  X, Download, ExternalLink, PlayCircle, BookOpen, CheckCircle2, 
  FileText, ArrowLeft, ArrowRight, Printer, Share2, Sparkles, Youtube, Eye
} from 'lucide-react';
import { ResourceItem, InAppChapter } from '../types/exam';

interface ResourceReaderModalProps {
  resource: ResourceItem | null;
  onClose: () => void;
}

export const ResourceReaderModal: React.FC<ResourceReaderModalProps> = ({
  resource,
  onClose
}) => {
  const [activeChapterIndex, setActiveChapterIndex] = useState<number>(0);
  const [viewMode, setViewMode] = useState<'PDF_VIEW' | 'CHAPTERS'>('CHAPTERS');

  if (!resource) return null;

  const chapters: InAppChapter[] = resource.inAppHandbookContent?.chapters || [
    {
      chapterTitle: 'Overview & Essential Sourced Notes',
      contentMarkdown: resource.description
    }
  ];

  const currentChapter = chapters[activeChapterIndex] || chapters[0];

  const handlePrintOrDownload = () => {
    // Generate clean printable window for instant direct PDF save
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(`
        <!DOCTYPE html>
        <html>
          <head>
            <title>${resource.title} - GovOS Official Study Material</title>
            <style>
              body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #111827;
                padding: 40px;
                max-width: 900px;
                margin: 0 auto;
              }
              h1 { color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; }
              h2 { color: #1e40af; margin-top: 24px; }
              h3 { color: #1f2937; }
              .meta-box { background: #f3f4f6; border-left: 4px solid #10b981; padding: 12px 16px; margin-bottom: 24px; }
              table { width: 100%; border-collapse: collapse; margin: 16px 0; }
              th, td { border: 1px solid #d1d5db; padding: 8px 12px; text-align: left; }
              th { background: #f9fafb; font-weight: bold; }
              code { background: #e5e7eb; padding: 2px 6px; border-radius: 4px; font-family: monospace; }
              pre { background: #f3f4f6; padding: 12px; border-radius: 6px; overflow-x: auto; }
              ul { padding-left: 20px; }
              li { margin-bottom: 6px; }
              @media print {
                body { padding: 0; }
                .no-print { display: none; }
              }
            </style>
          </head>
          <body>
            <div class="meta-box">
              <div style="font-size: 12px; text-transform: uppercase; color: #6b7280; font-weight: bold;">
                GovOS 100% Authoritative Sourced Study Material
              </div>
              <h1 style="margin: 8px 0;">${resource.title}</h1>
              <div><strong>Subject / Module:</strong> ${resource.subject} | <strong>Source / Author:</strong> ${resource.author}</div>
              <div><strong>Rating:</strong> ${resource.rating}</div>
            </div>

            <div>
              ${chapters.map((ch, idx) => `
                <div style="margin-bottom: 30px; page-break-inside: avoid;">
                  <h2>Chapter ${idx + 1}: ${ch.chapterTitle}</h2>
                  <div>${ch.contentMarkdown.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code>$1</code>')}</div>
                </div>
              `).join('')}
            </div>

            <div style="margin-top: 40px; border-top: 1px solid #d1d5db; padding-top: 12px; font-size: 11px; color: #9ca3af; text-align: center;">
              Downloaded from GovOS — Complete Candidate Lifecycle Platform.
            </div>
            <script>
              window.onload = function() {
                window.print();
              };
            </script>
          </body>
        </html>
      `);
      printWindow.document.close();
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(5, 10, 24, 0.88)',
      backdropFilter: 'blur(10px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div 
        className="glass-card"
        style={{
          width: '100%',
          maxWidth: '1100px',
          height: '92vh',
          display: 'flex',
          flexDirection: 'column',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.8)',
          background: 'var(--bg-card)'
        }}
      >
        {/* Header */}
        <div style={{
          padding: '16px 24px',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(15, 23, 42, 0.95)',
          gap: '16px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', overflow: 'hidden' }}>
            <div style={{
              padding: '8px',
              borderRadius: 'var(--radius-sm)',
              background: resource.resourceFormat === 'YOUTUBE_COURSE' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(59, 130, 246, 0.15)',
              color: resource.resourceFormat === 'YOUTUBE_COURSE' ? '#ef4444' : 'var(--primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              {resource.resourceFormat === 'YOUTUBE_COURSE' ? <PlayCircle size={24} /> : <FileText size={24} />}
            </div>
            <div style={{ overflow: 'hidden' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <span className="badge badge-verified" style={{ fontSize: '0.72rem' }}>
                  {resource.subject}
                </span>
                {resource.officialTag && (
                  <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', fontSize: '0.72rem' }}>
                    {resource.officialTag}
                  </span>
                )}
              </div>
              <h3 style={{ 
                fontSize: '1.15rem', 
                fontWeight: 800, 
                color: 'white', 
                margin: '2px 0 0 0',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {resource.title}
              </h3>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            {/* View Mode Toggle if direct PDF is available */}
            {resource.directPdfUrl && (
              <div style={{ display: 'flex', background: 'rgba(255,255,255,0.06)', borderRadius: 'var(--radius-md)', padding: '2px' }}>
                <button
                  onClick={() => setViewMode('PDF_VIEW')}
                  style={{
                    padding: '5px 10px',
                    fontSize: '0.78rem',
                    borderRadius: 'var(--radius-sm)',
                    border: 'none',
                    background: viewMode === 'PDF_VIEW' ? 'var(--primary)' : 'transparent',
                    color: 'white',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <Eye size={13} /> Original PDF
                </button>
                <button
                  onClick={() => setViewMode('CHAPTERS')}
                  style={{
                    padding: '5px 10px',
                    fontSize: '0.78rem',
                    borderRadius: 'var(--radius-sm)',
                    border: 'none',
                    background: viewMode === 'CHAPTERS' ? 'var(--primary)' : 'transparent',
                    color: 'white',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <BookOpen size={13} /> Structured Notes
                </button>
              </div>
            )}

            {/* Direct Download Button */}
            {resource.directPdfUrl ? (
              <a 
                href={resource.directPdfUrl} 
                download={resource.downloadFileName || 'GovOS_Official_Resource.pdf'}
                className="btn btn-emerald" 
                style={{ fontSize: '0.8rem', padding: '6px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
                title="Download genuine official PDF directly"
              >
                <Download size={14} /> Download PDF
              </a>
            ) : (
              <button 
                onClick={handlePrintOrDownload} 
                className="btn btn-emerald" 
                style={{ fontSize: '0.8rem', padding: '6px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
                title="Print or Save as PDF directly"
              >
                <Download size={14} /> Save / Print PDF
              </button>
            )}

            <a 
              href={resource.directPdfUrl || resource.youtubeUrl || resource.url} 
              target="_blank" 
              rel="noreferrer" 
              className="btn btn-outline" 
              style={{ fontSize: '0.8rem', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              Open Direct <ExternalLink size={14} />
            </a>

            <button 
              onClick={onClose}
              style={{ 
                background: 'rgba(255, 255, 255, 0.05)', 
                border: 'none', 
                color: 'var(--text-muted)', 
                cursor: 'pointer',
                borderRadius: '50%',
                padding: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          
          {/* 1. YOUTUBE COURSE EMBED & DIRECT VIDEO PLAYER */}
          {resource.resourceFormat === 'YOUTUBE_COURSE' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', padding: '24px' }}>
              
              {/* Native YouTube Video Player */}
              <div style={{ 
                position: 'relative', 
                paddingBottom: '56.25%', 
                height: 0, 
                overflow: 'hidden', 
                borderRadius: 'var(--radius-md)', 
                background: '#000',
                border: '1px solid var(--border-color)',
                boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
              }}>
                <iframe
                  src={`https://www.youtube-nocookie.com/embed/${resource.youtubeEmbedId || '6OW1mJTLms0'}?rel=0&autoplay=1`}
                  title={resource.title}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    border: 'none'
                  }}
                />
              </div>

              {/* Direct Video Launch Bar & Details */}
              <div style={{ 
                padding: '20px 24px', 
                borderRadius: 'var(--radius-md)', 
                background: 'rgba(255,255,255,0.02)', 
                border: '1px solid var(--border-color)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '16px'
              }}>
                <div style={{ flex: 1, minWidth: '280px' }}>
                  <span className="badge" style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5', fontSize: '0.75rem', marginBottom: '6px' }}>
                    {resource.officialTag || 'VERIFIED DIRECT VIDEO'}
                  </span>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'white', margin: '4px 0' }}>
                    {resource.title}
                  </h3>
                  <div style={{ fontSize: '0.85rem', color: '#93c5fd' }}>
                    Educator: <strong>{resource.author}</strong> • {resource.rating}
                  </div>
                </div>

                <a
                  href={resource.youtubeUrl || resource.url}
                  target="_blank"
                  rel="noreferrer"
                  className="btn"
                  style={{
                    background: '#ef4444',
                    color: 'white',
                    fontWeight: 700,
                    fontSize: '0.92rem',
                    padding: '10px 20px',
                    borderRadius: 'var(--radius-md)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    boxShadow: '0 8px 20px -4px rgba(239, 68, 68, 0.4)'
                  }}
                >
                  <PlayCircle size={18} /> Open Direct Video on YouTube <ExternalLink size={14} />
                </a>
              </div>

              {/* Study Tips Box */}
              <div style={{ 
                padding: '16px 20px', 
                borderRadius: 'var(--radius-md)', 
                background: 'rgba(16, 185, 129, 0.08)', 
                border: '1px solid rgba(16, 185, 129, 0.25)',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#86efac', fontWeight: 700, fontSize: '0.9rem' }}>
                  <CheckCircle2 size={16} color="#34d399" /> Recommended Preparation Approach:
                </div>
                <p style={{ fontSize: '0.88rem', color: '#d1fae5', margin: 0, lineHeight: 1.5 }}>
                  {resource.recommendedFor}
                </p>
              </div>

            </div>
          )}

          {/* 2. DIRECT ORIGINAL PDF VIEWER */}
          {resource.resourceFormat !== 'YOUTUBE_COURSE' && viewMode === 'PDF_VIEW' && resource.directPdfUrl && (
            <div style={{ width: '100%', height: '100%', minHeight: '560px', flex: 1 }}>
              <iframe 
                src={`${resource.directPdfUrl}#toolbar=1&navpanes=0`} 
                title={resource.title}
                style={{ width: '100%', height: '100%', minHeight: '560px', border: 'none', background: '#374151' }}
              />
            </div>
          )}

          {/* 3. STRUCTURED CHAPTER DIGEST READER */}
          {resource.resourceFormat !== 'YOUTUBE_COURSE' && (viewMode === 'CHAPTERS' || !resource.directPdfUrl) && (
            <div style={{ display: 'grid', gridTemplateColumns: chapters.length > 1 ? '260px 1fr' : '1fr', minHeight: '480px', flex: 1 }}>
              
              {/* Table of Chapters Sidebar */}
              {chapters.length > 1 && (
                <div style={{ 
                  borderRight: '1px solid var(--border-color)', 
                  background: 'rgba(0, 0, 0, 0.2)', 
                  padding: '16px 12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                  overflowY: 'auto'
                }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px', paddingLeft: '8px' }}>
                    Table of Contents ({chapters.length} Modules)
                  </div>
                  {chapters.map((ch, idx) => (
                    <button
                      key={idx}
                      onClick={() => setActiveChapterIndex(idx)}
                      style={{
                        padding: '10px 12px',
                        borderRadius: 'var(--radius-md)',
                        textAlign: 'left',
                        background: activeChapterIndex === idx ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                        border: activeChapterIndex === idx ? '1px solid var(--primary)' : '1px solid transparent',
                        color: activeChapterIndex === idx ? '#93c5fd' : 'var(--text-secondary)',
                        fontSize: '0.85rem',
                        fontWeight: activeChapterIndex === idx ? 700 : 500,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <span style={{ 
                        width: '20px', 
                        height: '20px', 
                        borderRadius: '50%', 
                        background: activeChapterIndex === idx ? 'var(--primary)' : 'rgba(255,255,255,0.06)',
                        color: 'white',
                        fontSize: '0.7rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0
                      }}>
                        {idx + 1}
                      </span>
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {ch.chapterTitle}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {/* Chapter Content Pane */}
              <div style={{ padding: '28px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                  <div>
                    <span style={{ fontSize: '0.78rem', color: '#93c5fd', fontWeight: 700, textTransform: 'uppercase' }}>
                      Chapter {activeChapterIndex + 1} of {chapters.length}
                    </span>
                    <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'white', margin: '4px 0 0 0' }}>
                      {currentChapter.chapterTitle}
                    </h2>
                  </div>

                  <div style={{ display: 'flex', gap: '8px' }}>
                    {activeChapterIndex > 0 && (
                      <button 
                        className="btn btn-secondary" 
                        onClick={() => setActiveChapterIndex(prev => prev - 1)}
                        style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                      >
                        <ArrowLeft size={14} /> Previous
                      </button>
                    )}
                    {activeChapterIndex < chapters.length - 1 && (
                      <button 
                        className="btn btn-primary" 
                        onClick={() => setActiveChapterIndex(prev => prev + 1)}
                        style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                      >
                        Next <ArrowRight size={14} />
                      </button>
                    )}
                  </div>
                </div>

                {/* Rich Markdown / HTML Text Render */}
                <div 
                  style={{ 
                    fontSize: '0.95rem', 
                    lineHeight: 1.8, 
                    color: '#e2e8f0',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}
                  dangerouslySetInnerHTML={{
                    __html: currentChapter.contentMarkdown
                      .replace(/\n\n/g, '<br/><br/>')
                      .replace(/\n• /g, '<br/>• ')
                      .replace(/\n1\. /g, '<br/>1. ')
                      .replace(/\n2\. /g, '<br/>2. ')
                      .replace(/\n3\. /g, '<br/>3. ')
                      .replace(/\n4\. /g, '<br/>4. ')
                      .replace(/\n5\. /g, '<br/>5. ')
                      .replace(/\n6\. /g, '<br/>6. ')
                      .replace(/\n7\. /g, '<br/>7. ')
                      .replace(/\n8\. /g, '<br/>8. ')
                      .replace(/\n9\. /g, '<br/>9. ')
                      .replace(/\n10\. /g, '<br/>10. ')
                      .replace(/\*\*(.*?)\*\*/g, '<strong style="color: #60a5fa;">$1</strong>')
                      .replace(/`([^`]+)`/g, '<code style="background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; color: #fbbf24; font-size: 0.9em;">$1</code>')
                  }}
                />

                <div style={{
                  marginTop: '20px',
                  padding: '14px 18px',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(59, 130, 246, 0.08)',
                  border: '1px solid rgba(59, 130, 246, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '12px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <CheckCircle2 size={16} color="var(--accent)" />
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      Authoritative legal source referenced directly.
                    </span>
                  </div>
                  {resource.directPdfUrl && (
                    <a
                      href={resource.directPdfUrl}
                      download={resource.downloadFileName || 'GovOS_Official_Resource.pdf'}
                      className="btn btn-emerald"
                      style={{ fontSize: '0.8rem', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                    >
                      <Download size={14} /> Download PDF File
                    </a>
                  )}
                </div>

              </div>

            </div>
          )}

        </div>

      </div>
    </div>
  );
};
