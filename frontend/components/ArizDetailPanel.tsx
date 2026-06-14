'use client';

import React, { useState } from 'react';
import { ArizStepData } from './ArizStepCard';

interface ArizDetailPanelProps {
  stepData: ArizStepData;
  onClose: () => void;
}

// ========== Step 1: 问题识别 =========
function Step1Detail({ data }: { data: any }) {
  const d = data.step1_result || data;
  return (
    <div className="space-y-4">
      <InfoRow label="问题对象" value={d.problem_object} />
      <InfoRow label="现象" value={d.phenomenon} />
      <InfoRow label="目标" value={d.goal} />
      <InfoRow label="矛盾方向" value={d.contradiction_hint} />
      {d.constraints?.length > 0 && (
        <div>
          <Label text="约束条件" />
          <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
            {d.constraints.map((c: string, i: number) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      )}
      {d.clarification_needed?.length > 0 && (
        <div>
          <Label text="待澄清问题" />
          <ul className="list-disc list-inside text-sm text-amber-700 space-y-1">
            {d.clarification_needed.map((q: string, i: number) => <li key={i}>{q}</li>)}
          </ul>
        </div>
      )}
      {data.database_query?.primary_system && (
        <div>
          <Label text="匹配到的系统" />
          <p className="text-sm text-gray-900 font-medium">
            {data.database_query.primary_system.system?.name}
          </p>
        </div>
      )}
    </div>
  );
}

// ========== Step 2: 系统组件分析 ==========
function Step2Detail({ data }: { data: any }) {
  const dbSystem = data.database_query?.primary_system;
  const dbComponents: any[] = dbSystem?.components || [];
  const supersystemComponents: string[] = data.supersystem_components || [];
  const userAdded: string[] = data.user_added || [];

  const [components, setComponents] = useState(() => {
    const result: any[] = [];
    for (const dbComp of dbComponents) {
      result.push({
        name: dbComp.name,
        functions: dbComp.functions?.map((f: any) => f.function_name) || [],
        description: dbComp.description || '',
        isFromDb: true,
        isSuper: false,
      });
    }
    for (const raw of supersystemComponents) {
      result.push({ name: raw, functions: [], description: '超系统组件', isFromDb: false, isSuper: true });
    }
    for (const raw of userAdded) {
      result.push({ name: raw, functions: [], description: '用户补充', isFromDb: false, isSuper: false });
    }
    return result;
  });

  const [newCompName, setNewCompName] = useState('');
  const [showAdd, setShowAdd] = useState(false);

  const handleDelete = (index: number) => {
    setComponents((prev: any[]) => prev.filter((_: any, i: number) => i !== index));
  };

  const handleAdd = () => {
    if (!newCompName.trim()) return;
    setComponents((prev: any[]) => [...prev, {
      name: newCompName.trim(), functions: [], description: '用户补充', isFromDb: false, isSuper: false,
    }]);
    setNewCompName('');
    setShowAdd(false);
  };

  return (
    <div>
      {data.supersystem && (
        <div className="mb-4">
          <Label text="超系统" />
          <p className="text-sm text-gray-700">{data.supersystem}</p>
        </div>
      )}
      {data.system_name && (
        <div className="mb-4">
          <Label text="系统" />
          <p className="text-sm font-medium text-gray-900">{data.system_name}</p>
        </div>
      )}
      {dbSystem?.system?.description && (
        <p className="text-xs text-gray-500 mb-4">{dbSystem.system.description}</p>
      )}
      <Label text={`组件清单（${components.length}个）`} />
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-2.5 font-medium text-gray-600">组件</th>
            <th className="text-left py-2.5 font-medium text-gray-600">功能</th>
            <th className="text-right py-2.5 font-medium text-gray-600 w-16">操作</th>
          </tr>
        </thead>
        <tbody>
          {components.map((comp: any, i: number) => {
            const funcs = (comp.functions || []).join('、');
            return (
              <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-2.5">
                  <span className="text-gray-900">{comp.name}</span>
                  {comp.isFromDb && <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600">库</span>}
                  {comp.isSuper && <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded bg-purple-50 text-purple-600">超系统</span>}
                </td>
                <td className="py-2.5 text-gray-600">{funcs || <span className="text-gray-400">—</span>}</td>
                <td className="py-2.5 text-right">
                  <button onClick={() => handleDelete(i)} className="text-xs text-red-500 hover:text-red-700 transition-colors">删除</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {showAdd ? (
        <div className="mt-3 flex items-center gap-2">
          <input autoFocus value={newCompName} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewCompName(e.target.value)}
            onKeyDown={(e: React.KeyboardEvent) => e.key === 'Enter' && handleAdd()}
            placeholder="输入组件名" className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <button onClick={handleAdd} className="text-sm text-blue-600 hover:text-blue-800 font-medium">确认</button>
          <button onClick={() => { setShowAdd(false); setNewCompName(''); }} className="text-sm text-gray-500 hover:text-gray-700">取消</button>
        </div>
      ) : (
        <button onClick={() => setShowAdd(true)} className="mt-3 text-sm text-blue-600 hover:text-blue-800 font-medium">+ 新增</button>
      )}
    </div>
  );
}

// ========== Step 3: 接触关系分析 ==========
function Step3Detail({ data }: { data: any }) {
  const contacts = data.contacts || [];
  return (
    <div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-2.5 font-medium text-gray-600">组件A</th>
            <th className="text-left py-2.5 font-medium text-gray-600">组件B</th>
            <th className="text-left py-2.5 font-medium text-gray-600">接触类型</th>
            <th className="text-left py-2.5 font-medium text-gray-600">界面</th>
          </tr>
        </thead>
        <tbody>
          {contacts.map((c: any, i: number) => (
            <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-2.5 text-gray-900">{c.component_a}</td>
              <td className="py-2.5 text-gray-900">{c.component_b}</td>
              <td className="py-2.5 text-gray-600">{c.contact_type}</td>
              <td className="py-2.5 text-gray-600">{c.interface || c.interface_desc}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ========== Step 4: 功能建模 ==========
function Step4Detail({ data }: { data: any }) {
  const functions = data.functions || [];
  const typeColors: Record<string, string> = {
    useful: 'bg-emerald-50 text-emerald-700', insufficient: 'bg-amber-50 text-amber-700',
    excessive: 'bg-red-50 text-red-700', harmful: 'bg-red-100 text-red-800', missing: 'bg-gray-100 text-gray-600',
  };
  const typeLabels: Record<string, string> = {
    useful: '有用', insufficient: '不足', excessive: '过度', harmful: '有害', missing: '缺失',
  };
  return (
    <div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-2.5 font-medium text-gray-600">源</th>
            <th className="text-left py-2.5 font-medium text-gray-600">功能</th>
            <th className="text-left py-2.5 font-medium text-gray-600">目标</th>
            <th className="text-left py-2.5 font-medium text-gray-600">类型</th>
            <th className="text-left py-2.5 font-medium text-gray-600">描述</th>
          </tr>
        </thead>
        <tbody>
          {functions.map((f: any, i: number) => (
            <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-2.5 text-gray-900">{f.source}</td>
              <td className="py-2.5 text-gray-900">{f.function}</td>
              <td className="py-2.5 text-gray-600">{f.target}</td>
              <td className="py-2.5"><span className={`text-xs px-2 py-0.5 rounded-full ${typeColors[f.type] || ''}`}>{typeLabels[f.type] || f.type}</span></td>
              <td className="py-2.5 text-gray-600 text-xs">{f.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ========== 通用详情（Step 5-9） ==========
function GenericDetail({ data }: { data: any }) {
  return (
    <pre className="text-sm text-gray-700 bg-gray-50 rounded-lg p-4 overflow-auto max-h-[500px]">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

// ========== 公共组件 ==========
function Label({ text }: { text: string }) {
  return <p className="text-xs font-medium text-gray-500 mb-1.5 uppercase tracking-wide">{text}</p>;
}

function InfoRow({ label, value }: { label: string; value?: string }) {
  if (!value) return null;
  return (
    <div>
      <Label text={label} />
      <p className="text-sm text-gray-900">{value}</p>
    </div>
  );
}

// ========== 主面板 ==========
export default function ArizDetailPanel({ stepData, onClose }: ArizDetailPanelProps) {
  const renderContent = () => {
    switch (stepData.step) {
      case 1: return <Step1Detail data={stepData.data} />;
      case 2: return <Step2Detail data={stepData.data} />;
      case 3: return <Step3Detail data={stepData.data} />;
      case 4: return <Step4Detail data={stepData.data} />;
      default: return <GenericDetail data={stepData.data} />;
    }
  };

  return (
    <div className="h-full flex flex-col bg-white border-l border-gray-200">
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <span className="text-lg">🔬</span>
          <h2 className="font-semibold text-gray-900">步骤{stepData.step}：{stepData.title}</h2>
        </div>
        <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center transition-colors">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M4 4l8 8M12 4l-8 8" />
          </svg>
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-5 py-4">
        {renderContent()}
      </div>
    </div>
  );
}
