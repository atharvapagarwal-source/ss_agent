'use client';

import React from 'react';
import {
  Bell,
  RefreshCw,
  Search,
  Sparkles,
  ChevronDown,
  ExternalLink,
  ShieldCheck,
} from 'lucide-react';

interface TopBarProps {
  onTriggerPipeline: () => void;
  isPipelineRunning: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  onTriggerPipeline,
  isPipelineRunning,
}) => {
  return (
    <header className="h-16 border-b border-slate-800/80 bg-[#0c101c]/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Search and context */}
      <div className="flex items-center gap-4 w-96">
        <div className="relative w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search posts, leads, keyword triggers, trends..."
            className="w-full bg-slate-900/80 border border-slate-800 text-xs rounded-xl pl-9 pr-4 py-2 text-slate-200 placeholder-slate-400 focus:outline-none focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/40 transition-all"
          />
        </div>
      </div>

      {/* Action controls & Coach Profile */}
      <div className="flex items-center gap-3">
        {/* Trigger 4-Agent Pipeline Button */}
        <button
          onClick={onTriggerPipeline}
          disabled={isPipelineRunning}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-xs font-bold transition-all shadow-md shadow-violet-600/20 active:scale-95 disabled:opacity-50"
        >
          {isPipelineRunning ? (
            <>
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>Agents Researching & Drafting...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
              <span>Run Autonomous Pipeline</span>
            </>
          )}
        </button>

        {/* Live SSE / Webhook Status */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/90 border border-slate-800 text-[11px] text-slate-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>Webhooks SSE Active</span>
        </div>

        {/* Notification Bell */}
        <button className="relative p-2 rounded-xl bg-slate-900/80 border border-slate-800 text-slate-400 hover:text-slate-200 transition-colors">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500" />
        </button>

        {/* Coach Profile */}
        <div className="flex items-center gap-3 pl-3 border-l border-slate-800">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-violet-500 to-pink-500 flex items-center justify-center text-white font-bold text-xs ring-2 ring-slate-800">
            SJ
          </div>
          <div className="hidden lg:block text-left">
            <div className="text-xs font-semibold text-slate-200">Sarah Jenkins</div>
            <div className="text-[10px] text-slate-400">Head Executive Coach</div>
          </div>
        </div>
      </div>
    </header>
  );
};
