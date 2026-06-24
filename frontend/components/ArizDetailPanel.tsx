'use client';

import React, { useState } from 'react';
import { ArizStepData } from './ArizStepCard';

interface ArizDetailPanelProps {
  stepData: ArizStepData;
  onClose: () => void;
  expanded?: boolean;
  onToggleExpand?: () => void;
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
  const supersystemComponents: any[] = data.supersystem_components || [];
  const userAdded: any[] = data.user_added || [];

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
      // 兼容字符串和对象格式
      const name = typeof raw === 'string' ? raw : raw.name;
      const funcs = typeof raw === 'string' ? [] : (raw.functions || []);
      result.push({ name, functions: funcs, description: '超系统组件', isFromDb: false, isSuper: true });
    }
    for (const raw of userAdded) {
      const name = typeof raw === 'string' ? raw : raw.name;
      const funcs = typeof raw === 'string' ? [] : (raw.functions || []);
      result.push({ name, functions: funcs, description: '用户补充', isFromDb: false, isSuper: false });
    }
    return result;
  });

  const [newCompName, setNewCompName] = useState('');
  const [showAdd, setShowAdd] = useState(false);

  const handleDelete = (index: number) => {
    setComponents((prev: any[]) => prev.filter((_: any, i: number) => i !== index));
  };

  const updateFunctions = (index: number, funcsStr: string) => {
    setComponents((prev: any[]) => prev.map((c: any, i: number) =>
      i === index ? { ...c, functions: funcsStr.split(/[、,，]/).map((s: string) => s.trim()).filter(Boolean) } : c
    ));
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
                <td className="py-2.5 text-gray-600">
                  {comp.isFromDb ? (
                    funcs || <span className="text-gray-400">—</span>
                  ) : (
                    <input
                      value={funcs}
                      onChange={(e) => updateFunctions(i, e.target.value)}
                      placeholder="输入功能，用顿号分隔"
                      className="w-full text-sm text-gray-600 bg-transparent border-none p-0 focus:outline-none focus:ring-0 placeholder:text-gray-300"
                    />
                  )}
                </td>
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
  const contacts: any[] = data.contacts || [];
  const allComponents: string[] = data.all_components || [];

  // 构建接触集合（双向）
  const contactSet = new Set<string>();
  for (const c of contacts) {
    contactSet.add(`${c.component_a}||${c.component_b}`);
    contactSet.add(`${c.component_b}||${c.component_a}`);
  }

  // 如果没有 all_components，从 contacts 提取唯一组件名
  const components = allComponents.length > 0
    ? allComponents
    : [...new Set(contacts.flatMap((c: any) => [c.component_a, c.component_b]))];

  if (components.length === 0) {
    return <p className="text-sm text-gray-400">暂无组件数据</p>;
  }

  // 组件名截断（矩阵列头空间有限）
  const trunc = (name: string) => name.length > 6 ? name.slice(0, 6) + '…' : name;

  return (
    <div>
      <Label text="组件互相作用分析" />
      <div className="overflow-x-auto mt-2">
        <table className="text-xs border-collapse">
          <thead>
            <tr>
              <th className="py-2 px-2 font-medium text-gray-600 text-left border-b border-gray-200"></th>
              {components.map((name: string, i: number) => (
                <th key={i} className="py-2 px-2 font-medium text-gray-600 text-center border-b border-gray-200 min-w-[72px]">
                  {trunc(name)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {components.map((rowName: string, ri: number) => (
              <tr key={ri}>
                <td className="py-2 px-2 font-medium text-gray-700 text-left border-b border-gray-100 whitespace-nowrap">
                  {rowName}
                </td>
                {components.map((colName: string, ci: number) => {
                  if (ri === ci) {
                    return <td key={ci} className="py-2 px-2 text-center border-b border-gray-100 bg-gray-50"></td>;
                  }
                  const inContact = contactSet.has(`${rowName}||${colName}`);
                  return (
                    <td key={ci} className="py-2 px-2 text-center border-b border-gray-100">
                      {inContact
                        ? <span className="text-emerald-600 font-medium">接触(+)</span>
                        : <span className="text-gray-400">不接触(-)</span>
                      }
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ========== Step 4: 功能建模 ==========
function Step4Detail({ data }: { data: any }) {
  const typeConfig: Record<string, { label: string; color: string }> = {
    useful:       { label: '有益功能', color: 'bg-blue-50 text-blue-700 border-blue-200' },
    insufficient: { label: '不足功能', color: 'bg-gray-100 text-gray-600 border-gray-200' },
    excessive:    { label: '过度功能', color: 'bg-orange-50 text-orange-700 border-orange-200' },
    harmful:      { label: '有害功能', color: 'bg-red-50 text-red-700 border-red-200' },
  };

  const [functions, setFunctions] = useState<any[]>(() => data.functions || []);
  const [showAdd, setShowAdd] = useState(false);
  const [newFn, setNewFn] = useState({ source: '', target: '', function: '', type: 'useful' });

  const handleDelete = (index: number) => {
    setFunctions(prev => prev.filter((_: any, i: number) => i !== index));
  };

  const handleAdd = () => {
    if (!newFn.source.trim() || !newFn.target.trim() || !newFn.function.trim()) return;
    setFunctions(prev => [...prev, { ...newFn }]);
    setNewFn({ source: '', target: '', function: '', type: 'useful' });
    setShowAdd(false);
  };

  const updateField = (index: number, field: string, value: string) => {
    setFunctions(prev => prev.map((f: any, i: number) => i === index ? { ...f, [field]: value } : f));
  };

  return (
    <div>
      <Label text={`功能模型（${functions.length}条）`} />
      <table className="w-full text-sm mt-2 table-fixed">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-2.5 font-medium text-gray-600 w-[18%]">作用者</th>
            <th className="text-left py-2.5 font-medium text-gray-600 w-[18%]">作用对象</th>
            <th className="text-left py-2.5 font-medium text-gray-600 w-[36%]">功能</th>
            <th className="text-left py-2.5 font-medium text-gray-600 w-[18%]">功能类型</th>
            <th className="text-right py-2.5 font-medium text-gray-600 w-[10%]">操作</th>
          </tr>
        </thead>
        <tbody>
          {functions.map((f: any, i: number) => {
            const cfg = typeConfig[f.type] || typeConfig.useful;
            return (
              <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-2.5 overflow-hidden">
                  <input value={f.source} onChange={(e) => updateField(i, 'source', e.target.value)}
                    className="w-full text-sm text-gray-900 bg-transparent border-none p-0 focus:outline-none truncate" />
                </td>
                <td className="py-2.5 overflow-hidden">
                  <input value={f.target} onChange={(e) => updateField(i, 'target', e.target.value)}
                    className="w-full text-sm text-gray-600 bg-transparent border-none p-0 focus:outline-none truncate" />
                </td>
                <td className="py-2.5 overflow-hidden">
                  <input value={f.function} onChange={(e) => updateField(i, 'function', e.target.value)}
                    className="w-full text-sm text-gray-900 bg-transparent border-none p-0 focus:outline-none truncate" />
                </td>
                <td className="py-2.5">
                  <select value={f.type} onChange={(e) => updateField(i, 'type', e.target.value)}
                    className={`text-xs px-2.5 py-1 rounded-full border font-medium ${cfg.color} focus:outline-none cursor-pointer`}>
                    {Object.entries(typeConfig).map(([k, v]) => (
                      <option key={k} value={k}>{v.label}</option>
                    ))}
                  </select>
                </td>
                <td className="py-2.5 text-right">
                  <button onClick={() => handleDelete(i)} className="text-xs text-red-500 hover:text-red-700 transition-colors">删除</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {showAdd ? (
        <div className="mt-3 grid grid-cols-4 gap-2 items-end">
          <input value={newFn.source} onChange={(e) => setNewFn(p => ({ ...p, source: e.target.value }))}
            placeholder="作用者" className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <input value={newFn.target} onChange={(e) => setNewFn(p => ({ ...p, target: e.target.value }))}
            placeholder="作用对象" className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <input value={newFn.function} onChange={(e) => setNewFn(p => ({ ...p, function: e.target.value }))}
            placeholder="功能" className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <div className="flex gap-2">
            <select value={newFn.type} onChange={(e) => setNewFn(p => ({ ...p, type: e.target.value }))}
              className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none">
              {Object.entries(typeConfig).map(([k, v]) => (
                <option key={k} value={k}>{v.label}</option>
              ))}
            </select>
          </div>
          <div className="col-span-4 flex gap-2 mt-1">
            <button onClick={handleAdd} className="text-sm text-blue-600 hover:text-blue-800 font-medium">确认</button>
            <button onClick={() => { setShowAdd(false); setNewFn({ source: '', target: '', function: '', type: 'useful' }); }} className="text-sm text-gray-500 hover:text-gray-700">取消</button>
          </div>
        </div>
      ) : (
        <button onClick={() => setShowAdd(true)} className="mt-3 text-sm text-blue-600 hover:text-blue-800 font-medium">+ 新增</button>
      )}
    </div>
  );
}

// ========== Step 5: 系统结构分析（网络图） ==========

/**
 * 层次布局算法（Sugiyama 风格）
 * 1. 分层：BFS 从入度为 0 的节点开始分配层级
 * 2. 层内排序：减少交叉
 * 3. 坐标计算：每层居中排列
 */
function hierarchicalLayout(
  nodeNames: string[],
  edges: Array<{ source: string; target: string }>,
  nodeW: number, nodeH: number, padding: number,
) {
  const n = nodeNames.length;
  if (n === 0) return { positions: {}, width: 0, height: 0 };

  // 建邻接表
  const outMap = new Map<string, Set<string>>();
  const inMap = new Map<string, Set<string>>();
  nodeNames.forEach(name => { outMap.set(name, new Set()); inMap.set(name, new Set()); });
  edges.forEach(e => {
    outMap.get(e.source)?.add(e.target);
    inMap.get(e.target)?.add(e.source);
  });

  // 1. BFS 分层（从入度为 0 的节点开始）
  const layer = new Map<string, number>();
  const queue: string[] = [];
  nodeNames.forEach(name => {
    if (inMap.get(name)!.size === 0) {
      layer.set(name, 0);
      queue.push(name);
    }
  });
  // 孤立节点（无入边无出边）放入第 0 层
  nodeNames.forEach(name => {
    if (inMap.get(name)!.size === 0 && outMap.get(name)!.size === 0 && !layer.has(name)) {
      layer.set(name, 0);
      queue.push(name);
    }
  });
  // 如果所有节点都有入边（有环），从度最高的节点开始
  if (queue.length === 0) {
    const sorted = [...nodeNames].sort((a, b) =>
      (outMap.get(b)!.size + inMap.get(b)!.size) - (outMap.get(a)!.size + inMap.get(a)!.size)
    );
    layer.set(sorted[0], 0);
    queue.push(sorted[0]);
  }

  let head = 0;
  while (head < queue.length) {
    const cur = queue[head++];
    const curLayer = layer.get(cur)!;
    for (const next of outMap.get(cur)!) {
      if (!layer.has(next)) {
        layer.set(next, curLayer + 1);
        queue.push(next);
      }
    }
  }
  // 未访问的节点
  nodeNames.forEach(name => {
    if (!layer.has(name)) layer.set(name, 0);
  });

  // 2. 按层分组
  const maxLayer = Math.max(...layer.values());
  const layers: string[][] = [];
  for (let i = 0; i <= maxLayer; i++) layers.push([]);
  nodeNames.forEach(name => layers[layer.get(name)!].push(name));

  // 3. 层内排序：尽量让相连的节点靠近
  for (let i = 1; i < layers.length; i++) {
    layers[i].sort((a, b) => {
      const aParents = Array.from(inMap.get(a)!);
      const bParents = Array.from(inMap.get(b)!);
      const aAvgParentPos = aParents.length > 0
        ? aParents.reduce((s, p) => s + (layers[i - 1].indexOf(p) >= 0 ? layers[i - 1].indexOf(p) : 0), 0) / aParents.length
        : 0;
      const bAvgParentPos = bParents.length > 0
        ? bParents.reduce((s, p) => s + (layers[i - 1].indexOf(p) >= 0 ? layers[i - 1].indexOf(p) : 0), 0) / bParents.length
        : 0;
      return aAvgParentPos - bAvgParentPos;
    });
  }

  // 4. 计算坐标
  const gapX = 120, gapY = 100;
  const pos: Record<string, { x: number; y: number }> = {};

  layers.forEach((layerNodes, layerIdx) => {
    const count = layerNodes.length;
    const totalWidth = count * nodeW + (count - 1) * gapX;
    const startX = (padding * 2 + Math.max(...layers.map(l => l.length)) * (nodeW + gapX) - gapX - totalWidth) / 2;
    layerNodes.forEach((name, colIdx) => {
      pos[name] = {
        x: Math.max(padding, startX + colIdx * (nodeW + gapX) + nodeW / 2),
        y: padding + layerIdx * (nodeH + gapY) + nodeH / 2,
      };
    });
  });

  const rows = layers.length;
  const maxColsInAnyLayer = Math.max(...layers.map(l => l.length));
  const width = padding * 2 + maxColsInAnyLayer * nodeW + (maxColsInAnyLayer - 1) * gapX;
  const height = padding * 2 + rows * nodeH + (rows - 1) * gapY;

  return { positions: pos, width, height };
}

/** 截断标签 */
function truncateLabel(text: string, maxLen: number = 5): string {
  if (!text) return '';
  const cleaned = text.replace(/[（(].*?[）)]/g, '').trim();
  return cleaned.length > maxLen ? cleaned.slice(0, maxLen) + '…' : cleaned;
}


function Step5Detail({ data }: { data: any }) {
  const functions: any[] = data.functions || [];
  const keyProblems: any[] = data.key_problems || [];

  const typeConfig: Record<string, { label: string; color: string }> = {
    useful:       { label: '有益功能', color: 'bg-blue-50 text-blue-700 border-blue-200' },
    insufficient: { label: '不足功能', color: 'bg-gray-100 text-gray-600 border-gray-200' },
    excessive:    { label: '过度功能', color: 'bg-orange-50 text-orange-700 border-orange-200' },
    harmful:      { label: '有害功能', color: 'bg-red-50 text-red-700 border-red-200' },
  };

  const severityConfig: Record<string, { label: string; color: string }> = {
    high:   { label: '严重', color: 'bg-red-50 text-red-700 border-red-200' },
    medium: { label: '中等', color: 'bg-orange-50 text-orange-700 border-orange-200' },
    low:    { label: '轻微', color: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
  };

  const keyProblemNodes = new Set(keyProblems.map((p: any) => p.node));

  // 提取唯一节点
  const nodeSet = new Set<string>();
  functions.forEach(f => { nodeSet.add(f.source); nodeSet.add(f.target); });
  const nodeNames = Array.from(nodeSet);

  const nodeW = 130, nodeH = 38;

  // 层次布局
  const { positions: nodePositions, width: W, height: H } = React.useMemo(
    () => hierarchicalLayout(nodeNames, functions, nodeW, nodeH, 60),
    [nodeNames.join(','), functions.length],
  );

  // 边样式
  const edgeStyle: Record<string, { stroke: string; strokeWidth: number; strokeDasharray?: string }> = {
    useful:       { stroke: '#2563eb', strokeWidth: 2 },
    harmful:      { stroke: '#ef4444', strokeWidth: 2.5, strokeDasharray: '8 4' },
    insufficient: { stroke: '#6b7280', strokeWidth: 1.5, strokeDasharray: '6 4' },
    excessive:    { stroke: '#ea580c', strokeWidth: 3 },
  };

  // Hover 状态
  const [hoveredNode, setHoveredNode] = React.useState<string | null>(null);

  // 计算 hover 相关节点和边
  const connectedNodes = React.useMemo(() => {
    if (!hoveredNode) return null;
    const set = new Set<string>([hoveredNode]);
    functions.forEach(f => {
      if (f.source === hoveredNode) set.add(f.target);
      if (f.target === hoveredNode) set.add(f.source);
    });
    return set;
  }, [hoveredNode, functions]);

  // 图例开关
  const [visibleTypes, setVisibleTypes] = React.useState<Record<string, boolean>>({
    useful: true, harmful: true, insufficient: true, excessive: true,
  });
  const toggleType = (t: string) => setVisibleTypes(prev => ({ ...prev, [t]: !prev[t] }));

  // 缩放
  const [zoom, setZoom] = React.useState(1);

  // 过滤后的边
  const visibleEdges = functions.filter((f: any) => visibleTypes[f.type] !== false);

  // 节点和边的透明度
  const nodeOpacity = (name: string) => {
    if (!connectedNodes) return 1;
    return connectedNodes.has(name) ? 1 : 0.15;
  };
  const edgeOpacity = (f: any) => {
    if (!connectedNodes) return 1;
    return connectedNodes.has(f.source) && connectedNodes.has(f.target) ? 1 : 0.08;
  };

  return (
    <div className="space-y-4">
      {/* 网络图 */}
      {nodeNames.length > 0 && (
        <div>
          <div className="flex items-center justify-between">
            <Label text={`系统结构关系图（${nodeNames.length}个组件，${visibleEdges.length}条关系）`} />
            <div className="flex items-center gap-1 text-xs">
              <button onClick={() => setZoom(z => Math.max(0.3, z - 0.15))}
                className="w-7 h-7 rounded border border-gray-300 hover:bg-gray-100 flex items-center justify-center text-gray-600">−</button>
              <span className="w-12 text-center text-gray-500">{Math.round(zoom * 100)}%</span>
              <button onClick={() => setZoom(z => Math.min(3, z + 0.15))}
                className="w-7 h-7 rounded border border-gray-300 hover:bg-gray-100 flex items-center justify-center text-gray-600">+</button>
              <button onClick={() => setZoom(1)}
                className="ml-1 px-2 h-7 rounded border border-gray-300 hover:bg-gray-100 text-gray-600">1:1</button>
            </div>
          </div>
          <div className="mt-2 border border-gray-200 rounded-lg overflow-auto bg-white" style={{ maxHeight: 600 }}>
            <div style={{ transform: `scale(${zoom})`, transformOrigin: 'top left', width: W, height: H }}>
              <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H}>
                <defs>
                  <marker id="arrow" viewBox="0 0 10 6" refX="10" refY="3" markerWidth="8" markerHeight="6" orient="auto">
                    <path d="M0,0 L10,3 L0,6 Z" fill="#94a3b8" />
                  </marker>
                  <marker id="arrow-red" viewBox="0 0 10 6" refX="10" refY="3" markerWidth="8" markerHeight="6" orient="auto">
                    <path d="M0,0 L10,3 L0,6 Z" fill="#ef4444" />
                  </marker>
                  <marker id="arrow-blue" viewBox="0 0 10 6" refX="10" refY="3" markerWidth="8" markerHeight="6" orient="auto">
                    <path d="M0,0 L10,3 L0,6 Z" fill="#2563eb" />
                  </marker>
                  <marker id="arrow-orange" viewBox="0 0 10 6" refX="10" refY="3" markerWidth="8" markerHeight="6" orient="auto">
                    <path d="M0,0 L10,3 L0,6 Z" fill="#ea580c" />
                  </marker>
                </defs>

                {/* 边：直线 + 白底标签 */}
                {visibleEdges.map((f: any, i: number) => {
                  const from = nodePositions[f.source];
                  const to = nodePositions[f.target];
                  if (!from || !to) return null;
                  const style = edgeStyle[f.type] || edgeStyle.useful;
                  const markerId = f.type === 'harmful' ? 'arrow-red' : f.type === 'excessive' ? 'arrow-orange' : f.type === 'useful' ? 'arrow-blue' : 'arrow';

                  const dx = to.x - from.x, dy = to.y - from.y;
                  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                  const shrink = Math.min(70, dist * 0.25);
                  const x1 = from.x + (dx / dist) * shrink;
                  const y1 = from.y + (dy / dist) * shrink;
                  const x2 = to.x - (dx / dist) * shrink;
                  const y2 = to.y - (dy / dist) * shrink;

                  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
                  // 标签偏移到线条侧面
                  const nx = -(dy / dist) * 16, ny = (dx / dist) * 16;
                  const label = truncateLabel(f.function, 5);
                  const op = edgeOpacity(f);

                  return (
                    <g key={`e${i}`} opacity={op} style={{ transition: 'opacity 0.2s' }}>
                      <line x1={x1} y1={y1} x2={x2} y2={y2}
                        stroke={style.stroke} strokeWidth={style.strokeWidth}
                        strokeDasharray={style.strokeDasharray}
                        markerEnd={`url(#${markerId})`} />
                      {/* 白底标签 */}
                      <rect x={mx + nx - 22} y={my + ny - 8} width={44} height={16}
                        rx={3} fill="white" fillOpacity={0.85} />
                      <text x={mx + nx} y={my + ny} textAnchor="middle" dominantBaseline="middle"
                        className="fill-gray-600" style={{ fontSize: 9, fontWeight: 500 }}>{label}</text>
                    </g>
                  );
                })}

                {/* 节点 */}
                {nodeNames.map((name) => {
                  const pos = nodePositions[name];
                  if (!pos) return null;
                  const isKey = keyProblemNodes.has(name);
                  const op = nodeOpacity(name);
                  return (
                    <g key={`n${name}`} opacity={op} style={{ transition: 'opacity 0.2s' }}
                      onMouseEnter={() => setHoveredNode(name)}
                      onMouseLeave={() => setHoveredNode(null)}
                      className="cursor-pointer">
                      <rect x={pos.x - nodeW / 2} y={pos.y - nodeH / 2} width={nodeW} height={nodeH}
                        rx={8} ry={8}
                        fill={isKey ? '#fef2f2' : '#f8fafc'}
                        stroke={isKey ? '#ef4444' : hoveredNode === name ? '#3b82f6' : '#cbd5e1'}
                        strokeWidth={isKey ? 2.5 : hoveredNode === name ? 2.5 : 1} />
                      <text x={pos.x} y={pos.y + 1} textAnchor="middle" dominantBaseline="middle"
                        className={`font-medium ${isKey ? 'fill-red-700' : 'fill-gray-800'}`}
                        style={{ fontSize: 11 }}>
                        {name}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
          </div>
          {/* 图例 */}
          <div className="flex flex-wrap gap-3 mt-2">
            {Object.entries(typeConfig).map(([k, v]) => {
              const visible = visibleTypes[k] !== false;
              return (
                <button key={k} onClick={() => toggleType(k)}
                  className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border transition-opacity ${visible ? 'opacity-100' : 'opacity-40'}`}
                  style={{ borderColor: k === 'useful' ? '#2563eb' : k === 'harmful' ? '#ef4444' : k === 'excessive' ? '#ea580c' : '#6b7280' }}>
                  <span className="w-4 h-0.5 inline-block"
                    style={{
                      borderTop: k === 'harmful' || k === 'insufficient' ? `2px dashed ${k === 'harmful' ? '#ef4444' : '#6b7280'}` : k === 'excessive' ? '3px solid #ea580c' : '2px solid #2563eb',
                    }} />
                  <span className="text-gray-700">{v.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ========== 通用详情（Step 6-9） ==========
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
export default function ArizDetailPanel({ stepData, onClose, expanded, onToggleExpand }: ArizDetailPanelProps) {
  const renderContent = () => {
    switch (stepData.step) {
      case 1: return <Step1Detail data={stepData.data} />;
      case 2: return <Step2Detail data={stepData.data} />;
      case 3: return <Step3Detail data={stepData.data} />;
      case 4: return <Step4Detail data={stepData.data} />;
      case 5: return <Step5Detail data={stepData.data} />;
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
        <div className="flex items-center gap-1">
          {onToggleExpand && (
            <button
              onClick={onToggleExpand}
              className="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center transition-colors"
              title={expanded ? '退出全屏' : '全屏显示'}
            >
              {expanded ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M8 3v3a2 2 0 01-2 2H3m18 0h-3a2 2 0 01-2-2V3m0 18v-3a2 2 0 012-2h3M3 16h3a2 2 0 012 2v3"/>
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M8 3H5a2 2 0 00-2 2v3m21 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3"/>
                </svg>
              )}
            </button>
          )}
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-gray-100 flex items-center justify-center transition-colors">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M4 4l8 8M12 4l-8 8" />
            </svg>
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-5 py-4">
        {renderContent()}
      </div>
    </div>
  );
}
