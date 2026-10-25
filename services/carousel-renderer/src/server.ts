/**
 * Express server for the Carousel Renderer Microservice.
 * Exposes:
 *   POST /render     — full render request (LinkedIn PDF + Instagram PNGs)
 *   POST /render/preview  — single-slide PNG for live HITL Studio preview
 *   GET  /health     — health check
 */
import express, { Request, Response, NextFunction } from 'express';
import dotenv from 'dotenv';
import { z } from 'zod';
import { renderCarousel, RenderRequest } from './renderer';
import path from 'path';
import { createLogger } from './logger';

dotenv.config();

const app = express();
const logger = createLogger('server');
const PORT = parseInt(process.env.PORT || '3001', 10);

// ── Middleware ──────────────────────────────────────────────────────────────
app.use(express.json({ limit: '10mb' }));

// Serve local rendered slides & PDFs
const LOCAL_STORAGE_DIR = path.resolve(process.cwd(), 'public', 'storage');
app.use('/storage', express.static(LOCAL_STORAGE_DIR));

// ── Request Schemas ─────────────────────────────────────────────────────────

const SlideSchema = z.object({
  slide_number: z.number().int().min(1),
  headline: z.string().max(120),
  body_text: z.string().max(600),
  visual_description: z.string().optional(),
  cta: z.string().nullable().optional(),
});

const BrandSchema = z.object({
  brand_colors: z.object({
    primary: z.string().default('#6C63FF'),
    secondary: z.string().default('#F0EDFF'),
    accent: z.string().default('#FF6B6B'),
    text: z.string().default('#1A1A2E'),
    text_light: z.string().default('#FFFFFF'),
  }).optional(),
  brand_fonts: z.object({
    heading: z.string().default('Inter'),
    body: z.string().default('Inter'),
  }).optional(),
  logo_url: z.string().nullable().optional(),
  coaching_niche: z.string().optional(),
});

const RenderRequestSchema = z.object({
  tenant_id: z.string().uuid(),
  post_id: z.string(),
  brand: BrandSchema.optional(),
  linkedin_slides: z.array(SlideSchema).min(0).max(10).optional(),
  instagram_slides: z.array(SlideSchema).min(0).max(10).optional(),
});

const PreviewRequestSchema = z.object({
  slide: SlideSchema,
  platform: z.enum(['linkedin', 'instagram']),
  brand: BrandSchema.optional(),
});

// ── Routes ──────────────────────────────────────────────────────────────────

app.get('/health', (_req: Request, res: Response) => {
  res.json({ status: 'ok', service: 'carousel-renderer', version: '1.0.0' });
});

/**
 * POST /render
 * Full render: generates LinkedIn PDF + Instagram PNG deck and uploads to storage.
 * Returns storage URLs for both assets.
 */
app.post('/render', async (req: Request, res: Response, next: NextFunction) => {
  const parsed = RenderRequestSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(422).json({ error: 'Invalid request', details: parsed.error.flatten() });
  }

  const renderReq: RenderRequest = parsed.data as RenderRequest;
  const startMs = Date.now();
  logger.info('Render request received', {
    tenant_id: renderReq.tenant_id,
    post_id: renderReq.post_id,
    linkedin_slides: renderReq.linkedin_slides?.length ?? 0,
    instagram_slides: renderReq.instagram_slides?.length ?? 0,
  });

  try {
    const result = await renderCarousel(renderReq);
    const elapsed = Date.now() - startMs;
    logger.info('Render complete', { post_id: renderReq.post_id, elapsed_ms: elapsed });
    return res.json({ ...result, render_ms: elapsed });
  } catch (err) {
    logger.error('Render failed', { error: (err as Error).message });
    next(err);
  }
});

/**
 * POST /render/preview
 * Renders a single slide as a PNG (base64) for the HITL Studio live preview.
 * No storage upload — returns base64 data URI directly.
 */
app.post('/render/preview', async (req: Request, res: Response, next: NextFunction) => {
  const parsed = PreviewRequestSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(422).json({ error: 'Invalid request', details: parsed.error.flatten() });
  }

  try {
    const { renderSingleSlidePreview } = await import('./renderer');
    const base64 = await renderSingleSlidePreview(
      parsed.data.slide,
      parsed.data.platform,
      parsed.data.brand
    );
    return res.json({ preview_data_uri: `data:image/png;base64,${base64}` });
  } catch (err) {
    logger.error('Preview render failed', { error: (err as Error).message });
    next(err);
  }
});

// ── Error Handler ───────────────────────────────────────────────────────────
app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  res.status(500).json({ error: 'Internal renderer error', message: err.message });
});

// ── Start ────────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  logger.info(`Carousel Renderer listening on port ${PORT}`);
});

export default app;
