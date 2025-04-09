const { app } = require('electron');
const path = require('path');
const fs = require('fs');
const https = require('https');

class DownloadManager {
  constructor() {
    this.downloadsPath = path.join(app.getPath('userData'), 'downloads');
    this.ensureDownloadDirectory();
  }

  ensureDownloadDirectory() {
    if (!fs.existsSync(this.downloadsPath)) {
      fs.mkdirSync(this.downloadsPath, { recursive: true });
    }
  }

  async downloadFile(url, filename) {
    return new Promise((resolve, reject) => {
      const filePath = path.join(this.downloadsPath, filename);
      const file = fs.createWriteStream(filePath);

      https.get(url, (response) => {
        if (response.statusCode !== 200) {
          reject(new Error(`Failed to download: ${response.statusCode}`));
          return;
        }

        response.pipe(file);

        file.on('finish', () => {
          file.close();
          resolve(filePath);
        });

        file.on('error', (err) => {
          fs.unlink(filePath, () => reject(err));
        });
      }).on('error', (err) => {
        fs.unlink(filePath, () => reject(err));
      });
    });
  }
}

module.exports = new DownloadManager();
