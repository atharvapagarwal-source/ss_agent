/**
 * Slide HTML/CSS Template Builder for Instagram & LinkedIn Carousels.
 * 
 * Generates pixel-perfect 1080x1350px high-aesthetic HTML layouts
 * with brand-aware dynamic styling, glassmorphism, modern typography,
 * and high-converting visual hierarchy for career coaches.
 */
import { SlideData, ResolvedBrand } from '../renderer';

function escapeHTML(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Format markdown-like bold text (*text* or **text**) into <strong> tags
 */
function formatBodyText(text: string): string {
  const escaped = escapeHTML(text);
  return escaped
    .replace(/\*\*(.*?)\*\*/g, '<strong class="highlight-text">$1</strong>')
    .replace(/\*(.*?)\*/g, '<strong class="highlight-text">$1</strong>')
    .replace(/\n\n/g, '</p><p class="slide-p">')
    .replace(/\n/g, '<br/>');
}

/**
 * Common CSS Styles used across both Instagram and LinkedIn templates
 */
function getCommonStyles(brand: ResolvedBrand): string {
  return `
    :root {
      --primary: ${brand.primaryColor};
      --secondary: ${brand.secondaryColor};
      --accent: ${brand.accentColor};
      --text: ${brand.textColor};
      --text-light: ${brand.textLightColor};
      --heading-font: '${brand.headingFont}', sans-serif;
      --body-font: '${brand.bodyFont}', sans-serif;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    body {
      width: 1080px;
      height: 1350px;
      overflow: hidden;
      font-family: var(--body-font);
      background-color: #0B0E14;
      color: #E6EDF3;
      display: flex;
      flex-direction: column;
      position: relative;
    }

    /* Ambient background glowing orbs */
    .glow-orb-1 {
      position: absolute;
      top: -120px;
      right: -80px;
      width: 600px;
      height: 600px;
      border-radius: 50%;
      background: radial-gradient(circle, ${brand.primaryColor}33 0%, rgba(0,0,0,0) 70%);
      filter: blur(80px);
      z-index: 0;
      pointer-events: none;
    }

    .glow-orb-2 {
      position: absolute;
      bottom: -150px;
      left: -100px;
      width: 650px;
      height: 650px;
      border-radius: 50%;
      background: radial-gradient(circle, ${brand.accentColor}26 0%, rgba(0,0,0,0) 70%);
      filter: blur(90px);
      z-index: 0;
      pointer-events: none;
    }

    .slide-container {
      position: relative;
      z-index: 1;
      width: 100%;
      height: 100%;
      padding: 80px 75px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    /* Header Bar */
    .slide-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      width: 100%;
    }

    .brand-badge {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .brand-logo {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      object-fit: cover;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }

    .brand-logo-fallback {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      background: linear-gradient(135deg, var(--primary), var(--accent));
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 22px;
      color: #FFFFFF;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
    }

    .niche-tag {
      font-size: 20px;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.15);
      padding: 8px 20px;
      border-radius: 9999px;
      color: #A0AEC0;
      backdrop-filter: blur(10px);
    }

    .slide-counter {
      font-size: 22px;
      font-weight: 700;
      color: #CBD5E1;
      background: rgba(255, 255, 255, 0.06);
      padding: 8px 18px;
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      letter-spacing: 0.03em;
    }

    /* Slide Content Area */
    .slide-main {
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: center;
      margin: 40px 0;
    }

    .hook-badge {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      font-size: 22px;
      font-weight: 700;
      color: var(--accent);
      background: rgba(255, 107, 107, 0.12);
      border: 1px solid rgba(255, 107, 107, 0.3);
      padding: 10px 24px;
      border-radius: 9999px;
      margin-bottom: 30px;
      width: fit-content;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    .slide-title-hook {
      font-family: var(--heading-font);
      font-size: 64px;
      font-weight: 800;
      line-height: 1.15;
      letter-spacing: -0.02em;
      color: #FFFFFF;
      margin-bottom: 32px;
    }

    .slide-title {
      font-family: var(--heading-font);
      font-size: 52px;
      font-weight: 800;
      line-height: 1.2;
      letter-spacing: -0.015em;
      color: #FFFFFF;
      margin-bottom: 30px;
    }

    .gradient-word {
      background: linear-gradient(135deg, var(--primary), var(--accent));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    /* Content Glass Card */
    .glass-card {
      background: rgba(22, 27, 34, 0.75);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 24px;
      padding: 44px;
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.45);
      position: relative;
      overflow: hidden;
    }

    .glass-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 4px;
      background: linear-gradient(90deg, var(--primary), var(--accent));
    }

    .slide-body {
      font-size: 32px;
      line-height: 1.5;
      color: #E2E8F0;
      font-weight: 400;
    }

    .slide-p {
      margin-top: 24px;
    }

    .highlight-text {
      color: #FFFFFF;
      font-weight: 700;
      background: rgba(255, 255, 255, 0.08);
      padding: 2px 8px;
      border-radius: 6px;
    }

    /* CTA Card on Final Slide */
    .cta-card {
      background: linear-gradient(145deg, rgba(30, 38, 56, 0.9), rgba(18, 22, 32, 0.95));
      border: 2px solid var(--primary);
      border-radius: 28px;
      padding: 50px 44px;
      text-align: center;
      box-shadow: 0 20px 50px rgba(108, 99, 255, 0.25);
    }

    .cta-button {
      display: inline-block;
      margin-top: 36px;
      padding: 22px 52px;
      font-size: 30px;
      font-weight: 800;
      color: #FFFFFF;
      background: linear-gradient(135deg, var(--primary), var(--accent));
      border-radius: 9999px;
      box-shadow: 0 10px 25px rgba(108, 99, 255, 0.4);
      letter-spacing: 0.02em;
    }

    /* Footer Bar */
    .slide-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      width: 100%;
      border-top: 1px solid rgba(255, 255, 255, 0.1);
      padding-top: 24px;
    }

    .footer-coach {
      font-size: 20px;
      color: #94A3B8;
      font-weight: 600;
    }

    .swipe-indicator {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 20px;
      font-weight: 700;
      color: var(--primary);
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    .arrow-icon {
      font-size: 24px;
    }
  `;
}

/**
 * Build Instagram Slide (1080x1350)
 */
export function buildInstagramSlideHTML(
  slide: SlideData,
  brand: ResolvedBrand,
  slideNumber: number,
  totalSlides: number
): string {
  const isHook = slideNumber === 1;
  const isLast = slideNumber === totalSlides && totalSlides > 1;
  const headline = escapeHTML(slide.headline);
  const formattedBody = formatBodyText(slide.body_text);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Slide ${slideNumber}</title>
  <style>
    ${getCommonStyles(brand)}
  </style>
</head>
<body>
  <div class="glow-orb-1"></div>
  <div class="glow-orb-2"></div>

  <div class="slide-container">
    <!-- Header -->
    <header class="slide-header">
      <div class="brand-badge">
        ${
          brand.logoUrl
            ? `<img src="${brand.logoUrl}" class="brand-logo" alt="Logo" />`
            : `<div class="brand-logo-fallback">⚡</div>`
        }
        <div class="niche-tag">Career Mastery</div>
      </div>
      <div class="slide-counter">${slideNumber} / ${totalSlides}</div>
    </header>

    <!-- Main Content -->
    <main class="slide-main">
      ${
        isHook
          ? `
          <div class="hook-badge">🔥 STRATEGY GUIDE</div>
          <h1 class="slide-title-hook">${headline}</h1>
          <div class="glass-card">
            <div class="slide-body"><p>${formattedBody}</p></div>
          </div>
          `
          : isLast
          ? `
          <h2 class="slide-title">${headline}</h2>
          <div class="cta-card">
            <div class="slide-body"><p>${formattedBody}</p></div>
            ${slide.cta ? `<div class="cta-button">${escapeHTML(slide.cta)}</div>` : ''}
          </div>
          `
          : `
          <h2 class="slide-title">${headline}</h2>
          <div class="glass-card">
            <div class="slide-body"><p>${formattedBody}</p></div>
          </div>
          `
      }
    </main>

    <!-- Footer -->
    <footer class="slide-footer">
      <div class="footer-coach">@careercoach • Save for later</div>
      ${
        !isLast
          ? `<div class="swipe-indicator">Swipe <span class="arrow-icon">→</span></div>`
          : `<div class="swipe-indicator">Share with a friend 🚀</div>`
      }
    </footer>
  </div>
</body>
</html>`;
}

/**
 * Build LinkedIn Document Slide (1080x1350 for high-res PDF generation)
 */
export function buildLinkedInSlideHTML(
  slide: SlideData,
  brand: ResolvedBrand,
  slideNumber: number,
  totalSlides: number
): string {
  const isHook = slideNumber === 1;
  const isLast = slideNumber === totalSlides && totalSlides > 1;
  const headline = escapeHTML(slide.headline);
  const formattedBody = formatBodyText(slide.body_text);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>LinkedIn Slide ${slideNumber}</title>
  <style>
    ${getCommonStyles(brand)}
    /* LinkedIn-specific subtle corporate refinement */
    body {
      background-color: #0A101D;
    }
    .linkedin-accent-bar {
      width: 60px;
      height: 6px;
      background: var(--primary);
      border-radius: 4px;
      margin-bottom: 24px;
    }
  </style>
</head>
<body>
  <div class="glow-orb-1"></div>
  <div class="glow-orb-2"></div>

  <div class="slide-container">
    <!-- Header -->
    <header class="slide-header">
      <div class="brand-badge">
        ${
          brand.logoUrl
            ? `<img src="${brand.logoUrl}" class="brand-logo" alt="Logo" />`
            : `<div class="brand-logo-fallback">💼</div>`
        }
        <div class="niche-tag">Executive Playbook</div>
      </div>
      <div class="slide-counter">${slideNumber} / ${totalSlides}</div>
    </header>

    <!-- Main Content -->
    <main class="slide-main">
      <div class="linkedin-accent-bar"></div>
      ${
        isHook
          ? `
          <h1 class="slide-title-hook">${headline}</h1>
          <div class="glass-card">
            <div class="slide-body"><p>${formattedBody}</p></div>
          </div>
          `
          : isLast
          ? `
          <h2 class="slide-title">${headline}</h2>
          <div class="cta-card">
            <div class="slide-body"><p>${formattedBody}</p></div>
            ${slide.cta ? `<div class="cta-button">${escapeHTML(slide.cta)}</div>` : ''}
          </div>
          `
          : `
          <h2 class="slide-title">${headline}</h2>
          <div class="glass-card">
            <div class="slide-body"><p>${formattedBody}</p></div>
          </div>
          `
      }
    </main>

    <!-- Footer -->
    <footer class="slide-footer">
      <div class="footer-coach">Follow for daily career insights</div>
      ${
        !isLast
          ? `<div class="swipe-indicator">Next Page <span class="arrow-icon">→</span></div>`
          : `<div class="swipe-indicator">Comment below 💬</div>`
      }
    </footer>
  </div>
</body>
</html>`;
}
