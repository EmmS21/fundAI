import { app } from 'electron';
import path from 'path';
import fs from 'fs/promises';
import crypto from 'crypto';

const CACHE_PATH = process.env.XDG_CACHE_HOME 
  || path.join(app.getPath('home'), '.cache', 'fundaai');

export class CacheController {
  private maxSize: number;

  constructor(maxSizeBytes: number) {
    this.maxSize = maxSizeBytes;
  }

  async init() {
    await fs.mkdir(CACHE_PATH, { recursive: true });
  }

  private getFilePath(url: string): string {
    const hash = crypto.createHash('sha256').update(url).digest('hex');
    return path.join(CACHE_PATH, hash);
  }

  async store(url: string, data: Buffer): Promise<string> {
    const filePath = this.getFilePath(url);
    await fs.writeFile(filePath, data);
    return filePath;
  }

  async get(url: string): Promise<Buffer | null> {
    try {
      const filePath = this.getFilePath(url);
      return await fs.readFile(filePath);
    } catch {
      return null;
    }
  }

  async cleanup() {
    // Implement LRU cache eviction
    // Remove files when cache size exceeds maxSize
  }
}
