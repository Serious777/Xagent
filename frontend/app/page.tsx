'use client';

import { useChat } from 'ai/react';
import { useRef, useEffect } from 'react';
import Message from '@/components/Message';

export default function Home() {
  const { messages, input, handleInputChange, handleSubmit, isLoading, stop } = useChat({
    api: '/api/chat',
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    handleInputChange(e);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isLoading) {
        handleSubmit(e as any);
        if (inputRef.current) {
          inputRef.current.style.height = 'auto';
        }
      }
    }
  };

  return (
    <div className="flex flex-col h-screen" style={{ background: 'var(--bg-primary)' }}>
      {/* 顶部导航 */}
      <header
        className="flex items-center justify-between px-6 py-3 border-b"
        style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold text-white" style={{ background: 'var(--accent)' }}>
            X
          </div>
          <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
            Xagent
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-1 rounded-full" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}>
            MiMo v2.5
          </span>
        </div>
      </header>

      {/* 消息区 */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full px-4">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center text-2xl font-bold mb-6 text-white"
              style={{ background: 'linear-gradient(135deg, var(--accent), #8b5cf6)' }}
            >
              X
            </div>
            <h1 className="text-xl font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
              你好，我是 Xagent
            </h1>
            <p className="text-sm mb-8" style={{ color: 'var(--text-secondary)' }}>
              AI 智能助手，支持工具调用和知识库管理
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-md">
              {[
                { icon: '🔍', label: '搜索信息', desc: '搜索互联网获取实时信息' },
                { icon: '📚', label: '知识库', desc: '管理 LLM Wiki 知识库' },
              ].map((item) => (
                <button
                  key={item.label}
                  onClick={() => {
                    const event = { target: { value: item.desc } } as any;
                    handleInputChange(event);
                    setTimeout(() => {
                      const fakeEvent = { preventDefault: () => {} } as any;
                      handleSubmit(fakeEvent);
                    }, 100);
                  }}
                  className="flex items-start gap-3 p-4 rounded-xl text-left transition-all hover:scale-[1.02]"
                  style={{
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border)',
                  }}
                >
                  <span className="text-xl mt-0.5">{item.icon}</span>
                  <div>
                    <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{item.label}</div>
                    <div className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{item.desc}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6">
            {messages.map((msg) => (
              <Message key={msg.id} message={msg} />
            ))}

            {isLoading && (
              <div className="flex items-start gap-3 mb-6 message-enter">
                <div
                  className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 text-white"
                  style={{ background: 'var(--accent)' }}
                >
                  X
                </div>
                <div
                  className="rounded-2xl rounded-tl-sm px-4 py-3"
                  style={{ background: 'var(--assistant-bg)', border: '1px solid var(--border)' }}
                >
                  <div className="flex items-center gap-1.5">
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* 输入区 */}
      <div className="border-t" style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div
            className="flex items-end gap-2 rounded-2xl px-4 py-3 input-glow transition-all"
            style={{ background: 'var(--bg-primary)', border: '1px solid var(--border)' }}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="输入你的问题... (Enter 发送, Shift+Enter 换行)"
              rows={1}
              className="flex-1 bg-transparent border-none outline-none resize-none text-sm leading-relaxed"
              style={{ color: 'var(--text-primary)' }}
              disabled={isLoading}
            />
            {isLoading ? (
              <button
                type="button"
                onClick={stop}
                className="w-8 h-8 rounded-lg flex items-center justify-center transition-all hover:scale-105 flex-shrink-0 text-white"
                style={{ background: '#ef4444' }}
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="white">
                  <rect x="2" y="2" width="10" height="10" rx="2" />
                </svg>
              </button>
            ) : (
              <button
                type="button"
                onClick={(e) => {
                  if (input.trim()) {
                    handleSubmit(e as any);
                    if (inputRef.current) {
                      inputRef.current.style.height = 'auto';
                    }
                  }
                }}
                disabled={!input.trim()}
                className="w-8 h-8 rounded-lg flex items-center justify-center transition-all hover:scale-105 disabled:opacity-30 disabled:hover:scale-100 flex-shrink-0 text-white"
                style={{ background: input.trim() ? 'var(--accent)' : 'var(--bg-hover)' }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
              </button>
            )}
          </div>
          <p className="text-center mt-2" style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
            Xagent · Powered by MiMo v2.5
          </p>
        </div>
      </div>
    </div>
  );
}
