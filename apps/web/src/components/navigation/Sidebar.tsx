'use client';

import React from 'react';
import {
  BarChart3,
  CheckSquare,
  Sparkles,
  Users2,
  Radio,
  Settings,
  Layers,
  Bot,
  Zap,
} from 'lucide-react';

export type ActiveTab = 'analytics' | 'hitl' | 'studio' | 'leads' | 'newsjack' | 'settings';

interface SidebarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  pendingHitlCount: number;
  urgentNewsjackCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  pendingHitlCount,
  urgentNewsjackCount,
}) => {
  const navItems = [
    {
      id: 'analytics' as ActiveTab,
      label: 'Telemetry & Analytics',
      icon: BarChart3,
      badge: null,
      desc: 'Reach velocity & conversion funnels',
    },
    {
      id: 'hitl' as ActiveTab,
      label: 'HITL Review Queue',
      icon: CheckSquare,
      badge: pendingHitlCount > 0 ? pendingHitlCount : null,
      badgeColor: 'bg-amber-500 text-black',
      desc: 'Human approval & slide diffing',
    },
    {
      id: 'studio' as ActiveTab,
      label: 'Autonomous Studio',
      icon: Sparkles,
      badge: null,
      desc: '4-Agent generation radar',
    },
    {
      id: 'newsjack' as ActiveTab,
      label: 'Job Newsjack Radar',
      icon: Radio,
      badge: urgentNewsjackCount > 0 ? `${urgentNewsjackCount} Urgent` : null,
      badgeColor: 'bg-rose-500 text-white animate-pulse',
      desc: 'Real-time layoff & hiring alerts',
    },
    {
      id: 'leads' as ActiveTab,
      label: 'Comment-to-DM CRM',
      icon: Users2,
      badge: null,
      desc: 'Captured leads & DM automation',
    },
    {
      id: 'settings' as ActiveTab,
      label: 'Brand Kit & Integrations',
      icon: Settings,
      badge: null,
      desc: 'Multi-tenant colors & OAuth',
    },
  ];

  return (
    <aside className="w-72 bg-[#0c101c] border-r border-slate-800/80 flex flex-col justify-between select-none">
      <div>
        {/* App Branding */}
        <div className="p-6 border-b border-slate-800/60 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-violet-600 via-indigo-500 to-fuchsia-500 flex items-center justify-center shadow-lg shadow-violet-500/20">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-extrabold text-base tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent flex items-center gap-2">
              SocialCoach <span className="text-xs px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-400 font-mono font-semibold">AI</span>
            </div>
            <div className="text-[11px] text-slate-400 font-medium">Autonomous SaaS for Coaches</div>
          </div>
        </div>

        {/* Tenant Active Indicator */}
        <div className="mx-4 my-4 p-3 rounded-xl bg-slate-900/90 border border-slate-800 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-xs">
            SJ
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-slate-200 truncate">Sarah Jenkins Coaching</div>
            <div className="text-[10px] text-emerald-400 flex items-center gap-1 font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Enterprise Active
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <div className="px-3 space-y-1 mt-2">
          <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Agent Operations
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full group flex items-center justify-between px-3.5 py-2.5 rounded-xl text-left transition-all duration-200 ${
                  isActive
                    ? 'bg-violet-600/15 border border-violet-500/40 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Icon
                    className={`w-4 h-4 transition-colors ${
                      isActive ? 'text-violet-400' : 'text-slate-400 group-hover:text-slate-300'
                    }`}
                  />
                  <div className="truncate">
                    <div className="text-xs font-semibold leading-tight">{item.label}</div>
                  </div>
                </div>

                {item.badge && (
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      item.badgeColor || 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* System Status Footbar */}
      <div className="p-4 m-3 rounded-xl bg-gradient-to-br from-slate-900/90 to-slate-950 border border-slate-800/80">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-semibold text-slate-300 flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-amber-400" /> LangGraph Agents
          </span>
          <span className="text-[10px] text-emerald-400 font-mono font-medium">4 / 4 Healthy</span>
        </div>
        <div className="grid grid-cols-4 gap-1 text-center font-mono text-[9px] text-slate-400">
          <div className="bg-slate-800/60 py-1 rounded" title="Trend Hunter: Active">Ag-1</div>
          <div className="bg-slate-800/60 py-1 rounded" title="Content Creator: Active">Ag-2</div>
          <div className="bg-slate-800/60 py-1 rounded" title="Critic / HITL: Active">Ag-3</div>
          <div className="bg-slate-800/60 py-1 rounded" title="Comment-to-DM: Active">Ag-4</div>
        </div>
      </div>
    </aside>
  );
};
