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
  conversationId?: string | null;
  onConfirmed?: () => void;
}

export default function ArizStepCard({ stepData, onView, conversationId, onConfirmed }: ArizStepCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

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

  const isCurrent = stepData.status === 'current' && !confirmed;
  const displayStatus = confirmed ? 'done' : stepData.status;

  // 只有后端确认数据已保存（工具已调用）才显示确认按钮
  const isSaved = stepData.data?._saved === true || (stepData as any).saved === true || confirmed;

  const handleConfirm = async () => {
    if (!conversationId) return;
    setConfirming(true);
    try {
      const resp = await fetch(`/api/ariz/confirm/${conversationId}`, { method: 'POST' });
      const data = await resp.json();
      if (data.ok) {
        setConfirmed(true);
        onConfirmed?.();
      }
    } catch (e) {
      console.error('确认失败:', e);
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div className={`mb-4 border rounded-xl overflow-hidden transition-all ${statusColors[displayStatus]}`}>
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:opacity-90 transition-opacity"
        onClick={() => {
          setExpanded(!expanded);
          if (!expanded) onView(stepData);
        }}
      >
        <div className="flex items-center gap-2.5">
          <span className="text-sm">{statusIcons[displayStatus]}</span>
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
          {isSaved && isCurrent && (
            <button
              className="text-xs px-3 py-1 rounded-md bg-emerald-500 text-white hover:bg-emerald-600 transition-colors font-medium disabled:opacity-50"
              onClick={(e) => {
                e.stopPropagation();
                handleConfirm();
              }}
              disabled={confirming}
            >
              {confirming ? '确认中...' : '确认'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

const STEP_NAMES: Record<number, string> = {
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

function buildStepSummary(stepNum: number, data: any): string {
  if (stepNum === 1) return data.problem_object || '';
  if (stepNum === 2) return `共${(data.all_components || []).length}个组件`;
  if (stepNum === 3) return `${(data.contacts || []).length}组接触关系`;
  if (stepNum === 4) return `${(data.functions || []).length}条功能关系`;
  return data.status || data.message || '已完成';
}

/**
 * 从消息内容中解析 ARIZ 步骤卡片
 * 格式: **调用工具: ariz_stepN_xxx**
 * ```json
 * {"card_data": {...}, "status": "saved", ...}
 * ```
 */
export function parseArizSteps(content: string): { textParts: string[]; steps: ArizStepData[] } {
  const textParts: string[] = [];
  const steps: ArizStepData[] = [];

  const toolRegex = /\*\*调用工具: (ariz_step\d_\w+)\*\*\n```json\n([\s\S]*?)\n```/g;
  let lastIndex = 0;
  let match;

  while ((match = toolRegex.exec(content)) !== null) {
    const before = content.slice(lastIndex, match.index).trim();
    if (before) textParts.push(before);

    try {
      const result = JSON.parse(match[2]);

      if (result.card_data) {
        const card = result.card_data;
        steps.push({
          step: card.step,
          title: card.title || STEP_NAMES[card.step] || `步骤${card.step}`,
          summary: buildStepSummary(card.step, card.data || {}),
          data: { ...(card.data || {}), _saved: card.saved === true },
          status: card.status || 'current',
        });
      } else {
        const toolName = match[1];
        const stepMatch = toolName.match(/ariz_step(\d)_(\w+)/);
        if (stepMatch) {
          const stepNum = parseInt(stepMatch[1]);
          steps.push({
            step: stepNum,
            title: STEP_NAMES[stepNum] || `步骤${stepNum}`,
            summary: buildStepSummary(stepNum, result),
            data: result,
            status: 'current',
          });
        }
      }
    } catch {}

    lastIndex = match.index + match[0].length;
  }

  const remaining = content.slice(lastIndex).trim();
  if (remaining) textParts.push(remaining);

  // 去重：同一步骤后出现的覆盖先出现的（支持修改流程）
  const deduped = new Map<number, ArizStepData>();
  for (const step of steps) {
    deduped.set(step.step, step);
  }

  return { textParts, steps: Array.from(deduped.values()) };
}
