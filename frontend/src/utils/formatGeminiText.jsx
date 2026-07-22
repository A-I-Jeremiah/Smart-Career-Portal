import React from 'react';

const renderInlineText = (text) => {
  if (!text) return null;

  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    const boldMatch = part.match(/^\*\*([^*]+)\*\*$/);
    if (boldMatch) {
      return <strong key={index}>{boldMatch[1]}</strong>;
    }
    return <React.Fragment key={index}>{part}</React.Fragment>;
  });
};

const cleanLine = (line) => line.replace(/\s+/g, ' ').trim();

const normalizeGeminiText = (text) => (
  String(text || '')
    .replace(/\r\n/g, '\n')
    .replace(/([^\n])\s+(#{1,6}\s*\S)/g, '$1\n$2')
    .replace(/([^\n])\s+(\d+\.\s+\S)/g, '$1\n$2')
    .replace(/([^\n])\s+([-*](?!\*)\s*(?:\*\*)?[A-Za-z0-9])/g, '$1\n$2')
);

export const stripMarkdownSyntax = (text) => (
  cleanLine(String(text || '')
    .replace(/^#{1,6}\s*/, '')
    .replace(/^[-*](?!\*)\s*/, '')
    .replace(/^\d+\.\s+/, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1'))
);

export const stripBlockMarkdownSyntax = (text) => (
  cleanLine(String(text || '')
    .replace(/^#{1,6}\s*/, '')
    .replace(/^[-*](?!\*)\s*/, '')
    .replace(/^\d+\.\s+/, ''))
);

const GeminiFormattedText = ({ text, compact = false }) => {
  if (!text) return null;

  const lines = normalizeGeminiText(text)
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);

  return (
    <div className={`gemini-rich-text${compact ? ' gemini-rich-text-compact' : ''}`}>
      {lines.map((line, index) => {
        const heading = line.match(/^(#{1,6})\s*(.+)$/);
        if (heading) {
          const level = heading[1].length;
          const HeadingTag = level <= 2 ? 'h3' : 'h4';
          const headingClass = level <= 2 ? 'gemini-rich-heading' : 'gemini-rich-subheading';
          return (
            <HeadingTag key={index} className={headingClass}>
              {renderInlineText(stripMarkdownSyntax(heading[2]))}
            </HeadingTag>
          );
        }

        const bullet = line.match(/^[-*](?!\*)\s*(.+)$/);
        if (bullet) {
          return (
            <div key={index} className="gemini-rich-list-item">
              <span className="gemini-rich-marker" aria-hidden="true" />
              <span>{renderInlineText(cleanLine(bullet[1]))}</span>
            </div>
          );
        }

        const numbered = line.match(/^(\d+)\.\s+(.+)$/);
        if (numbered) {
          return (
            <div key={index} className="gemini-rich-list-item">
              <span className="gemini-rich-number">{numbered[1]}</span>
              <span>{renderInlineText(cleanLine(numbered[2]))}</span>
            </div>
          );
        }

        return (
          <p key={index} className="gemini-rich-paragraph">
            {renderInlineText(cleanLine(line))}
          </p>
        );
      })}
    </div>
  );
};

export default GeminiFormattedText;
