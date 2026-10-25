'use client';

import React, { useState } from 'react';
import { Sidebar, ActiveTab } from '@/components/navigation/Sidebar';
import { TopBar } from '@/components/navigation/TopBar';
import { AnalyticsView } from '@/components/dashboard/AnalyticsView';
import { HitlQueueView } from '@/components/hitl/HitlQueueView';
import { ContentStudioView } from '@/components/studio/ContentStudioView';
import { LeadsCrmView } from '@/components/leads/LeadsCrmView';
import { NewsjackView } from '@/components/newsjack/NewsjackView';
import { SettingsView } from '@/components/settings/SettingsView';
import { TrendItem, MOCK_POSTS, MOCK_TRENDS } from '@/lib/api';

export default function Home() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('analytics');
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [pendingHitlCount, setPendingHitlCount] = useState(
    MOCK_POSTS.filter((p) => p.status === 'PENDING_APPROVAL').length
  );
  const [urgentNewsjackCount, setUrgentNewsjackCount] = useState(
    MOCK_TRENDS.filter((t) => t.urgency === 'HIGH').length
  );

  const handleTriggerPipeline = () => {
    setIsPipelineRunning(true);
    setActiveTab('studio');
    setTimeout(() => {
      setIsPipelineRunning(false);
      setPendingHitlCount((prev) => prev + 1);
    }, 5000);
  };

  const handleSelectTrendForPipeline = (trend: TrendItem) => {
    setActiveTab('studio');
    handleTriggerPipeline();
  };

  return (
    <div className="flex h-screen bg-[#070A12] text-slate-100 overflow-hidden">
      {/* Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        pendingHitlCount={pendingHitlCount}
        urgentNewsjackCount={urgentNewsjackCount}
      />

      {/* Main App Workspace */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <TopBar
          onTriggerPipeline={handleTriggerPipeline}
          isPipelineRunning={isPipelineRunning}
        />

        {/* Dynamic View Scrollable Canvas */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          <div className="max-w-7xl mx-auto">
            {activeTab === 'analytics' && <AnalyticsView />}
            {activeTab === 'hitl' && <HitlQueueView />}
            {activeTab === 'studio' && (
              <ContentStudioView
                onPostCreated={() => setPendingHitlCount((prev) => prev + 1)}
              />
            )}
            {activeTab === 'leads' && <LeadsCrmView />}
            {activeTab === 'newsjack' && (
              <NewsjackView
                onSelectTrendForPipeline={handleSelectTrendForPipeline}
              />
            )}
            {activeTab === 'settings' && <SettingsView />}
          </div>
        </main>
      </div>
    </div>
  );
}
