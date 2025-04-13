const { app } = require('electron');
const path = require('path');
const fs = require('fs');
const https = require('https');
const url = require('url');

class DownloadManager {
  constructor() {
    this.downloadsPath = app.getPath('downloads');
  }

  ensureDownloadDirectory() {
    if (!fs.existsSync(this.downloadsPath)) {
      console.log(`[DownloadManager] Creating download directory: ${this.downloadsPath}`);
      fs.mkdirSync(this.downloadsPath, { recursive: true });
    }
  }

  async downloadFile(downloadUrl, desiredFilename, progressCallback) {
    return new Promise((resolve, reject) => {
      const filePath = path.join(this.downloadsPath, desiredFilename);
      console.log(`[DownloadManager] Target file path: ${filePath}`);

      const file = fs.createWriteStream(filePath);

      const parsedUrl = new url.URL(downloadUrl);
      const httpModule = parsedUrl.protocol === 'https:' ? https : require('http');

      const request = httpModule.get(downloadUrl, (response) => {
        console.log('[DownloadManager] Response headers:', response.headers);
        if (response.statusCode !== 200) {
          file.close();
          fs.unlink(filePath, () => {});
          reject(new Error(`Failed to download: ${response.statusCode} ${response.statusMessage || ''}`));
          return;
        }

        const headerContentLength = response.headers['content-length'];
        console.log(`[DownloadManager] Raw content-length header: ${headerContentLength}`);
        const totalBytes = parseInt(headerContentLength, 10);
        console.log(`[DownloadManager] Parsed totalBytes: ${totalBytes}`);
        let receivedBytes = 0;

        let finalFilename = desiredFilename;
        const disposition = response.headers['content-disposition'];
        if (disposition) {
          console.log(`[DownloadManager] Found Content-Disposition: ${disposition}`);
          const filenameMatch = disposition.match(/filename="?(.+)"?/i);
          if (filenameMatch && filenameMatch[1]) {
            finalFilename = path.basename(filenameMatch[1].replace(/["\\]/g, ''));
            console.log(`[DownloadManager] Parsed filename from header: ${finalFilename}`);
          } else {
            console.log(`[DownloadManager] Could not parse filename from header, using default: ${finalFilename}`);
            finalFilename = path.basename(finalFilename);
          }
        } else {
          console.log(`[DownloadManager] No Content-Disposition header, using default: ${finalFilename}`);
          finalFilename = path.basename(finalFilename);
        }

        // --- ADD THIS LOG ---
        console.log(`[DownloadManager - LOG 2] Determined final filename: '${finalFilename}' (Input was: '${desiredFilename}')`);
        // --- END LOG ---

        const filePath = path.join(this.downloadsPath, finalFilename);
        console.log(`[DownloadManager] Target file path: ${filePath}`);
        const file = fs.createWriteStream(filePath);

        response.on('data', (chunk) => {
          receivedBytes += chunk.length;
          console.log(`[DownloadManager] 'data' event: receivedBytes=${receivedBytes}, typeof progressCallback=${typeof progressCallback}, totalBytes=${totalBytes}`);
          if (progressCallback && totalBytes) {
            const percentage = Math.round((receivedBytes / totalBytes) * 100);
            progressCallback({
              percentage,
              transferred: receivedBytes,
              total: totalBytes
            });
          }
        });

        response.pipe(file);

        file.on('finish', () => {
          // --- ADD THIS LOG ---
          console.log(`[DownloadManager - LOG 3] Resolving promise with: Path='${filePath}', Filename='${finalFilename}'`);
          // --- END LOG ---
          file.close(() => resolve({path: filePath, filename: finalFilename}));
        });

        file.on('error', (err) => {
          file.close();
          fs.unlink(filePath, () => reject(err));
        });
      }).on('error', (err) => {
        file.close();
        fs.unlink(filePath, () => reject(err));
      });

      request.setTimeout(30000, () => {
        request.destroy();
        file.close();
        fs.unlink(filePath, () => {});
        reject(new Error('Download request timed out'));
      });
    });
  }
}

module.exports = new DownloadManager();
