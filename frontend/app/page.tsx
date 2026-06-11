'use client';

import { useRef, useEffect, useState } from 'react';
import Message from '@/components/Message';
import Sidebar from '@/components/Sidebar';
import ArizDetailPanel from '@/components/ArizDetailPanel';
import { ArizStepData } from '@/components/ArizStepCard';

interface Msg { id: string; role: 'user' | 'assistant'; content: string; }

export default function Home() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [convId, setConvId] = useState<string | null>(null);
  const [arizStep, setArizStep] = useState<ArizStepData | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading]);
  useEffect(() => { inputRef.current?.focus(); }, [convId]);

  const newChat = async () => {
    const resp = await fetch('/api/conversations', { method: 'POST' });
    const data = await resp.json();
    setConvId(data.id);
    setMessages([]);
    setInput('');
    setArizStep(null);
  };

  const switchChat = async (id: string) => {
    setConvId(id);
    const resp = await fetch(`/api/conversations/${id}/messages`);
    const data = await resp.json();
    setMessages(data.map((m: any, i: number) => ({
      id: `${id}-${i}`,
      role: m.role,
      content: m.content,
    })));
    setInput('');
    setArizStep(null);
  };

  const deleteChat = async (id: string) => {
    await fetch(`/api/conversations/${id}`, { method: 'DELETE' });
    if (convId === id) {
      setConvId(null);
      setMessages([]);
      setArizStep(null);
    }
  };

  useEffect(() => { if (!convId) newChat(); }, []);

  const autoGrow = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
  };

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Msg = { id: Date.now().toString(), role: 'user', content: input };
    const assistantMsg: Msg = { id: (Date.now() + 1).toString(), role: 'assistant', content: '' };
    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setInput('');
    setLoading(true);
    if (inputRef.current) inputRef.current.style.height = 'auto';

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: convId,
          messages: [...messages, userMsg].map(m => ({ role: m.role, content: m.content })),
        }),
        signal: controller.signal,
      });

      const reader = resp.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('0:')) {
            try {
              const text = JSON.parse(line.slice(2));
              setMessages(prev => prev.map(m =>
                m.id === assistantMsg.id ? { ...m, content: m.content + text } : m
              ));
            } catch {}
          }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') console.error(e);
    }
    setLoading(false);
  };

  const stop = () => { abortRef.current?.abort(); setLoading(false); };
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  return (
    <div className="flex h-screen bg-white">
      {/* 侧边栏 */}
      <Sidebar currentId={convId} onNew={newChat} onSwitch={switchChat} onDelete={deleteChat} />

      {/* 主区域 */}
      <div className="flex flex-1 min-w-0">
        {/* 左侧：对话区 */}
        <div className="flex flex-col flex-1 min-w-0">
          {/* 顶部栏 */}
          <header className="flex items-center justify-between px-4 py-2.5 border-b border-gray-100">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-gray-900 flex items-center justify-center">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round">
                  <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                  <path d="M2 17l10 5 10-5"/>
                  <path d="M2 12l10 5 10-5"/>
                </svg>
              </div>
              <span className="font-semibold text-[15px] text-gray-900">Xagent</span>
              <span className="text-xs text-gray-400 ml-1">· PACK创新智能体</span>
            </div>
            {arizStep && (
              <div className="text-xs text-blue-600 bg-blue-50 px-2.5 py-1 rounded-full">
                步骤{arizStep.step}：{arizStep.title}
              </div>
            )}
          </header>

          {/* 消息区 */}
          <div className="flex-1 overflow-y-auto">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full px-4">
                <div className="w-16 h-16 rounded-2xl bg-gray-900 flex items-center justify-center mb-4">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.5">
                    <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                    <path d="M2 17l10 5 10-5"/>
                    <path d="M2 12l10 5 10-5"/>
                  </svg>
                </div>
                <p className="text-gray-900 font-medium text-lg mb-1">动力电池PACK创新智能体</p>
                <p className="text-gray-400 text-sm">基于 TRIZ ARIZ 方法论的系统化创新分析</p>
                <div className="mt-6 grid grid-cols-2 gap-3 max-w-md">
                  {[
                    { icon: '🔍', text: '问题识别与矛盾分析' },
                    { icon: '🧩', text: '系统组件与功能建模' },
                    { icon: '🔗', text: '因果链追溯根因' },
                    { icon: '💡', text: '创新方案生成' },
                  ].map((item, i) => (
                    <button
                      key={i}
                      className="flex items-center gap-2 px-4 py-3 rounded-xl border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-colors text-left"
                      onClick={() => setInput(item.text === '问题识别与矛盾分析' ? '我需要分析一个PACK问题' : `帮我${item.text}`)}
                    >
                      <span className="text-lg">{item.icon}</span>
                      <span className="text-sm text-gray-700">{item.text}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="max-w-[680px] mx-auto px-4 py-6">
                {messages.map(m => (
                  <Message
                    key={m.id}
                    message={m}
                    onPreview={() => {}}
                    onArizStep={(stepData) => setArizStep(stepData)}
                  />
                ))}
                {loading && (
                  <div className="flex gap-3 mb-5 msg-in">
                    <div className="flex items-center gap-1.5 pt-1">
                      <div className="dot" /><div className="dot" /><div className="dot" />
                    </div>
                  </div>
                )}
                <div ref={bottomRef} />
              </div>
            )}
          </div>

          {/* 输入区 */}
          <div className="border-t border-gray-100 bg-white">
            <div className="max-w-[680px] mx-auto px-4 py-3">
              <div className="relative flex items-end border border-gray-200 rounded-2xl bg-white hover:border-gray-300 focus-within:border-gray-400 transition-colors shadow-sm">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={autoGrow}
                  onKeyDown={onKey}
                  placeholder="请输入您遇到的技术问题或现象，或者想要达到的改进指标"
                  rows={4}
                  className="flex-1 px-4 py-3 bg-transparent border-none outline-none resize-none text-[15px] text-gray-900 placeholder:text-gray-400"
                  disabled={loading}
                />
                <div className="pr-2 pb-2">
                  {loading ? (
                    <button onClick={stop} className="w-8 h-8 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-colors">
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="#737373"><rect x="2" y="2" width="10" height="10" rx="2"/></svg>
                    </button>
                  ) : (
                    <button
                      onClick={send}
                      disabled={!input.trim()}
                      className="w-8 h-8 rounded-full flex items-center justify-center transition-colors disabled:opacity-20"
                      style={{ background: input.trim() ? '#10a37f' : '#f4f4f5' }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                      </svg>
                    </button>
                  )}
                </div>
              </div>
              <p className="text-center text-[11px] text-gray-300 mt-2">Xagent · TRIZ ARIZ · MiMo v2.5</p>
            </div>
          </div>
        </div>

        {/* 右侧：ARIZ 详情面板 */}
        {arizStep && (
          <div className="w-[480px] flex-shrink-0">
            <ArizDetailPanel
              stepData={arizStep}
              onClose={() => setArizStep(null)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
