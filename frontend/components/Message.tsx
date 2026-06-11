'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import CodeBlock from './CodeBlock';
import ArizStepCard, { ArizStepData } from './ArizStepCard';

interface MessageProps {
  message: { id: string; role: 'user' | 'assistant'; content: string };
  onPreview?: (code: string, language: string) => void;
  onArizStep?: (stepData: ArizStepData) => void;
}

// 检测消息中是否包含 ARIZ 工具调用结果
function extractArizSteps(content: string): { before: string; steps: ArizStepData[]; after: string } {
  // 匹配后端生成的工具调用结果块
  // 格式: **调用工具: ariz_stepN_xxx**\n```json\n{...}\n```\n
  console.log('[ARIZ] Parsing message, length:', content.length, 'has tool call:', content.includes('调用工具'));
  const toolRegex = /\*\*调用工具: (ariz_step\d_\w+)\*\*\n```json\n([\s\S]*?)\n```\s*\n?/g;
  const steps: ArizStepData[] = [];
  let before = '';
  let after = '';
  let foundFirst = false;
  let lastIdx = 0;

  let match;
  while ((match = toolRegex.exec(content)) !== null) {
    if (!foundFirst) {
      before = content.slice(0, match.index).trim();
      foundFirst = true;
    }

    const toolName = match[1];
    console.log('[ARIZ] Matched tool:', toolName, 'data length:', match[2].length);
    try {
      const data = JSON.parse(match[2]);
      const stepMatch = toolName.match(/ariz_step(\d)_(\w+)/);
      if (stepMatch) {
        const stepNum = parseInt(stepMatch[1]);
        const stepNames: Record<number, string> = {
          1: '问题识别', 2: '系统组件分析', 3: '接触关系分析',
          4: '功能建模', 5: '系统结构分析', 6: '功能建模问题总结',
          7: '因果链分析', 8: '关键问题/切入点', 9: '生成创新方案',
        };

        let summary = '';
        if (stepNum === 1) summary = data.problem_object || '';
        else if (stepNum === 2) {
          const comps = data.all_components || data.database_components || [];
          summary = `共${comps.length}个组件`;
        } else if (stepNum === 3) summary = `共${(data.contacts || []).length}个接触关系`;
        else summary = data.message || '已完成';

        steps.push({
          step: stepNum,
          title: stepNames[stepNum] || `步骤${stepNum}`,
          summary,
          data,
          status: 'done',
        });
      }
    } catch {}

    lastIdx = match.index + match[0].length;
  }

  if (foundFirst) {
    after = content.slice(lastIdx).trim();
  } else {
    before = content;
  }

  return { before, steps, after };
}

export default function Message({ message, onPreview, onArizStep }: MessageProps) {
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

  // 解析 ARIZ 步骤
  const { before, steps, after } = extractArizSteps(message.content);

  return (
    <div className="msg-in mb-5">
      <div className="markdown-body text-gray-900">
        {/* 工具调用前的文本 */}
        {before && (
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
            {before}
          </ReactMarkdown>
        )}

        {/* ARIZ 步骤卡片 */}
        {steps.length > 0 && (
          <div className="my-3">
            {steps.map((step, i) => (
              <ArizStepCard
                key={i}
                stepData={step}
                onView={(sd) => onArizStep?.(sd)}
              />
            ))}
          </div>
        )}

        {/* 工具调用后的文本 */}
        {after && (
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
            {after}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}
