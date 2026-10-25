'use client';

import React, { useState } from 'react';
import {
  Palette,
  ShieldCheck,
  Key,
  Sliders,
  CheckCircle2,
  ExternalLink,
  Save,
  RefreshCw,
} from 'lucide-react';

export const SettingsView: React.FC = () => {
  const [primaryColor, setPrimaryColor] = useState('#6C63FF');
  const [accentColor, setAccentColor] = useState('#FF6B6B');
  const [headingFont, setHeadingFont] = useState('Plus Jakarta Sans');
  const [coachNiche, setCoachNiche] = useState('Tech Executive & VP Transitions');
  const [minJitter, setMinJitter] = useState(30);
  const [maxJitter, setMaxJitter] = useState(300);
  const [hourlyCap, setHourlyCap] = useState(45);
  const [savedNotice, setSavedNotice] = useState(false);

  const handleSave = () => {
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 3000);
  };

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            Brand Kit & Multi-Tenant Settings
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Configure dynamic carousel brand tokens, OAuth platform connections, and Comment-to-DM anti-ban rate limiters.
          </p>
        </div>

        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold transition-all shadow-md shadow-violet-600/20 active:scale-95 self-start sm:self-auto"
        >
          <Save className="w-3.5 h-3.5" />
          <span>Save Changes</span>
        </button>
      </div>

      {savedNotice && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2 animate-fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>Brand profile and rate limiter settings saved to tenant database!</span>
        </div>
      )}

      {/* Brand Kit Card */}
      <div className="glass-panel p-6 rounded-2xl space-y-4">
        <h2 className="text-sm font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
          <Palette className="w-4 h-4 text-violet-400" />
          Dynamic Slide & Carousel Brand Profile
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-[11px] font-semibold text-slate-400 block mb-1">
              Primary Brand Accent (Hex)
            </label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={primaryColor}
                onChange={(e) => setPrimaryColor(e.target.value)}
                className="w-9 h-9 rounded-lg border border-slate-700 bg-transparent cursor-pointer"
              />
              <input
                type="text"
                value={primaryColor}
                onChange={(e) => setPrimaryColor(e.target.value)}
                className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200"
              />
            </div>
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-400 block mb-1">
              Secondary Contrast Accent (Hex)
            </label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={accentColor}
                onChange={(e) => setAccentColor(e.target.value)}
                className="w-9 h-9 rounded-lg border border-slate-700 bg-transparent cursor-pointer"
              />
              <input
                type="text"
                value={accentColor}
                onChange={(e) => setAccentColor(e.target.value)}
                className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200"
              />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
          <div>
            <label className="text-[11px] font-semibold text-slate-400 block mb-1">
              Coaching Specialization / Niche
            </label>
            <input
              type="text"
              value={coachNiche}
              onChange={(e) => setCoachNiche(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-200"
            />
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-400 block mb-1">
              Typography Font Family
            </label>
            <select
              value={headingFont}
              onChange={(e) => setHeadingFont(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-200"
            >
              <option value="Plus Jakarta Sans">Plus Jakarta Sans (Modern Executive)</option>
              <option value="Inter">Inter (Clean Corporate)</option>
              <option value="Outfit">Outfit (Vibrant Bold)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Platform OAuth Connections */}
      <div className="glass-panel p-6 rounded-2xl space-y-4">
        <h2 className="text-sm font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          Platform OAuth Connections (AES-256 Vault Encrypted)
        </h2>

        <div className="space-y-3">
          {[
            {
              platform: 'LinkedIn API v2',
              account: 'Sarah Jenkins (linkedin.com/in/sarahjenkins-coach)',
              status: 'CONNECTED',
              permissions: 'w_member_social, r_basicprofile, direct_messages',
            },
            {
              platform: 'Meta Graph API (Instagram + FB)',
              account: '@sarahjenkins.executive (IG Business)',
              status: 'CONNECTED',
              permissions: 'instagram_manage_comments, instagram_manage_messages',
            },
            {
              platform: 'X / Twitter API v2',
              account: '@sarah_coaches (Verified Org)',
              status: 'CONNECTED',
              permissions: 'tweet.read, tweet.write, dm.write',
            },
          ].map((item) => (
            <div
              key={item.platform}
              className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-white">{item.platform}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-bold">
                    {item.status}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 mt-1">{item.account}</div>
                <div className="text-[10px] text-slate-500 font-mono mt-0.5">Scopes: {item.permissions}</div>
              </div>

              <button className="text-xs text-slate-400 hover:text-rose-400 transition-colors font-medium">
                Disconnect
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Jitter Rate Limiter Controls */}
      <div className="glass-panel p-6 rounded-2xl space-y-4">
        <h2 className="text-sm font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
          <Sliders className="w-4 h-4 text-pink-400" />
          DM Jitter & Anti-Detection Automation Settings
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="text-[11px] font-semibold text-slate-400 block mb-1">
              Min Jitter Delay (Seconds)
            </label>
            <input
              type="number"
              value={minJitter}
              onChange={(e) => setMinJitter(Number(e.target.value))}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-200"
            />
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-400 block mb-1">
              Max Jitter Delay (Seconds)
            </label>
            <input
              type="number"
              value={maxJitter}
              onChange={(e) => setMaxJitter(Number(e.target.value))}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-200"
            />
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-400 block mb-1">
              Max Hourly Cap (Per Tenant)
            </label>
            <input
              type="number"
              value={hourlyCap}
              onChange={(e) => setHourlyCap(Number(e.target.value))}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-200"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
