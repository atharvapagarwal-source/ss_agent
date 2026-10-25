/**
 * API client for SocialCoach AI Backend.
 * Connects to FastAPI backend (default http://localhost:8000)
 * with graceful fallback data for standalone frontend development.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface TenantInfo {
  id: string;
  name: string;
  subdomain: string;
  niche: string;
  plan: string;
}

export interface PostItem {
  id: string;
  topic: string;
  hook: string;
  platforms: string[];
  status: 'PENDING_APPROVAL' | 'APPROVED' | 'SCHEDULED' | 'PUBLISHED' | 'REJECTED';
  created_at: string;
  scheduled_for?: string | null;
  linkedin_text?: string;
  twitter_thread?: string[];
  instagram_caption?: string;
  facebook_post?: string;
  slides?: Array<{
    slide_number: number;
    headline: string;
    body_text: string;
    cta?: string;
  }>;
  critic_score?: number;
  critic_feedback?: string;
}

export interface LeadItem {
  id: string;
  platform: 'instagram' | 'linkedin' | 'twitter' | 'facebook';
  username: string;
  post_topic: string;
  keyword_triggered: string;
  dm_status: 'QUEUED' | 'SENT' | 'DELIVERED' | 'FAILED' | 'CONVERTED';
  sent_at: string;
  lead_magnet_url: string;
}

export interface TrendItem {
  id: string;
  headline: string;
  source: string;
  virality_score: number;
  category: 'LAYOFF' | 'HIRING_SURGE' | 'REMOTE_WORK' | 'SALARY_TREND' | 'AI_IMPACT';
  detected_at: string;
  urgency: 'HIGH' | 'MEDIUM' | 'LOW';
  recommended_angle: string;
}

// ── Default Mock State for Instant Demo / Fallback ──────────────────────────
export const MOCK_TENANTS: TenantInfo[] = [
  {
    id: 't-1001-executive',
    name: 'Sarah Jenkins Career Coaching',
    subdomain: 'sarah-jenkins',
    niche: 'Tech Executive & VP Transitions',
    plan: 'ENTERPRISE',
  },
  {
    id: 't-1002-engineering',
    name: 'DevToLeader Accelerator',
    subdomain: 'dev-to-leader',
    niche: 'Senior Engineers to Engineering Managers',
    plan: 'PRO',
  },
];

export const MOCK_POSTS: PostItem[] = [
  {
    id: 'post-901',
    topic: 'How to bypass 90% of resume ATS filters in 2026',
    hook: 'Still sending 100 cold resumes a week? Here is why 92% are auto-rejected before a human sees them — and the 3-step reverse pipeline that gets interview calls.',
    platforms: ['linkedin', 'instagram', 'twitter'],
    status: 'PENDING_APPROVAL',
    created_at: new Date(Date.now() - 35 * 60 * 1000).toISOString(),
    critic_score: 9.4,
    critic_feedback: 'Strong authority hook. Carousel flow is tight and actionable. CTA keyword "RESUME" is placed prominently on slide 5.',
    linkedin_text: `92% of resumes never reach a human hiring manager.\n\nNot because the candidate is unqualified.\nBecause modern ATS uses semantic intent scoring, not basic keyword matching.\n\nHere is the exact 3-step reverse pipeline my executive clients use to land $250k+ roles:\n\n1. Target the Problem, Not the Title\n2. Reverse-Engineer the 90-day deliverable\n3. Warm executive introduction over cold portal drops\n\nWant my full ATS Semantic Blueprint & 5 proven executive templates?\n👉 Comment "RESUME" below and my AI assistant will instantly send it to your inbox!`,
    twitter_thread: [
      '1/5 🧵 92% of resumes never reach human eyes.\n\nNot because candidates lack skills, but because legacy ATS tactics fail in 2026.\n\nHere is how to reverse the odds:',
      '2/5 🎯 Tip 1: Never apply on company portals first. Reach the hiring director directly with a 3-sentence Value Proposition Brief.',
      '3/5 📊 Tip 2: Replace job duties with quantifiable outcomes: "Built X leading to $Y revenue in Z months".',
      '4/5 ⚡ Tip 3: Optimize for semantic entity clusters, not dumb keyword repetition.',
      '5/5 Want the exact resume checklist my VP clients use? Drop "RESUME" below and I’ll DM you the Notion template!',
    ],
    instagram_caption: 'Stop applying to 50 jobs a day on LinkedIn Easy Apply. 📉\n\nSwipe through for the 2026 Executive Playbook to unlock unlisted senior roles. ➡️\n\nComment "RESUME" to get our free 12-page PDF guide sent straight to your DMs! 🚀',
    facebook_post: 'Tired of radio silence after submitting applications? Swipe through this guide to see what hiring managers actually look for in senior candidates today. Comment RESUME for the full toolkit.',
    slides: [
      {
        slide_number: 1,
        headline: 'Why 92% of Resumes Get Ghosted in 2026',
        body_text: 'The job market has fundamentally shifted. Portals receive 800+ automated applications per role within 2 hours. Here is how to stand out.',
      },
      {
        slide_number: 2,
        headline: 'Step 1: The Executive Value Brief',
        body_text: 'Ditch the 3-page generic CV. Instead, write a 1-page impact document highlighting the top 3 company business risks you solve.',
      },
      {
        slide_number: 3,
        headline: 'Step 2: The Semantic Clustering Method',
        body_text: 'Modern ATS tools look for skill context. Don’t just write "Python" — write "Designed fault-tolerant microservices reducing latency by 42%".',
      },
      {
        slide_number: 4,
        headline: 'Step 3: The 3-Node Backchannel Strategy',
        body_text: 'Identify 2 peers and 1 former team member inside the target department. Ask about active challenges before applying.',
      },
      {
        slide_number: 5,
        headline: 'Want the Full 2026 ATS Blueprint?',
        body_text: 'Get our complete Notion checklist, executive summary templates, and cold outreach scripts for senior roles.',
        cta: 'Comment "RESUME" below for instant DM access',
      },
    ],
  },
  {
    id: 'post-902',
    topic: 'Breaking: 14,000 Tech Layoffs Announced This Week — Here is Your 48-Hour Survival Protocol',
    hook: 'If you were impacted or feel nervous about restructuring, DO NOT panic apply. Do these 4 steps in the first 48 hours instead.',
    platforms: ['linkedin', 'twitter'],
    status: 'SCHEDULED',
    created_at: new Date(Date.now() - 3 * 3600 * 1000).toISOString(),
    scheduled_for: new Date(Date.now() + 2 * 3600 * 1000).toISOString(),
    critic_score: 9.1,
    critic_feedback: 'Timely newsjack. Empathetic yet highly tactical. High virality expected.',
    linkedin_text: `14,000 tech professionals were impacted by layoffs this week alone.\n\nIf you were affected: Take a breath. This is market restructuring, not a reflection of your talent.\n\nHere is your exact 48-hour protocol:\n1. Consolidate your portfolio and brag sheet before laptop access ends.\n2. Request 3 LinkedIn recommendations while memories are fresh.\n3. File severance questions and benefits paperwork calmly.\n4. Comment "GUIDE" for our free 14-day re-employment roadmap.`,
  },
  {
    id: 'post-903',
    topic: 'How to Negotiate a $40,000 Signing Bonus in Senior Roles',
    hook: 'Most candidates leave an average of $38,000 on the table during offer negotiation because they negotiate salary instead of total comp.',
    platforms: ['linkedin', 'instagram'],
    status: 'PUBLISHED',
    created_at: new Date(Date.now() - 24 * 3600 * 1000).toISOString(),
    critic_score: 9.6,
  },
];

export const MOCK_LEADS: LeadItem[] = [
  {
    id: 'lead-1',
    platform: 'linkedin',
    username: 'alex.rivera.tech',
    post_topic: 'How to bypass 90% of resume ATS filters',
    keyword_triggered: 'RESUME',
    dm_status: 'CONVERTED',
    sent_at: '12 mins ago',
    lead_magnet_url: 'https://coaching.io/dl/ats-blueprint-2026.pdf',
  },
  {
    id: 'lead-2',
    platform: 'instagram',
    username: 'priya_design_lead',
    post_topic: 'How to bypass 90% of resume ATS filters',
    keyword_triggered: 'RESUME',
    dm_status: 'DELIVERED',
    sent_at: '28 mins ago',
    lead_magnet_url: 'https://coaching.io/dl/ats-blueprint-2026.pdf',
  },
  {
    id: 'lead-3',
    platform: 'twitter',
    username: 'marcus_builds',
    post_topic: '48-Hour Layoff Survival Protocol',
    keyword_triggered: 'GUIDE',
    dm_status: 'SENT',
    sent_at: '45 mins ago',
    lead_magnet_url: 'https://coaching.io/dl/rehire-roadmap.pdf',
  },
  {
    id: 'lead-4',
    platform: 'linkedin',
    username: 'david_chen_fintech',
    post_topic: 'Negotiate $40,000 Signing Bonus',
    keyword_triggered: 'OFFER',
    dm_status: 'CONVERTED',
    sent_at: '1 hr ago',
    lead_magnet_url: 'https://coaching.io/dl/negotiation-scripts.pdf',
  },
  {
    id: 'lead-5',
    platform: 'instagram',
    username: 'elena_product_growth',
    post_topic: 'How to bypass 90% of resume ATS filters',
    keyword_triggered: 'RESUME',
    dm_status: 'DELIVERED',
    sent_at: '2 hrs ago',
    lead_magnet_url: 'https://coaching.io/dl/ats-blueprint-2026.pdf',
  },
];

export const MOCK_TRENDS: TrendItem[] = [
  {
    id: 'trend-1',
    headline: 'Major Cloud Provider announces 8% restructuring to double down on Autonomous AI Agents',
    source: 'TechCrunch / BLS Jobs Report',
    virality_score: 96,
    category: 'LAYOFF',
    detected_at: '18 mins ago',
    urgency: 'HIGH',
    recommended_angle: 'Pivot story: How infrastructure engineers can re-position skills for the Agentic AI wave.',
  },
  {
    id: 'trend-2',
    headline: 'Q4 Hiring Rebound: Cybersecurity and Platform Engineering salaries jump 14%',
    source: 'Wall Street Journal Careers',
    virality_score: 88,
    category: 'SALARY_TREND',
    detected_at: '1 hour ago',
    urgency: 'MEDIUM',
    recommended_angle: 'Salary negotiation breakdown for mid-to-senior security specialists.',
  },
  {
    id: 'trend-3',
    headline: 'Return-to-Office Mandate backlash leads to 35% surge in remote contractor applications',
    source: 'LinkedIn Workforce Insights',
    virality_score: 92,
    category: 'REMOTE_WORK',
    detected_at: '3 hours ago',
    urgency: 'HIGH',
    recommended_angle: 'Tactical guide: How to negotiate permanent remote terms during interview rounds.',
  },
];

// ── Analytics Time Series Telemetry ─────────────────────────────────────────
export const MOCK_TELEMETRY = [
  { hour: '00:00', reach: 1200, comments: 14, dmsSent: 12, clicks: 8 },
  { hour: '04:00', reach: 1900, comments: 28, dmsSent: 26, clicks: 18 },
  { hour: '08:00', reach: 6400, comments: 112, dmsSent: 104, clicks: 76 },
  { hour: '12:00', reach: 11800, comments: 245, dmsSent: 230, clicks: 178 },
  { hour: '16:00', reach: 15900, comments: 380, dmsSent: 358, clicks: 294 },
  { hour: '20:00', reach: 21400, comments: 490, dmsSent: 462, clicks: 388 },
  { hour: 'Now', reach: 24800, comments: 582, dmsSent: 546, clicks: 460 },
];

export const MOCK_FUNNEL_DATA = [
  { stage: '1. Impressions / Views', count: 48600, dropoff: '100%' },
  { stage: '2. Post Engagements / Comments', count: 1820, dropoff: '3.7%' },
  { stage: '3. Trigger Keyword Matches', count: 1460, dropoff: '80.2%' },
  { stage: '4. Lead Magnet DMs Sent', count: 1410, dropoff: '96.5%' },
  { stage: '5. Resource Download / Converted', count: 894, dropoff: '63.4%' },
];

export const MOCK_PLATFORM_STATS = [
  { platform: 'LinkedIn', reach: 26400, leads: 512, conversionRate: '4.8%', icon: 'linkedin' },
  { platform: 'Instagram', reach: 14200, leads: 268, conversionRate: '3.9%', icon: 'instagram' },
  { platform: 'Twitter (X)', reach: 8900, leads: 114, conversionRate: '2.8%', icon: 'twitter' },
  { platform: 'Facebook', reach: 3100, leads: 48, conversionRate: '2.2%', icon: 'facebook' },
];
