'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import CodeBlock from './CodeBlock';
import ArizStepCard, { ArizStepData, parseArizSteps } from './ArizStepCard';

interface MessageProps {
  message: { id: string; role: 'user' | 'assistant'; content: string };
  onPreview?: (code: string, language: string) => void;
  onArizStep?: (stepData: ArizStepData) => void;
  onStepConfirmed?: () => void;
  conversationId?: string | null;
}

export default function Message({ message, onPreview, onArizStep, onStepConfirmed, conversationId }: MessageProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="msg-in mb-5 flex justify-end">
        <div className="bg-[#f4f4f4] rounded-3xl px-5 py-2.5 max-w-[85%] ml-auto">
          <p className="text-[15px] text-gray-900 leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  const { textParts, steps } = parseArizSteps(message.content);
  const cleanText = textParts.join('\n\n').trim();

  return (
    <div className="msg-in mb-5">
      <div className="markdown-body text-gray-900">
        {cleanText && (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                const code = String(children).replace(/\n$/, '');
                const isInline = !match && !code.includes('\n');
                if (isInline) return <code className={className} {...props}>{children}</code>;
                return <CodeBlock language={match?.[1] || 'text'} code={code} onPreview={onPreview} />;
              },
            }}
          >
            {cleanText}
          </ReactMarkdown>
        )}

        {steps.length > 0 && (
          <div className="my-3">
            {steps.map((step, i) => (
              <ArizStepCard
                key={`${step.step}-${i}`}
                stepData={step}
                onView={(sd) => onArizStep?.(sd)}
                conversationId={conversationId}
                onConfirmed={onStepConfirmed}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
