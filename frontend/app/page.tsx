'use client';

import { useChat } from 'ai/react';
import Message from '@/components/Message';

export default function Home() {
  const { messages, input, handleInputChange, handleSubmit, isLoading, stop } = useChat({
    api: '/api/chat',
  });

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto">
      {/* 头部 */}
      <header className="border-b p-4 flex items-center justify-between">
        <h1 className="text-xl font-bold">⚡ Xagent</h1>
        <span className="text-sm text-gray-500">AI Agent with Skills</span>
      </header>

      {/* 消息区 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-20">
            <p className="text-lg">👋 你好！我是 Xagent</p>
            <p className="text-sm mt-2">我可以帮你搜索信息、管理知识库等</p>
          </div>
        )}
        {messages.map((msg) => (
          <Message key={msg.id} message={msg} />
        ))}

        {isLoading && (
          <div className="flex items-center gap-2 text-gray-500 p-4">
            <div className="animate-pulse">●</div>
            <div className="animate-pulse delay-100">●</div>
            <div className="animate-pulse delay-200">●</div>
            <span className="text-sm ml-2">思考中...</span>
          </div>
        )}
      </div>

      {/* 输入区 */}
      <form onSubmit={handleSubmit} className="border-t p-4">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={handleInputChange}
            placeholder="输入你的问题..."
            className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          {isLoading ? (
            <button
              type="button"
              onClick={stop}
              className="bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600"
            >
              停止
            </button>
          ) : (
            <button
              type="submit"
              className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50"
              disabled={!input.trim()}
            >
              发送
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
