'use client';

import React, { useState } from 'react';

export interface ArizStepData {
  step: number;
  title: string;
  summary: string;
  data: any;
  status: 'done' | 'current' | 'pending';
}

interface ArizStepCardProps {
  stepData: ArizStepData;
  onView: (stepData: ArizStepData) => void;
}

export default function ArizStepCard({ stepData, onView }: ArizStepCardProps) {
  const [expanded, setExpanded] = useState(false);

  const statusColors = {
    done: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    current: 'bg-blue-50 text-blue-700 border-blue-200',
    pending: 'bg-gray-50 text-gray-500 border-gray-200',
  };

  const statusIcons = {
    done: '✅',
    current: '🔍',
    pending: '⬜',
  };

  return (
    <div className={`mb-4 border rounded-xl overflow-hidden transition-all ${statusColors[stepData.status]}`}>
      {/* 折叠头部 */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:opacity-90 transition-opacity"
        onClick={() => {
          setExpanded(!expanded);
          if (!expanded) onView(stepData);
        }}
      >
        <div className="flex items-center gap-2.5">
          <span className="text-sm">{statusIcons[stepData.status]}</span>
          <span className="font-medium text-sm">
            步骤{stepData.step}：{stepData.title}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs opacity-70 truncate max-w-[300px]">
            {stepData.summary}
          </span>
          <button
            className="text-xs px-2.5 py-1 rounded-md bg-white/60 hover:bg-white/80 border border-current/20 transition-colors font-medium"
            onClick={(e) => {
              e.stopPropagation();
              onView(stepData);
            }}
          >
            查看
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * 从消息内容中解析 ARIZ 步骤数据
 * 后端工具调用结果格式: **调用工具: ariz_stepN_xxx**\n```json\n{...}\n```
 */
export function parseArizSteps(content: string): { textParts: string[]; steps: ArizStepData[] } {
  const textParts: string[] = [];
  const steps: ArizStepData[] = [];

  // 匹配工具调用结果
  const toolRegex = /\*\*调用工具: (ariz_step\d_\w+)\*\*\n```json\n([\s\S]*?)\n```/g;
  let lastIndex = 0;
  let match;

  while ((match = toolRegex.exec(content)) !== null) {
    // 添加工具调用前的文本
    const before = content.slice(lastIndex, match.index).trim();
    if (before) textParts.push(before);

    const toolName = match[1];
    try {
      const data = JSON.parse(match[2]);
      const stepMatch = toolName.match(/ariz_step(\d)_(\w+)/);
      if (stepMatch) {
        const stepNum = parseInt(stepMatch[1]);
        const stepNames: Record<number, string> = {
          1: '问题识别',
          2: '系统组件分析',
          3: '接触关系分析',
          4: '功能建模',
          5: '系统结构分析',
          6: '功能建模问题总结',
          7: '因果链分析',
          8: '关键问题/切入点',
          9: '生成创新方案',
        };

        // 生成摘要
        let summary = '';
        if (stepNum === 1) {
          summary = data.problem_object || '';
        } else if (stepNum === 2) {
          const comps = data.all_components || data.database_components || [];
          summary = `共${comps.length}个组件`;
        } else if (stepNum === 3) {
          const contacts = data.contacts || [];
          summary = `共${contacts.length}个接触关系`;
        } else {
          summary = data.status || data.message || '已完成';
        }

        steps.push({
          step: stepNum,
          title: stepNames[stepNum] || `步骤${stepNum}`,
          summary,
          data,
          status: data.status === 'completed' ? 'done' : 'done',
        });
      }
    } catch {}

    lastIndex = match.index + match[0].length;
  }

  // 添加剩余文本
  const remaining = content.slice(lastIndex).trim();
  if (remaining) textParts.push(remaining);

  return { textParts, steps };
}
