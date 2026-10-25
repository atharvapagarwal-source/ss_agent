'use client';

import React, { useState } from 'react';
import {
  CheckCircle2,
  Clock,
  Edit3,
  RotateCcw,
  Send,
  Eye,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  SlidersHorizontal,
  ThumbsDown,
  Calendar,
  AlertCircle,
} from 'lucide-react';
import { PostItem, MOCK_POSTS } from '@/lib/api';

export const HitlQueueView: React.FC = () => {
  const [posts, setPosts] = useState<PostItem[]>(MOCK_POSTS);
  const [selectedPost, setSelectedPost] = useState<PostItem>(MOCK_POSTS[0]);
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [activePlatformTab, setActivePlatformTab] = useState<'linkedin' | 'instagram' | 'twitter' | 'facebook'>('linkedin');
  const [revisionPrompt, setRevisionPrompt] = useState('');
  const [isRevisionModalOpen, setIsRevisionModalOpen] = useState(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  const pendingPosts = posts.filter((p) => p.status === 'PENDING_APPROVAL');

  const handleApprovePublish = (postId: string) => {
    setPosts((prev) =>
      prev.map((p) => (p.id === postId ? { ...p, status: 'PUBLISHED' } : p))
    );
    showNotice('Post approved and published immediately across all platforms! 🚀');
  };

  const handleApproveSchedule = (postId: string) => {
    setPosts((prev) =>
      prev.map((p) => (p.id === postId ? { ...p, status: 'SCHEDULED' } : p))
    );
    showNotice('Post scheduled for high-engagement peak window (14:30 EST) 📅');
  };

  const handleSendRevision = () => {
    if (!revisionPrompt.trim()) return;
    setIsRevisionModalOpen(false);
    showNotice(`Revision feedback sent to Agent 2 (Content Creator): "${revisionPrompt}"`);
    setRevisionPrompt('');
  };

  const showNotice = (msg: string) => {
    setActionSuccessMsg(msg);
    setTimeout(() => setActionSuccessMsg(null), 4000);
  };

  const slides = selectedPost.slides || [];
  const activeSlide = slides[currentSlideIndex] || slides[0];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            Human-in-the-Loop (HITL) Approval Queue
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30 font-mono font-medium">
              {pendingPosts.length} Awaiting Approval
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Review agent-generated drafts, inspect 1080x1350 carousel slides, refine copy, or request natural language revisions.
          </p>
        </div>
      </div>

      {actionSuccessMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2.5 animate-fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>{actionSuccessMsg}</span>
        </div>
      )}

      {/* Main Grid: Post Selector + Slide & Copy Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Post Queue List (4 cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-400 px-1">
            Pending Approval ({pendingPosts.length})
          </div>

          <div className="space-y-2.5">
            {posts.map((post) => {
              const isSelected = selectedPost.id === post.id;
              return (
                <div
                  key={post.id}
                  onClick={() => {
                    setSelectedPost(post);
                    setCurrentSlideIndex(0);
                  }}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-violet-600/15 border-violet-500/50 shadow-md shadow-violet-500/10'
                      : 'bg-slate-900/60 border-slate-800/80 hover:bg-slate-800/40'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                        post.status === 'PENDING_APPROVAL'
                          ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                          : post.status === 'PUBLISHED'
                          ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                          : 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/30'
                      }`}
                    >
                      {post.status.replace('_', ' ')}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      Score: <strong className="text-violet-400">{post.critic_score}/10</strong>
                    </span>
                  </div>

                  <h3 className="text-xs font-bold text-slate-200 line-clamp-2 leading-relaxed">
                    {post.topic}
                  </h3>

                  <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
                    <div className="flex items-center gap-1.5">
                      {post.platforms.map((p) => (
                        <span key={p} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 capitalize">
                          {p}
                        </span>
                      ))}
                    </div>
                    {post.slides && (
                      <span className="text-[10px] text-slate-400">
                        {post.slides.length} slides
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Interactive Carousel & Copy Editor (8 cols) */}
        <div className="lg:col-span-8 space-y-5">
          {/* Top Bar for Selected Post */}
          <div className="glass-panel p-5 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-mono text-violet-400 font-semibold">{selectedPost.id}</span>
                <span className="text-slate-400">•</span>
                <span className="text-xs text-slate-300">Critic AI Score:</span>
                <span className="text-xs font-bold px-2 py-0.5 rounded bg-violet-500/20 text-violet-300">
                  {selectedPost.critic_score} / 10
                </span>
              </div>
              <h2 className="text-sm font-extrabold text-white line-clamp-1">{selectedPost.topic}</h2>
            </div>

            {/* HITL Action Buttons */}
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={() => setIsRevisionModalOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5 text-amber-400" />
                <span>Revise with AI</span>
              </button>

              <button
                onClick={() => handleApproveSchedule(selectedPost.id)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-200 text-xs font-semibold border border-indigo-500/40 transition-colors"
              >
                <Calendar className="w-3.5 h-3.5 text-indigo-400" />
                <span>Schedule</span>
              </button>

              <button
                onClick={() => handleApprovePublish(selectedPost.id)}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold transition-all shadow-md shadow-emerald-600/20 active:scale-95"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Approve & Publish</span>
              </button>
            </div>
          </div>

          {/* Critic Feedback Banner */}
          {selectedPost.critic_feedback && (
            <div className="p-3.5 rounded-xl bg-violet-950/40 border border-violet-800/40 text-xs text-violet-200 flex items-start gap-2.5">
              <Sparkles className="w-4 h-4 text-amber-300 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="text-white">Agent 3 (Critic / Compliance Guard):</strong>{' '}
                {selectedPost.critic_feedback}
              </div>
            </div>
          )}

          {/* Slide Deck Inspector (Interactive 1080x1350 Preview) */}
          {slides.length > 0 && (
            <div className="glass-panel p-6 rounded-2xl">
              <div className="flex items-center justify-between mb-4">
                <div className="text-xs font-bold text-white flex items-center gap-2">
                  <Eye className="w-4 h-4 text-violet-400" />
                  <span>Carousel Slide Renderer ({slides.length} slides)</span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    disabled={currentSlideIndex === 0}
                    onClick={() => setCurrentSlideIndex((i) => i - 1)}
                    className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-30"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="text-xs font-mono text-slate-300">
                    Slide {currentSlideIndex + 1} of {slides.length}
                  </span>
                  <button
                    disabled={currentSlideIndex === slides.length - 1}
                    onClick={() => setCurrentSlideIndex((i) => i + 1)}
                    className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 disabled:opacity-30"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Slide Preview Frame (4:5 Aspect Ratio Styled Preview) */}
              <div className="relative w-full max-w-md mx-auto aspect-[4/5] rounded-2xl bg-[#0B0E14] border border-slate-700 p-8 flex flex-col justify-between shadow-2xl overflow-hidden">
                <div className="absolute -top-20 -right-20 w-48 h-48 rounded-full bg-violet-600/20 blur-3xl pointer-events-none" />
                <div className="absolute -bottom-20 -left-20 w-48 h-48 rounded-full bg-pink-600/20 blur-3xl pointer-events-none" />

                {/* Slide Header */}
                <div className="relative z-10 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded bg-gradient-to-tr from-violet-500 to-indigo-500 flex items-center justify-center text-[10px] font-bold text-white">
                      💼
                    </div>
                    <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
                      Executive Playbook
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-400">
                    {activeSlide.slide_number} / {slides.length}
                  </span>
                </div>

                {/* Slide Main Body */}
                <div className="relative z-10 my-auto space-y-4">
                  <h3 className="text-lg font-black text-white leading-tight">
                    {activeSlide.headline}
                  </h3>
                  <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-300 leading-relaxed">
                    {activeSlide.body_text}
                  </div>
                  {activeSlide.cta && (
                    <div className="p-3 rounded-xl bg-gradient-to-r from-violet-600 to-pink-600 text-center text-xs font-bold text-white shadow-lg shadow-violet-600/30">
                      {activeSlide.cta}
                    </div>
                  )}
                </div>

                {/* Slide Footer */}
                <div className="relative z-10 flex items-center justify-between text-[10px] text-slate-500 pt-2 border-t border-slate-800">
                  <span>@careercoach • Save for later</span>
                  <span className="text-violet-400 font-bold">Swipe →</span>
                </div>
              </div>
            </div>
          )}

          {/* Platform Specific Copy Tabs */}
          <div className="glass-panel p-5 rounded-2xl">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3 mb-4">
              {(['linkedin', 'instagram', 'twitter', 'facebook'] as const).map((platform) => (
                <button
                  key={platform}
                  onClick={() => setActivePlatformTab(platform)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold capitalize transition-colors ${
                    activePlatformTab === platform
                      ? 'bg-violet-600 text-white'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {platform} Copy
                </button>
              ))}
            </div>

            {/* Copy Content */}
            <div className="space-y-3">
              {activePlatformTab === 'linkedin' && (
                <textarea
                  defaultValue={selectedPost.linkedin_text || 'No LinkedIn copy generated.'}
                  rows={8}
                  className="w-full bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 text-xs text-slate-200 font-mono leading-relaxed focus:outline-none focus:border-violet-500/50"
                />
              )}
              {activePlatformTab === 'instagram' && (
                <textarea
                  defaultValue={selectedPost.instagram_caption || 'No Instagram caption generated.'}
                  rows={8}
                  className="w-full bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 text-xs text-slate-200 font-mono leading-relaxed focus:outline-none focus:border-violet-500/50"
                />
              )}
              {activePlatformTab === 'twitter' && (
                <div className="space-y-2">
                  {(selectedPost.twitter_thread || ['No thread generated.']).map((tweet, i) => (
                    <div key={i} className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-300 font-mono">
                      {tweet}
                    </div>
                  ))}
                </div>
              )}
              {activePlatformTab === 'facebook' && (
                <textarea
                  defaultValue={selectedPost.facebook_post || 'No Facebook copy generated.'}
                  rows={6}
                  className="w-full bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 text-xs text-slate-200 font-mono leading-relaxed focus:outline-none focus:border-violet-500/50"
                />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Revision Modal Dialog */}
      {isRevisionModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0f1422] border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl animate-fade-in">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <RotateCcw className="w-4 h-4 text-violet-400" />
                Prompt Agent 2 for Revision
              </h3>
              <button
                onClick={() => setIsRevisionModalOpen(false)}
                className="text-slate-400 hover:text-white text-xs font-bold"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Provide natural language feedback. The Content Creator Agent will re-generate the copy and carousel slides to match your guidelines.
            </p>

            <textarea
              value={revisionPrompt}
              onChange={(e) => setRevisionPrompt(e.target.value)}
              placeholder="e.g. 'Make the hook punchier for mid-career engineers feeling burnt out. Add a stat about salary increases in slide 3.'"
              rows={4}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500"
            />

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setIsRevisionModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleSendRevision}
                className="px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold flex items-center gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                Regenerate Post
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
