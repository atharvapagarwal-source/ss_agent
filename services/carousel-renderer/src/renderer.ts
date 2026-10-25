/**
 * Core Playwright renderer.
 *
 * Renders HTML/CSS slide templates into:
 *   - Instagram: 1080×1350px PNG files (per slide)
 *   - LinkedIn:  1080×1350px PNGs stitched into a multi-page PDF
 *
 * Pipeline per render request:
 *   1. Resolve brand colors/fonts
 *   2. Build HTML for each slide using the appropriate template
 *   3. Launch headless Chromium, navigate to data URL, screenshot
 *   4. Upload PNGs to storage (Supabase / S3)
 *   5. For LinkedIn: stitch PNGs into PDF using pdf-lib
 *   6. Return storage URLs
 */
import { chromium, Browser, Page } from 'playwright';
import { PDFDocument } from 'pdf-lib';
import sharp from 'sharp';
import { uploadBuffer, uploadPDF } from './storage';
import { buildInstagramSlideHTML, buildLinkedInSlideHTML } from './templates/slide-builder';
import { createLogger } from './logger';

const logger = createLogger('renderer');

// ── Types ───────────────────────────────────────────────────────────────────

export interface SlideData {
  slide_number: number;
  headline: string;
  body_text: string;
  visual_description?: string;
  cta?: string | null;
}

export interface BrandProfile {
  brand_colors?: {
    primary: string;
    secondary: string;
    accent: string;
    text: string;
    text_light: string;
  };
  brand_fonts?: { heading: string; body: string };
  logo_url?: string | null;
  coaching_niche?: string;
}

export interface RenderRequest {
  tenant_id: string;
  post_id: string;
  brand?: BrandProfile;
  linkedin_slides?: SlideData[];
  instagram_slides?: SlideData[];
}

export interface RenderResult {
  linkedin_pdf?: string;        // Storage URL for the LinkedIn carousel PDF
  instagram_pngs?: string[];   // Ordered array of storage URLs for Instagram PNGs
}

// ── Canvas sizes ────────────────────────────────────────────────────────────
const INSTAGRAM_VIEWPORT = { width: 1080, height: 1350 };
const LINKEDIN_VIEWPORT  = { width: 1080, height: 1350 };  // Square-ish for doc carousels

// ── Browser singleton ───────────────────────────────────────────────────────
let _browser: Browser | null = null;

async function getBrowser(): Promise<Browser> {
  if (!_browser || !_browser.isConnected()) {
    _browser = await chromium.launch({
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--font-render-hinting=none',
        '--disable-gpu',
      ],
    });
    logger.info('Chromium browser launched');
  }
  return _browser;
}

// ── Main Render Function ─────────────────────────────────────────────────────

export async function renderCarousel(req: RenderRequest): Promise<RenderResult> {
  const brand = resolveBrand(req.brand);
  const result: RenderResult = {};
  const browser = await getBrowser();

  // ── Render Instagram PNGs ─────────────────────────────────────────────────
  if (req.instagram_slides && req.instagram_slides.length > 0) {
    const igUrls = await renderPlatformSlides({
      browser,
      slides: req.instagram_slides,
      brand,
      platform: 'instagram',
      tenantId: req.tenant_id,
      postId: req.post_id,
      viewport: INSTAGRAM_VIEWPORT,
    });
    result.instagram_pngs = igUrls;
    logger.info('Instagram slides rendered', { count: igUrls.length });
  }

  // ── Render LinkedIn PDF ───────────────────────────────────────────────────
  if (req.linkedin_slides && req.linkedin_slides.length > 0) {
    const liPdfUrl = await renderLinkedInPDF({
      browser,
      slides: req.linkedin_slides,
      brand,
      tenantId: req.tenant_id,
      postId: req.post_id,
    });
    result.linkedin_pdf = liPdfUrl;
    logger.info('LinkedIn PDF rendered', { url: liPdfUrl });
  }

  return result;
}

// ── Single-slide preview for HITL Studio ─────────────────────────────────────

export async function renderSingleSlidePreview(
  slide: SlideData,
  platform: 'linkedin' | 'instagram',
  brand?: BrandProfile
): Promise<string> {
  const resolvedBrand = resolveBrand(brand);
  const browser = await getBrowser();
  const viewport = platform === 'instagram' ? INSTAGRAM_VIEWPORT : LINKEDIN_VIEWPORT;

  const html = platform === 'instagram'
    ? buildInstagramSlideHTML(slide, resolvedBrand, slide.slide_number, 1)
    : buildLinkedInSlideHTML(slide, resolvedBrand, slide.slide_number, 1);

  const page = await browser.newPage();
  try {
    await page.setViewportSize(viewport);
    await page.setContent(html, { waitUntil: 'networkidle' });
    await loadGoogleFonts(page, resolvedBrand);

    const screenshotBuffer = await page.screenshot({
      type: 'png',
      clip: { x: 0, y: 0, ...viewport },
      animations: 'disabled',
    });

    return screenshotBuffer.toString('base64');
  } finally {
    await page.close();
  }
}

// ── Platform Slide Renderer ─────────────────────────────────────────────────

async function renderPlatformSlides(opts: {
  browser: Browser;
  slides: SlideData[];
  brand: ResolvedBrand;
  platform: 'instagram' | 'linkedin';
  tenantId: string;
  postId: string;
  viewport: { width: number; height: number };
}): Promise<string[]> {
  const { browser, slides, brand, platform, tenantId, postId, viewport } = opts;
  const urls: string[] = [];

  for (const slide of slides) {
    const html = platform === 'instagram'
      ? buildInstagramSlideHTML(slide, brand, slide.slide_number, slides.length)
      : buildLinkedInSlideHTML(slide, brand, slide.slide_number, slides.length);

    const page = await browser.newPage();
    try {
      await page.setViewportSize(viewport);
      await page.setContent(html, { waitUntil: 'networkidle' });
      await loadGoogleFonts(page, brand);

      // Screenshot
      const rawBuffer = await page.screenshot({
        type: 'png',
        clip: { x: 0, y: 0, ...viewport },
        animations: 'disabled',
      });

      // Optimize with sharp — compress while keeping 1080×1350
      const optimized = await sharp(rawBuffer)
        .png({ compressionLevel: 8, quality: 95 })
        .toBuffer();

      // Upload to storage
      const storageKey = `${tenantId}/${postId}/${platform}/slide-${slide.slide_number}.png`;
      const url = await uploadBuffer(optimized, storageKey, 'image/png');
      urls.push(url);

      logger.info('Slide rendered', { platform, slide: slide.slide_number, url });
    } finally {
      await page.close();
    }
  }

  return urls;
}

// ── LinkedIn PDF Builder ─────────────────────────────────────────────────────

async function renderLinkedInPDF(opts: {
  browser: Browser;
  slides: SlideData[];
  brand: ResolvedBrand;
  tenantId: string;
  postId: string;
}): Promise<string> {
  const { browser, slides, brand, tenantId, postId } = opts;

  // Step 1: Render each LinkedIn slide as PNG
  const pngBuffers: Buffer[] = [];

  for (const slide of slides) {
    const html = buildLinkedInSlideHTML(slide, brand, slide.slide_number, slides.length);
    const page = await browser.newPage();
    try {
      await page.setViewportSize(LINKEDIN_VIEWPORT);
      await page.setContent(html, { waitUntil: 'networkidle' });
      await loadGoogleFonts(page, brand);

      const raw = await page.screenshot({
        type: 'png',
        clip: { x: 0, y: 0, ...LINKEDIN_VIEWPORT },
        animations: 'disabled',
      });

      // Convert to high-quality JPEG for PDF embedding (smaller file size)
      const jpeg = await sharp(raw)
        .jpeg({ quality: 92, mozjpeg: true })
        .toBuffer();

      pngBuffers.push(jpeg);
    } finally {
      await page.close();
    }
  }

  // Step 2: Stitch into PDF using pdf-lib
  const pdfDoc = await PDFDocument.create();
  pdfDoc.setTitle('LinkedIn Carousel');
  pdfDoc.setAuthor('SocialCoach AI');
  pdfDoc.setCreationDate(new Date());

  for (const jpegBuffer of pngBuffers) {
    const img = await pdfDoc.embedJpg(jpegBuffer);
    // LinkedIn documents render best at 4:5 ratio
    const page = pdfDoc.addPage([1080, 1350]);
    page.drawImage(img, {
      x: 0,
      y: 0,
      width: 1080,
      height: 1350,
    });
  }

  const pdfBytes = await pdfDoc.save();
  const storageKey = `${tenantId}/${postId}/linkedin/carousel.pdf`;
  const url = await uploadPDF(Buffer.from(pdfBytes), storageKey);

  return url;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

async function loadGoogleFonts(page: Page, brand: ResolvedBrand): Promise<void> {
  /**
   * Pre-load Google Fonts so screenshots render with correct typography.
   * We inject a <link> tag and wait for the font to be fully loaded.
   */
  const fontFamily = encodeURIComponent(`${brand.headingFont}:wght@400;600;700;800`);
  await page.evaluate((family) => {
    return new Promise<void>((resolve) => {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = `https://fonts.googleapis.com/css2?family=${family}&display=swap`;
      link.onload = () => resolve();
      document.head.appendChild(link);
      // Fallback timeout
      setTimeout(resolve, 2000);
    });
  }, fontFamily);
}

// ── Brand resolution ─────────────────────────────────────────────────────────

export interface ResolvedBrand {
  primaryColor: string;
  secondaryColor: string;
  accentColor: string;
  textColor: string;
  textLightColor: string;
  headingFont: string;
  bodyFont: string;
  logoUrl: string | null;
}

function resolveBrand(brand?: BrandProfile): ResolvedBrand {
  return {
    primaryColor:    brand?.brand_colors?.primary    ?? '#6C63FF',
    secondaryColor:  brand?.brand_colors?.secondary  ?? '#F0EDFF',
    accentColor:     brand?.brand_colors?.accent     ?? '#FF6B6B',
    textColor:       brand?.brand_colors?.text       ?? '#1A1A2E',
    textLightColor:  brand?.brand_colors?.text_light ?? '#FFFFFF',
    headingFont:     brand?.brand_fonts?.heading     ?? 'Inter',
    bodyFont:        brand?.brand_fonts?.body        ?? 'Inter',
    logoUrl:         brand?.logo_url                 ?? null,
  };
}
