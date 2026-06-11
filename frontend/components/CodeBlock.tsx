'use client';

import { useState, useRef } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

const codeTheme = {
  ...oneDark,
  'pre[class*="language-"]': {
    ...oneDark['pre[class*="language-"]'],
    background: '#1e1e1e',
    borderRadius: '0 0 8px 8px',
    fontSize: '13px',
    lineHeight: '1.55',
    margin: 0,
  },
  'code[class*="language-"]': { ...oneDark['code[class*="language-"]'], fontSize: '13px' },
};

interface CodeBlockProps {
  language: string;
  code: string;
  onPreview?: (code: string, language: string) => void;
}

export default function CodeBlock({ language, code, onPreview }: CodeBlockProps) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const preRef = useRef<HTMLPreElement>(null);

  const canPreview = ['html', 'htm', 'svg'].includes(language.toLowerCase());

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 rounded-lg overflow-hidden border border-gray-200">
      {/* 标题栏 — 始终显示 */}
      <div
        className="flex items-center justify-between px-3 py-2 bg-[#f7f7f8] cursor-pointer select-none hover:bg-[#efefef] transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          {/* 折叠箭头 */}
          <svg
            width="12" height="12" viewBox="0 0 12 12" fill="none"
            className={`transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
          >
            <path d="M4.5 2.5L8 6L4.5 9.5" stroke="#737373" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="text-[12px] font-mono text-gray-500">{language || 'code'}</span>
          <span className="text-[11px] text-gray-400">{code.split('\n').length} 行</span>
        </div>
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          {canPreview && onPreview && (
            <button
              onClick={() => onPreview(code, language)}
              className="px-2 py-0.5 text-[11px] rounded bg-[#10a37f] text-white hover:bg-[#0e8f6e] transition-colors"
            >
              预览
            </button>
          )}
          <button
            onClick={handleCopy}
            className="px-2 py-0.5 text-[11px] rounded transition-colors"
            style={{ background: copied ? '#10a37f' : '#e5e5e5', color: copied ? 'white' : '#666' }}
          >
            {copied ? '✓ 已复制' : '复制'}
          </button>
        </div>
      </div>

      {/* 代码内容 — 默认折叠 */}
      {expanded && (
        <div className="relative">
          <SyntaxHighlighter
            ref={preRef}
            style={codeTheme}
            language={language || 'text'}
            PreTag="div"
            customStyle={{ margin: 0, borderRadius: '0 0 8px 8px' }}
          >
            {code}
          </SyntaxHighlighter>
        </div>
      )}
    </div>
  );
}
