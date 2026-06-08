'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useState } from 'react';

interface MessageProps {
  message: { id: string; role: 'user' | 'assistant'; content: string; };
}

const codeTheme = {
  ...oneDark,
  'pre[class*="language-"]': { ...oneDark['pre[class*="language-"]'], background: '#1e1e1e', borderRadius: '8px', fontSize: '13px', lineHeight: '1.55' },
  'code[class*="language-"]': { ...oneDark['code[class*="language-"]'], fontSize: '13px' },
};

function CopyBtn({ text }: { text: string }) {
  const [ok, setOk] = useState(false);
  return (
    <button
      onClick={async () => { await navigator.clipboard.writeText(text); setOk(true); setTimeout(() => setOk(false), 2000); }}
      className="absolute top-2 right-2 px-2 py-0.5 rounded text-[11px] opacity-0 group-hover:opacity-100 transition-opacity"
      style={{ background: ok ? '#10a37f' : '#333', color: 'white' }}
    >
      {ok ? '✓' : '复制'}
    </button>
  );
}

export default function Message({ message }: MessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`msg-in mb-5 ${isUser ? 'flex justify-end' : ''}`}>
      {isUser ? (
        /* 用户消息 — 灰色圆角气泡，参考 ChatGPT */
        <div className="bg-[#f4f4f4] rounded-3xl px-5 py-2.5 max-w-[85%] ml-auto">
          <p className="text-[15px] text-gray-900 leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>
      ) : (
        /* 助手消息 — 纯文字，无气泡，参考 ChatGPT */
        <div className="markdown-body text-gray-900">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                const code = String(children).replace(/\n$/, '');
                if (inline) return <code className={className} {...props}>{children}</code>;
                return (
                  <div className="relative group my-3">
                    {match && (
                      <div className="absolute top-0 left-0 px-2 py-0.5 text-[11px] text-white bg-[#333] rounded-t-lg rounded-bl-lg z-10">{match[1]}</div>
                    )}
                    <SyntaxHighlighter style={codeTheme} language={match?.[1] || 'text'} PreTag="div"
                      customStyle={{ margin: 0, borderTopLeftRadius: match ? 0 : '8px' }}>
                      {code}
                    </SyntaxHighlighter>
                    <CopyBtn text={code} />
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
  );
}
