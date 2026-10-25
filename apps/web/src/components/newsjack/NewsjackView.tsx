'use client';

import React, { useState } from 'react';
import {
  Radio,
  TrendingUp,
  AlertTriangle,
  Zap,
  ArrowRight,
  ExternalLink,
  Sparkles,
  Flame,
  Clock,
} from 'lucide-react';
import { TrendItem, MOCK_TRENDS } from '@/lib/api';

interface NewsjackViewProps {
  onSelectTrendForPipeline: (trend: TrendItem) => void;
}

export const NewsjackView: React.FC<NewsjackViewProps> = ({ onSelectTrendForPipeline }) => {
  const [trends, setTrends] = useState<TrendItem[]>(MOCK_TRENDS);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            Job Market Newsjack Radar
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30 font-mono font-medium flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-ping" />
              Real-Time Radar
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Agent 1 monitors layoff announcements, Department of Labor statistics, and executive hiring surges to hijack viral career discussions.
          </p>
        </div>

        <div className="text-xs text-slate-400 font-mono bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-xl">
          Poller: <span className="text-emerald-400 font-bold">Every 15 min cron</span>
        </div>
      </div>

      {/* Radar Cards List */}
      <div className="space-y-4">
        {trends.map((trend) => (
          <div
            key={trend.id}
            className="glass-panel p-6 rounded-2xl border border-slate-800 glass-panel-hover flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6"
          >
            {/* Left Content */}
            <div className="space-y-3 flex-1">
              <div className="flex items-center gap-3 flex-wrap">
                <span
                  className={`text-[10px] font-mono font-extrabold px-2.5 py-0.5 rounded-full uppercase ${
                    trend.urgency === 'HIGH'
                      ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                      : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                  }`}
                >
                  {trend.urgency} Urgency
                </span>

                <span className="text-xs text-slate-400 flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" /> {trend.detected_at}
                </span>

                <span className="text-xs text-slate-500">•</span>

                <span className="text-xs text-slate-400">
                  Source: <strong className="text-slate-300">{trend.source}</strong>
                </span>
              </div>

              <h2 className="text-base font-extrabold text-white leading-snug">
                {trend.headline}
              </h2>

              {/* Recommended Strategic Angle */}
              <div className="p-3 rounded-xl bg-violet-950/30 border border-violet-800/30 text-xs text-violet-300 flex items-start gap-2">
                <Sparkles className="w-4 h-4 text-amber-300 flex-shrink-0 mt-0.5" />
                <div>
                  <strong className="text-white">Recommended Coaching Angle:</strong> {trend.recommended_angle}
                </div>
              </div>
            </div>

            {/* Right: Virality Score & 1-Click Action */}
            <div className="flex lg:flex-col items-center lg:items-end justify-between w-full lg:w-auto gap-4 pt-2 lg:pt-0 border-t lg:border-t-0 border-slate-800">
              <div className="text-left lg:text-right">
                <div className="text-[10px] uppercase font-bold text-slate-400 flex items-center gap-1 lg:justify-end">
                  <Flame className="w-3.5 h-3.5 text-rose-500" /> Virality Index
                </div>
                <div className="text-2xl font-black text-rose-400 font-mono">
                  {trend.virality_score} <span className="text-xs text-slate-500 font-normal">/ 100</span>
                </div>
              </div>

              <button
                onClick={() => onSelectTrendForPipeline(trend)}
                className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-xs font-bold transition-all shadow-lg shadow-violet-600/25 flex items-center gap-1.5 active:scale-95"
              >
                <span>Newsjack This Story</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
