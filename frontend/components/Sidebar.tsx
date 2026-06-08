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
}

export default function Sidebar({ currentId, onNew, onSwitch, onDelete }: SidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [open, setOpen] = useState(true);

  const refresh = async () => {
    const resp = await fetch('/api/conversations');
    const data = await resp.json();
    setConversations(data);
  };

  useEffect(() => { refresh(); }, [currentId]);

  // 每 3 秒刷新一次列表
  useEffect(() => {
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div
      className="flex flex-col border-r transition-all duration-200"
      style={{
        width: open ? '260px' : '0px',
        minWidth: open ? '260px' : '0px',
        borderColor: '#e5e5e5',
        background: '#f9fafb',
        overflow: 'hidden',
      }}
    >
      {/* 新建对话 */}
      <div className="p-3">
        <button
          onClick={onNew}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-700 hover:bg-gray-200 transition-colors border border-gray-200"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          新对话
        </button>
      </div>

      {/* 对话列表 */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {conversations.map((conv) => (
          <div
            key={conv.id}
            onClick={() => onSwitch(conv.id)}
            className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm cursor-pointer mb-0.5 transition-colors ${
              currentId === conv.id
                ? 'bg-gray-200 text-gray-900'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="flex-shrink-0 opacity-50">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <span className="truncate flex-1">{conv.title}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(conv.id);
              }}
              className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-gray-300 rounded transition-opacity"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
