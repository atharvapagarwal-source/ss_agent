/**
 * Storage service for Carousel Renderer.
 * Uploads generated PNG slides and PDF documents to S3, Supabase Storage,
 * or local dev static storage with public URLs.
 */
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { StorageClient } from '@supabase/storage-js';
import fs from 'fs';
import path from 'path';
import { createLogger } from './logger';

const logger = createLogger('storage');

const S3_BUCKET = process.env.S3_BUCKET_NAME || process.env.AWS_S3_BUCKET;
const S3_REGION = process.env.AWS_REGION || 'us-east-1';
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const SUPABASE_BUCKET = process.env.SUPABASE_BUCKET || 'carousels';
const STORAGE_BASE_URL = process.env.STORAGE_PUBLIC_BASE_URL || 'http://localhost:3001/storage';

// ── S3 Client Initializer ───────────────────────────────────────────────────
let s3Client: S3Client | null = null;
if (process.env.AWS_ACCESS_KEY_ID && process.env.AWS_SECRET_ACCESS_KEY && S3_BUCKET) {
  s3Client = new S3Client({
    region: S3_REGION,
    endpoint: process.env.AWS_ENDPOINT_URL || undefined,
    forcePathStyle: Boolean(process.env.AWS_ENDPOINT_URL),
    credentials: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    },
  });
}

// ── Supabase Client Initializer ─────────────────────────────────────────────
let supabaseStorage: StorageClient | null = null;
if (SUPABASE_URL && SUPABASE_SERVICE_KEY) {
  supabaseStorage = new StorageClient(`${SUPABASE_URL}/storage/v1`, {
    apikey: SUPABASE_SERVICE_KEY,
    Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
  });
}

// ── Local Fallback Storage Directory ────────────────────────────────────────
const LOCAL_STORAGE_DIR = path.resolve(process.cwd(), 'public', 'storage');
if (!fs.existsSync(LOCAL_STORAGE_DIR)) {
  fs.mkdirSync(LOCAL_STORAGE_DIR, { recursive: true });
}

/**
 * Upload a raw buffer to storage and return its public URL.
 */
export async function uploadBuffer(
  buffer: Buffer,
  key: string,
  contentType: string = 'image/png'
): Promise<string> {
  // 1. Try S3
  if (s3Client && S3_BUCKET) {
    try {
      await s3Client.send(
        new PutObjectCommand({
          Bucket: S3_BUCKET,
          Key: key,
          Body: buffer,
          ContentType: contentType,
        })
      );
      const publicUrl = process.env.AWS_ENDPOINT_URL
        ? `${process.env.AWS_ENDPOINT_URL}/${S3_BUCKET}/${key}`
        : `https://${S3_BUCKET}.s3.${S3_REGION}.amazonaws.com/${key}`;
      return publicUrl;
    } catch (err) {
      logger.error('Failed to upload buffer to S3, falling back', { error: (err as Error).message });
    }
  }

  // 2. Try Supabase Storage
  if (supabaseStorage) {
    try {
      const { error } = await supabaseStorage
        .from(SUPABASE_BUCKET)
        .upload(key, buffer, {
          contentType,
          upsert: true,
        });

      if (!error) {
        const { data } = supabaseStorage.from(SUPABASE_BUCKET).getPublicUrl(key);
        return data.publicUrl;
      }
      logger.error('Failed to upload buffer to Supabase, falling back', { error: error.message });
    } catch (err) {
      logger.error('Supabase upload exception', { error: (err as Error).message });
    }
  }

  // 3. Local disk fallback
  const localFilePath = path.join(LOCAL_STORAGE_DIR, key);
  const dir = path.dirname(localFilePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(localFilePath, buffer);
  logger.info('Saved asset to local storage fallback', { key, path: localFilePath });
  return `${STORAGE_BASE_URL}/${key.replace(/\\/g, '/')}`;
}

/**
 * Upload a PDF document buffer and return its public URL.
 */
export async function uploadPDF(buffer: Buffer, key: string): Promise<string> {
  return uploadBuffer(buffer, key, 'application/pdf');
}
