'use client';

import { useState } from 'react';

interface PreviewPanelProps {
  code: string;
  language: string;
  onClose: () => void;
}

export default function PreviewPanel({ code, language, onClose }: PreviewPanelProps) {
  const [refreshKey, setRefreshKey] = useState(0);

  const getSrcDoc = () => {
    if (['html', 'htm'].includes(language.toLowerCase())) {
      return code;
    }
    if (language.toLowerCase() === 'svg') {
      return `<!DOCTYPE html><html><head><style>body{margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;background:#fff;}</style></head><body>${code}</body></html>`;
    }
    return `<!DOCTYPE html><html><head><style>body{margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;background:#fff;font-family:sans-serif;color:#333;}</style></head><body><pre>${code}</pre></body></html>`;
  };

  return (
    <div className="w-[420px] border-l border-gray-200 bg-white flex flex-col h-full animate-slide-in">
      {/* 头部 */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10a37f" strokeWidth="2">
            <rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
          <span className="text-[13px] font-medium text-gray-700">预览</span>
          <span className="text-[11px] text-gray-400">{language}</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setRefreshKey(k => k + 1)}
            className="p-1 rounded hover:bg-gray-100 transition-colors"
            title="刷新"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#666" strokeWidth="2" strokeLinecap="round">
              <path d="M1 4v6h6M23 20v-6h-6"/><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
            </svg>
          </button>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-gray-100 transition-colors"
            title="关闭"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#666" strokeWidth="2" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      </div>

      {/* 预览内容 */}
      <div className="flex-1 bg-white">
        <iframe
          key={refreshKey}
          srcDoc={getSrcDoc()}
          className="w-full h-full border-none"
          sandbox="allow-scripts allow-same-origin"
          title="预览"
        />
      </div>
    </div>
  );
}
