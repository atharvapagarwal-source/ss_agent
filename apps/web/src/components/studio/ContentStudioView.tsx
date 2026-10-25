'use client';

import React, { useState } from 'react';
import {
  Sparkles,
  Bot,
  Layers,
  ArrowRight,
  CheckCircle,
  Clock,
  Send,
  FileText,
  Sliders,
  Play,
  RotateCw,
} from 'lucide-react';

interface ContentStudioViewProps {
  onPostCreated?: () => void;
}

export const ContentStudioView: React.FC<ContentStudioViewProps> = ({ onPostCreated }) => {
  const [topicPrompt, setTopicPrompt] = useState(
    'How to transition from Senior Software Engineer to Engineering Manager in 6 months without taking a pay cut'
  );
  const [leadMagnetKeyword, setLeadMagnetKeyword] = useState('MANAGER');
  const [leadMagnetName, setLeadMagnetName] = useState('EM Transition Roadmap 2026.pdf');
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['linkedin', 'instagram', 'twitter']);
  const [isGenerating, setIsGenerating] = useState(false);
  const [pipelineStep, setPipelineStep] = useState<number>(0);
  const [generatedSuccess, setGeneratedSuccess] = useState(false);

  const togglePlatform = (p: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(p) ? prev.filter((item) => item !== p) : [...prev, p]
    );
  };

  const handleRunPipeline = () => {
    setIsGenerating(true);
    setGeneratedSuccess(false);
    setPipelineStep(1);

    // Simulate agent steps with realistic progress
    setTimeout(() => setPipelineStep(2), 1200);
    setTimeout(() => setPipelineStep(3), 2600);
    setTimeout(() => setPipelineStep(4), 3800);
    setTimeout(() => {
      setIsGenerating(false);
      setPipelineStep(5);
      setGeneratedSuccess(true);
      if (onPostCreated) onPostCreated();
    }, 5000);
  };

  const samplePrompts = [
    'How to negotiate a $35,000 equity increase after a successful performance review',
    'The 4 hidden reasons senior leaders fail the Google/Meta system design interview',
    'Why the modern "fractional executive" role is replacing traditional full-time VPs',
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
          Autonomous 4-Agent Content Studio
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/30 font-mono font-medium">
            LangGraph Orchestrated
          </span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Spawn our 4 specialized AI agents to autonomously research job trends, draft multi-platform copy, render 1080x1350 carousels, and configure Comment-to-DM triggers.
        </p>
      </div>

      {/* Main Studio Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Topic & Configuration Form (7 cols) */}
        <div className="lg:col-span-7 space-y-5">
          {/* Topic Input Card */}
          <div className="glass-panel p-6 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-white flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-violet-400" />
                <span>Career Coaching Topic or Strategic Theme</span>
              </label>
              <span className="text-[10px] text-slate-400 font-mono">Agent 1: Trend Hunter</span>
            </div>

            <textarea
              value={topicPrompt}
              onChange={(e) => setTopicPrompt(e.target.value)}
              rows={3}
              className="w-full bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500/60 leading-relaxed"
              placeholder="Enter a strategic career coaching question or angle..."
            />

            {/* Quick Prompts */}
            <div className="space-y-1.5">
              <span className="text-[11px] text-slate-400 font-medium">Quick suggestions:</span>
              <div className="flex flex-wrap gap-1.5">
                {samplePrompts.map((p, i) => (
                  <button
                    key={i}
                    onClick={() => setTopicPrompt(p)}
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 transition-colors text-left truncate max-w-full"
                  >
                    💡 {p}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Lead Magnet & DM Automation Card */}
          <div className="glass-panel p-6 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-white flex items-center gap-2">
                <Send className="w-4 h-4 text-pink-400" />
                <span>Comment-to-DM Lead Magnet Setup</span>
              </label>
              <span className="text-[10px] text-pink-400 font-mono font-semibold">Agent 4 Automation</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-[11px] font-semibold text-slate-400 block mb-1">
                  Trigger Keyword (Fuzzy Matched 70%+)
                </label>
                <input
                  type="text"
                  value={leadMagnetKeyword}
                  onChange={(e) => setLeadMagnetKeyword(e.target.value.toUpperCase())}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2 text-xs font-mono font-bold text-violet-400 focus:outline-none focus:border-violet-500"
                />
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-400 block mb-1">
                  Attached Lead Magnet Asset
                </label>
                <input
                  type="text"
                  value={leadMagnetName}
                  onChange={(e) => setLeadMagnetName(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-300 focus:outline-none focus:border-violet-500"
                />
              </div>
            </div>
          </div>

          {/* Platform Distribution Checklist */}
          <div className="glass-panel p-6 rounded-2xl space-y-3">
            <label className="text-xs font-bold text-white block">Publishing Distribution Channels</label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { id: 'linkedin', name: 'LinkedIn', desc: 'Post + PDF Carousel' },
                { id: 'instagram', name: 'Instagram', desc: '1080×1350 PNG Deck' },
                { id: 'twitter', name: 'X / Twitter', desc: '5-Tweet Thread' },
                { id: 'facebook', name: 'Facebook', desc: 'Longform Authority' },
              ].map((plat) => {
                const isChecked = selectedPlatforms.includes(plat.id);
                return (
                  <div
                    key={plat.id}
                    onClick={() => togglePlatform(plat.id)}
                    className={`p-3 rounded-xl border cursor-pointer transition-all ${
                      isChecked
                        ? 'bg-violet-600/15 border-violet-500/50 text-white'
                        : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:bg-slate-800/40'
                    }`}
                  >
                    <div className="text-xs font-bold">{plat.name}</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">{plat.desc}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Run Pipeline Action Button */}
          <button
            onClick={handleRunPipeline}
            disabled={isGenerating || !topicPrompt.trim()}
            className="w-full py-3.5 px-6 rounded-2xl bg-gradient-to-r from-violet-600 via-indigo-600 to-pink-600 hover:from-violet-500 hover:to-pink-500 text-white font-black text-sm tracking-wide shadow-xl shadow-violet-600/25 transition-all flex items-center justify-center gap-2 active:scale-98 disabled:opacity-50"
          >
            {isGenerating ? (
              <>
                <RotateCw className="w-4 h-4 animate-spin" />
                <span>Executing 4-Agent LangGraph Pipeline...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                <span>Launch Autonomous 4-Agent Pipeline</span>
              </>
            )}
          </button>
        </div>

        {/* Right Column: Live Agent Graph Visualization (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="glass-panel p-6 rounded-2xl space-y-5">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <Bot className="w-4 h-4 text-violet-400" />
              LangGraph Multi-Agent Architecture
            </h2>

            {/* Agent 1 */}
            <div
              className={`p-4 rounded-xl border transition-all ${
                pipelineStep === 1
                  ? 'bg-violet-600/20 border-violet-500 animate-pulse'
                  : pipelineStep > 1
                  ? 'bg-emerald-950/20 border-emerald-800/40'
                  : 'bg-slate-900/60 border-slate-800'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-violet-600/30 text-violet-400 text-[10px] flex items-center justify-center font-bold">1</span>
                  Agent 1: Trend Hunter & Newsjack
                </span>
                {pipelineStep > 1 ? (
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                ) : pipelineStep === 1 ? (
                  <span className="text-[10px] font-mono text-violet-400 font-bold">Searching BLS/Tech...</span>
                ) : (
                  <span className="text-[10px] text-slate-500">Standby</span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Scrapes tech hiring signals, layoffs, and job market trends for hook angles.
              </p>
            </div>

            {/* Agent 2 */}
            <div
              className={`p-4 rounded-xl border transition-all ${
                pipelineStep === 2
                  ? 'bg-violet-600/20 border-violet-500 animate-pulse'
                  : pipelineStep > 2
                  ? 'bg-emerald-950/20 border-emerald-800/40'
                  : 'bg-slate-900/60 border-slate-800'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-violet-600/30 text-violet-400 text-[10px] flex items-center justify-center font-bold">2</span>
                  Agent 2: Multi-Format Content Creator
                </span>
                {pipelineStep > 2 ? (
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                ) : pipelineStep === 2 ? (
                  <span className="text-[10px] font-mono text-violet-400 font-bold">Generating 5 Slides...</span>
                ) : (
                  <span className="text-[10px] text-slate-500">Standby</span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Produces LinkedIn copy, Twitter threads, Instagram caption, and 5 carousel slides.
              </p>
            </div>

            {/* Agent 3 */}
            <div
              className={`p-4 rounded-xl border transition-all ${
                pipelineStep === 3
                  ? 'bg-violet-600/20 border-violet-500 animate-pulse'
                  : pipelineStep > 3
                  ? 'bg-emerald-950/20 border-emerald-800/40'
                  : 'bg-slate-900/60 border-slate-800'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-violet-600/30 text-violet-400 text-[10px] flex items-center justify-center font-bold">3</span>
                  Agent 3: HITL Critic & Compliance Guard
                </span>
                {pipelineStep > 3 ? (
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                ) : pipelineStep === 3 ? (
                  <span className="text-[10px] font-mono text-violet-400 font-bold">Scoring Virality (9.3/10)...</span>
                ) : (
                  <span className="text-[10px] text-slate-500">Standby</span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Quality checks copy, ensures career coaching voice, routes to Human Approval Queue.
              </p>
            </div>

            {/* Agent 4 */}
            <div
              className={`p-4 rounded-xl border transition-all ${
                pipelineStep === 4
                  ? 'bg-violet-600/20 border-violet-500 animate-pulse'
                  : pipelineStep > 4
                  ? 'bg-emerald-950/20 border-emerald-800/40'
                  : 'bg-slate-900/60 border-slate-800'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-pink-600/30 text-pink-400 text-[10px] flex items-center justify-center font-bold">4</span>
                  Agent 4: Comment-to-DM Webhook Setup
                </span>
                {pipelineStep > 4 ? (
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                ) : pipelineStep === 4 ? (
                  <span className="text-[10px] font-mono text-pink-400 font-bold">Arming Webhook Listeners...</span>
                ) : (
                  <span className="text-[10px] text-slate-500">Standby</span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Binds fuzzy keyword matcher &quot;{leadMagnetKeyword}&quot; to automatic DM dispatcher.
              </p>
            </div>

            {/* Completed Banner */}
            {generatedSuccess && (
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs space-y-2 animate-fade-in">
                <div className="flex items-center gap-2 font-bold text-white">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  <span>Pipeline Completed Successfully!</span>
                </div>
                <p className="text-slate-300">
                  New draft ready with 5 rendered carousel slides, LinkedIn text, and armed Comment-to-DM automation. Transferred to the <strong>HITL Approval Queue</strong>.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
