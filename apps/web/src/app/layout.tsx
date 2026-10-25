import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'SocialCoach AI — Autonomous Multi-Tenant Social Media & Lead-Gen Agent',
  description:
    'AI-powered social media trend research, newsjacking, carousel generation, human-in-the-loop approvals, comment-to-DM lead automation, and telemetry analytics for career coaches.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-['Plus_Jakarta_Sans',sans-serif] bg-[#090D16] text-slate-100 min-h-screen">
        {children}
      </body>
    </html>
  );
}
