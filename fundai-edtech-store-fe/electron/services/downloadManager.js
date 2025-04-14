const { app } = require('electron');
const path = require('path');
const fs = require('fs');
const https = require('https');
const http = require('http');
const url = require('url');

class DownloadManager {
  constructor() {
    this.downloadsPath = app.getPath('downloads');
    this.ensureDownloadDirectory();
  }

  ensureDownloadDirectory() {
    if (!fs.existsSync(this.downloadsPath)) {
      console.log(`[DownloadManager] Creating download directory: ${this.downloadsPath}`);
      fs.mkdirSync(this.downloadsPath, { recursive: true });
    }
  }

  async downloadFile(downloadUrl, desiredFilename, progressCallback) {
    const finalFilePath = path.join(this.downloadsPath, desiredFilename);
    console.log(`[DownloadManager] Starting download. Target file path: ${finalFilePath}`);

    return new Promise((resolve, reject) => {
      const file = fs.createWriteStream(finalFilePath);

      const parsedUrl = new url.URL(downloadUrl);
      const httpModule = parsedUrl.protocol === 'https:' ? https : http;

      const request = httpModule.get(downloadUrl, (response) => {
        console.log('[DownloadManager] Response status:', response.statusCode);
        if (response.statusCode !== 200) {
          file.close();
          fs.unlink(finalFilePath, (err) => {
             if (err) console.error(`[DownloadManager] Error removing file after status ${response.statusCode}: ${err.message}`);
          });
          reject(new Error(`Download failed: ${response.statusCode} ${response.statusMessage || ''}`));
          return;
        }

        const headerContentLength = response.headers['content-length'];
        const totalBytes = parseInt(headerContentLength, 10);
        let receivedBytes = 0;
        let lastProgressEmitTime = 0;

        response.on('data', (chunk) => {
          receivedBytes += chunk.length;
          if (progressCallback && totalBytes > 0) {
            const now = Date.now();
            if (now - lastProgressEmitTime > 250 || receivedBytes === totalBytes) {
               const percentage = Math.round((receivedBytes / totalBytes) * 100);
               progressCallback({
                 filename: desiredFilename,
                 path: finalFilePath,
                 percentage,
                 transferred: receivedBytes,
                 total: totalBytes
               });
               lastProgressEmitTime = now;
            }
          }
        });

        response.pipe(file);

        file.on('finish', () => {
          file.close(() => {
              console.log(`[DownloadManager] Download finished: ${finalFilePath}`);
              resolve({ path: finalFilePath, filename: desiredFilename });
          });
        });

        file.on('error', (err) => {
          file.close(() => {
             fs.unlink(finalFilePath, (unlinkErr) => {
                 if (unlinkErr) console.error(`[DownloadManager] Error removing file after write error: ${unlinkErr.message}`);
             });
             console.error(`[DownloadManager] File write error for ${desiredFilename}:`, err);
             reject(new Error(`File write error: ${err.message}`));
          });
        });

      }).on('error', (err) => {
          file.close(() => {
             fs.unlink(finalFilePath, (unlinkErr) => {
                if (unlinkErr) console.error(`[DownloadManager] Error removing file after request error: ${unlinkErr.message}`);
             });
             console.error(`[DownloadManager] HTTP request error for ${desiredFilename}:`, err);
             reject(new Error(`Network request error: ${err.message}`));
          });
      });

      request.setTimeout(60000, () => {
        request.destroy(new Error('Download request timed out'));
      });
    });
  }
}

module.exports = new DownloadManager();
