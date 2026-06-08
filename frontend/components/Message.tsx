'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useState } from 'react';

interface MessageProps {
  message: {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
  };
}

const customTheme = {
  ...oneLight,
  'pre[class*="language-"]': {
    ...oneLight['pre[class*="language-"]'],
    background: '#1e293b',
    borderRadius: '8px',
    fontSize: '13px',
    lineHeight: '1.6',
    color: '#e2e8f0',
  },
  'code[class*="language-"]': {
    ...oneLight['code[class*="language-"]'],
    fontSize: '13px',
    color: '#e2e8f0',
  },
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="absolute top-2 right-2 px-2 py-1 rounded text-xs transition-all"
      style={{
        background: copied ? 'var(--accent)' : 'rgba(255,255,255,0.1)',
        color: copied ? 'white' : '#94a3b8',
      }}
    >
      {copied ? '✓ 已复制' : '复制'}
    </button>
  );
}

export default function Message({ message }: MessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex mb-6 message-enter ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 mr-3 mt-1 text-white"
          style={{ background: 'var(--accent)' }}
        >
          X
        </div>
      )}

      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser ? 'rounded-tr-sm' : 'rounded-tl-sm'
        }`}
        style={{
          background: isUser ? 'var(--user-bg)' : 'var(--assistant-bg)',
          border: `1px solid ${isUser ? 'transparent' : 'var(--border)'}`,
        }}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed text-white">
            {message.content}
          </p>
        ) : (
          <div className="markdown-body">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ node, inline, className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  const codeString = String(children).replace(/\n$/, '');

                  if (inline) {
                    return (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  }

                  return (
                    <div className="relative my-3">
                      {match && (
                        <div
                          className="absolute top-0 left-0 px-2 py-0.5 text-xs rounded-bl-lg rounded-tr-lg z-10 text-white"
                          style={{ background: 'var(--accent)' }}
                        >
                          {match[1]}
                        </div>
                      )}
                      <SyntaxHighlighter
                        style={customTheme}
                        language={match ? match[1] : 'text'}
                        PreTag="div"
                        customStyle={{
                          margin: 0,
                          borderTopLeftRadius: match ? '0' : '8px',
                        }}
                      >
                        {codeString}
                      </SyntaxHighlighter>
                      <CopyButton text={codeString} />
                    </div>
                  );
                },
                table({ children }) {
                  return (
                    <div className="overflow-x-auto my-3">
                      <table>{children}</table>
                    </div>
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>

      {isUser && (
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center text-xs flex-shrink-0 ml-3 mt-1"
          style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}
        >
          U
        </div>
      )}
    </div>
  );
}
