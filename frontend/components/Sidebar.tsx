'use client';

import { useState, useEffect } from 'react';

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface SidebarProps {
  currentId: string | null;
  onNew: () => void;
  onSwitch: (id: string) => void;
  onDelete: (id: string) => void;
  refreshKey?: number;
}

export default function Sidebar({ currentId, onNew, onSwitch, onDelete, refreshKey }: SidebarProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  const refresh = async () => {
    const resp = await fetch('/api/conversations');
    const data = await resp.json();
    setConversations(data);
  };

  useEffect(() => { refresh(); }, [currentId, refreshKey]);
  useEffect(() => {
    const timer = setInterval(refresh, 5000);
    return () => clearInterval(timer);
  }, []);

  const filteredConversations = conversations.filter(c =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const openHistory = () => {
    setShowHistory(true);
    refresh();
  };

  return (
    <>
      {/* ===== 窄图标栏 ===== */}
      <div
        className="flex flex-col items-center py-3 bg-[#fafafa] border-r border-gray-100"
        style={{ width: '56px', minWidth: '56px' }}
      >
        {/* Logo */}
        <div className="mb-4 w-9 h-9 rounded-xl bg-gray-900 flex items-center justify-center">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>

        {/* 菜单 */}
        <div className="flex flex-col gap-1">
          {/* 零件创新智能体 */}
          <div className="relative">
            <button
              onClick={() => {}}
              onMouseEnter={() => setHovered('agent')}
              onMouseLeave={() => setHovered(null)}
              className="w-9 h-9 flex items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-all"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="7" height="7" rx="1.5"/>
                <rect x="14" y="3" width="7" height="7" rx="1.5"/>
                <rect x="3" y="14" width="7" height="7" rx="1.5"/>
                <rect x="14" y="14" width="7" height="7" rx="1.5"/>
              </svg>
            </button>
            {hovered === 'agent' && (
              <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-2.5 py-1 rounded-md bg-gray-900 text-white text-[11px] whitespace-nowrap z-50 pointer-events-none shadow-lg">
                零件创新智能体
              </div>
            )}
          </div>

          {/* 历史记录 */}
          <div className="relative">
            <button
              onClick={openHistory}
              onMouseEnter={() => setHovered('history')}
              onMouseLeave={() => setHovered(null)}
              className="w-9 h-9 flex items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-all"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            </button>
            {hovered === 'history' && (
              <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-2.5 py-1 rounded-md bg-gray-900 text-white text-[11px] whitespace-nowrap z-50 pointer-events-none shadow-lg">
                历史记录
              </div>
            )}
          </div>
        </div>

        {/* 分隔线 */}
        <div className="w-6 border-t border-gray-200 my-3" />

        {/* 新建对话 */}
        <div className="relative">
          <button
            onClick={onNew}
            onMouseEnter={() => setHovered('new')}
            onMouseLeave={() => setHovered(null)}
            className="w-9 h-9 flex items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-all"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
          </button>
          {hovered === 'new' && (
            <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-2.5 py-1 rounded-md bg-gray-900 text-white text-[11px] whitespace-nowrap z-50 pointer-events-none shadow-lg">
              新对话
            </div>
          )}
        </div>
      </div>

      {/* ===== 历史记录弹窗 ===== */}
      {showHistory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setShowHistory(false)} />
          <div className="relative bg-white rounded-2xl shadow-2xl w-[480px] max-h-[80vh] flex flex-col animate-fade-in">
            {/* 头部 */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#737373" strokeWidth="1.8" strokeLinecap="round">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
                <span className="font-medium text-gray-800 text-[15px]">历史记录</span>
              </div>
              <button
                onClick={() => setShowHistory(false)}
                className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#737373" strokeWidth="2" strokeLinecap="round">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>

            {/* 搜索框 */}
            <div className="px-5 py-3">
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-50 border border-gray-200">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2" strokeLinecap="round">
                  <circle cx="11" cy="11" r="8"/>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <input
                  type="text"
                  placeholder="搜索对话..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="flex-1 text-[13px] bg-transparent outline-none placeholder:text-gray-400 text-gray-700"
                />
              </div>
            </div>

            {/* 对话列表 */}
            <div className="flex-1 overflow-y-auto px-3 pb-3">
              {filteredConversations.length === 0 ? (
                <div className="text-center py-10 text-gray-400 text-[13px]">暂无对话</div>
              ) : (
                filteredConversations.map((conv) => (
                  <div
                    key={conv.id}
                    className={`group flex items-center gap-2.5 px-3 py-2.5 rounded-lg cursor-pointer mb-0.5 transition-all ${
                      currentId === conv.id ? 'bg-gray-100' : 'hover:bg-gray-50'
                    }`}
                    onClick={() => { onSwitch(conv.id); setShowHistory(false); }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#a3a3a3" strokeWidth="1.5" className="flex-shrink-0">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                    <span className="text-[13px] text-gray-700 truncate flex-1">{conv.title}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); onDelete(conv.id); }}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-200 transition-all"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2">
                        <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                      </svg>
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
