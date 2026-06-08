'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useState } from 'react';

interface MessageProps {
  message: {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
  };
}

// 自定义代码高亮主题
const customTheme = {
  ...oneDark,
  'pre[class*="language-"]': {
    ...oneDark['pre[class*="language-"]'],
    background: '#1a1a24',
    borderRadius: '8px',
    fontSize: '13px',
    lineHeight: '1.6',
  },
  'code[class*="language-"]': {
    ...oneDark['code[class*="language-"]'],
    fontSize: '13px',
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
        background: copied ? 'var(--accent)' : 'var(--bg-tertiary)',
        color: copied ? 'white' : 'var(--text-secondary)',
        border: '1px solid var(--border)',
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
          className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 mr-3 mt-1"
          style={{ background: 'var(--accent)', color: 'white' }}
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
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>
            {message.content}
          </p>
        ) : (
          <div className="markdown-body" style={{ color: 'var(--text-primary)' }}>
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
                          className="absolute top-0 left-0 px-2 py-0.5 text-xs rounded-bl-lg rounded-tr-lg z-10"
                          style={{ background: 'var(--accent)', color: 'white' }}
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
                // 表格样式
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
