'use client';

import React, { useState } from 'react';
import {
  Users2,
  Download,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  Send,
  ExternalLink,
  Tag,
  ArrowUpDown,
  Sparkles,
} from 'lucide-react';
import { LeadItem, MOCK_LEADS } from '@/lib/api';

export const LeadsCrmView: React.FC = () => {
  const [leads, setLeads] = useState<LeadItem[]>(MOCK_LEADS);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedKeyword, setSelectedKeyword] = useState<string>('ALL');
  const [selectedPlatform, setSelectedPlatform] = useState<string>('ALL');

  const filteredLeads = leads.filter((lead) => {
    const matchesSearch =
      lead.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
      lead.post_topic.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesKeyword =
      selectedKeyword === 'ALL' || lead.keyword_triggered === selectedKeyword;
    const matchesPlatform =
      selectedPlatform === 'ALL' || lead.platform === selectedPlatform;
    return matchesSearch && matchesKeyword && matchesPlatform;
  });

  const exportCSV = () => {
    const headers = 'ID,Username,Platform,Keyword,Status,SentAt,PostTopic\n';
    const rows = filteredLeads
      .map(
        (l) =>
          `"${l.id}","${l.username}","${l.platform}","${l.keyword_triggered}","${l.dm_status}","${l.sent_at}","${l.post_topic.replace(/"/g, '""')}"`
      )
      .join('\n');
    const blob = new Blob([headers + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `socialcoach-leads-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            Comment-to-DM Lead CRM
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-pink-500/10 text-pink-400 border border-pink-500/30 font-mono font-medium">
              {leads.length} Warm Leads Captured
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Autonomous inbound leads generated from comment trigger keywords. Monitored, rate-limited, and delivered automatically.
          </p>
        </div>

        <button
          onClick={exportCSV}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold border border-slate-700 transition-colors self-start sm:self-auto"
        >
          <Download className="w-3.5 h-3.5 text-violet-400" />
          <span>Export CRM as CSV</span>
        </button>
      </div>

      {/* CRM Filter Controls */}
      <div className="glass-panel p-4 rounded-2xl flex flex-col md:flex-row items-center gap-4">
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search leads by username or topic..."
            className="w-full bg-slate-900 border border-slate-800 text-xs rounded-xl pl-9 pr-3 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500"
          />
        </div>

        {/* Keyword Filter */}
        <div className="flex items-center gap-2 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
          <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
            <Tag className="w-3.5 h-3.5" /> Trigger:
          </span>
          {['ALL', 'RESUME', 'GUIDE', 'OFFER'].map((kw) => (
            <button
              key={kw}
              onClick={() => setSelectedKeyword(kw)}
              className={`text-[11px] px-2.5 py-1 rounded-lg font-mono font-bold transition-colors ${
                selectedKeyword === kw
                  ? 'bg-violet-600 text-white'
                  : 'bg-slate-900 text-slate-400 hover:bg-slate-800'
              }`}
            >
              {kw}
            </button>
          ))}
        </div>

        {/* Platform Filter */}
        <div className="flex items-center gap-2 w-full md:w-auto overflow-x-auto pb-1 md:pb-0 md:ml-auto">
          <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" /> Platform:
          </span>
          {['ALL', 'linkedin', 'instagram', 'twitter'].map((plat) => (
            <button
              key={plat}
              onClick={() => setSelectedPlatform(plat)}
              className={`text-[11px] px-2.5 py-1 rounded-lg capitalize transition-colors ${
                selectedPlatform === plat
                  ? 'bg-violet-600 text-white'
                  : 'bg-slate-900 text-slate-400 hover:bg-slate-800'
              }`}
            >
              {plat}
            </button>
          ))}
        </div>
      </div>

      {/* Leads Table */}
      <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800 text-[11px] uppercase tracking-wider font-semibold">
              <tr>
                <th className="py-3.5 px-4">Lead Profile</th>
                <th className="py-3.5 px-4">Platform</th>
                <th className="py-3.5 px-4">Keyword Match</th>
                <th className="py-3.5 px-4">DM Dispatch Status</th>
                <th className="py-3.5 px-4">Origin Post</th>
                <th className="py-3.5 px-4 text-right">Sent Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredLeads.map((lead) => (
                <tr key={lead.id} className="hover:bg-slate-800/30 transition-colors">
                  {/* Lead Profile */}
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center font-bold text-white text-[10px]">
                        {lead.username.slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <div className="font-semibold text-slate-200">@{lead.username}</div>
                        <a
                          href={lead.lead_magnet_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[10px] text-violet-400 hover:underline flex items-center gap-1"
                        >
                          Asset delivered <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      </div>
                    </div>
                  </td>

                  {/* Platform */}
                  <td className="py-3.5 px-4">
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300 capitalize">
                      {lead.platform}
                    </span>
                  </td>

                  {/* Keyword */}
                  <td className="py-3.5 px-4">
                    <span className="text-xs font-mono font-bold text-violet-400 bg-violet-500/10 border border-violet-500/20 px-2 py-0.5 rounded">
                      &quot;{lead.keyword_triggered}&quot;
                    </span>
                  </td>

                  {/* Status Badge */}
                  <td className="py-3.5 px-4">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full inline-flex items-center gap-1 ${
                        lead.dm_status === 'CONVERTED'
                          ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                          : lead.dm_status === 'DELIVERED'
                          ? 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/30'
                          : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                      }`}
                    >
                      {lead.dm_status === 'CONVERTED' && <CheckCircle2 className="w-3 h-3" />}
                      {lead.dm_status === 'DELIVERED' && <Send className="w-3 h-3" />}
                      {lead.dm_status === 'SENT' && <Clock className="w-3 h-3" />}
                      {lead.dm_status}
                    </span>
                  </td>

                  {/* Post Topic */}
                  <td className="py-3.5 px-4 text-slate-300 max-w-xs truncate">
                    {lead.post_topic}
                  </td>

                  {/* Sent Time */}
                  <td className="py-3.5 px-4 text-right text-slate-400 font-mono text-[11px]">
                    {lead.sent_at}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
