'use client';

import React from 'react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Funnel,
  FunnelChart,
  LabelList,
  Cell,
} from 'recharts';
import {
  TrendingUp,
  Users,
  MessageSquare,
  Sparkles,
  Share2,
  ArrowUpRight,
  Send,
  Zap,
  Target,
} from 'lucide-react';
import {
  MOCK_TELEMETRY,
  MOCK_FUNNEL_DATA,
  MOCK_PLATFORM_STATS,
} from '@/lib/api';

const FUNNEL_COLORS = ['#6366F1', '#8B5CF6', '#A855F7', '#EC4899', '#10B981'];

export const AnalyticsView: React.FC = () => {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            Telemetry & Second-Level Analytics
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-mono font-medium flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Live Feed
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time multi-platform reach velocity, Comment-to-DM conversions, and cross-channel engagement telemetry.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 font-mono">
            Window: <span className="text-violet-400 font-bold">Past 24 Hours</span>
          </div>
        </div>
      </div>

      {/* Top Telemetry Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-5 rounded-2xl glass-panel-hover relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">Total Cross-Platform Reach</span>
            <div className="w-8 h-8 rounded-lg bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white tracking-tight">52,600</span>
            <span className="text-xs font-semibold text-emerald-400 flex items-center gap-0.5">
              <ArrowUpRight className="w-3.5 h-3.5" /> +34.2%
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">LinkedIn + Instagram + Twitter + FB</div>
        </div>

        <div className="glass-panel p-5 rounded-2xl glass-panel-hover relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">Comment Inflow & Replies</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <MessageSquare className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white tracking-tight">1,820</span>
            <span className="text-xs font-semibold text-emerald-400 flex items-center gap-0.5">
              <ArrowUpRight className="w-3.5 h-3.5" /> +28.4%
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">100% replied with AI contextual comments</div>
        </div>

        <div className="glass-panel p-5 rounded-2xl glass-panel-hover relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">Automated DMs Dispatched</span>
            <div className="w-8 h-8 rounded-lg bg-pink-500/10 border border-pink-500/20 flex items-center justify-center text-pink-400">
              <Send className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white tracking-tight">1,410</span>
            <span className="text-xs font-semibold text-emerald-400 flex items-center gap-0.5">
              <ArrowUpRight className="w-3.5 h-3.5" /> 96.5% rate
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Jitter rate limiter active (30s–5m)</div>
        </div>

        <div className="glass-panel p-5 rounded-2xl glass-panel-hover relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">High-Ticket Leads Captured</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <Target className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-emerald-400 tracking-tight">894</span>
            <span className="text-xs font-semibold text-emerald-400 flex items-center gap-0.5">
              <ArrowUpRight className="w-3.5 h-3.5" /> 63.4% conv
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Opted into coaching discovery calendar</div>
        </div>
      </div>

      {/* Main Charts Row: Reach Velocity & Conversion Funnel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Reach Velocity Chart (2 cols) */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-400" />
                Live Reach & Comment Velocity (24h)
              </h2>
              <p className="text-xs text-slate-400">
                Shows exponential virality curves from recent newsjack carousel drop.
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-violet-500" /> Reach
              </span>
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-pink-500" /> DMs Sent
              </span>
            </div>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={MOCK_TELEMETRY} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="reachGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="dmGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#EC4899" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#EC4899" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                <XAxis dataKey="hour" stroke="#64748B" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0F172A',
                    borderColor: '#334155',
                    borderRadius: '12px',
                    fontSize: '12px',
                    color: '#F8FAFC',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="reach"
                  stroke="#8B5CF6"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#reachGrad)"
                  name="Reach Velocity"
                />
                <Area
                  type="monotone"
                  dataKey="dmsSent"
                  stroke="#EC4899"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#dmGrad)"
                  name="DMs Dispatched"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Comment-to-DM Conversion Funnel (1 col) */}
        <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Target className="w-4 h-4 text-emerald-400" />
                Comment-to-DM Funnel
              </h2>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Real-time drop-off from post view to verified lead magnet download.
            </p>

            <div className="space-y-3">
              {MOCK_FUNNEL_DATA.map((item, index) => (
                <div key={item.stage} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-semibold text-slate-300">{item.stage}</span>
                    <span className="font-mono font-bold text-white">
                      {item.count.toLocaleString()}
                    </span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.max(12, (item.count / 48600) * 100)}%`,
                        backgroundColor: FUNNEL_COLORS[index],
                      }}
                    />
                  </div>
                  <div className="text-[10px] text-right text-slate-400">
                    Step conversion: <span className="text-slate-300 font-semibold">{item.dropoff}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 p-3 rounded-xl bg-violet-500/10 border border-violet-500/20 text-xs text-violet-300 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-300 flex-shrink-0" />
            <span>Keyword <strong>&quot;RESUME&quot;</strong> drove 68% of all conversions today.</span>
          </div>
        </div>
      </div>

      {/* Platform Breakdown Cards */}
      <div>
        <h2 className="text-sm font-bold text-white mb-3">Cross-Platform Channel Performance</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {MOCK_PLATFORM_STATS.map((plat) => (
            <div key={plat.platform} className="glass-panel p-4 rounded-xl flex items-center justify-between">
              <div>
                <div className="text-xs font-bold text-white">{plat.platform}</div>
                <div className="text-lg font-black text-slate-200 mt-1">
                  {plat.reach.toLocaleString()}{' '}
                  <span className="text-[10px] font-normal text-slate-400">views</span>
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">
                  Leads: <strong className="text-emerald-400">{plat.leads}</strong> ({plat.conversionRate})
                </div>
              </div>
              <div className="w-10 h-10 rounded-xl bg-slate-800/80 border border-slate-700/60 flex items-center justify-center font-bold text-xs text-violet-400">
                {plat.platform.slice(0, 2).toUpperCase()}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
