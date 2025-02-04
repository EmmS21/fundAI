import { ipcMain } from 'electron';
import { Database } from 'sqlite';
import { CacheController } from '../cache/controller';
import axios from 'axios';

export const setupIpcHandlers = (db: Database, cache: CacheController) => {
  ipcMain.handle('get-apps', async () => {
    const apps = await db.all('SELECT * FROM apps ORDER BY last_updated DESC');
    return apps;
  });

  ipcMain.handle('sync-apps', async (event, token: string) => {
    try {
      const lastUpdate = await db.get('SELECT MAX(last_updated) as last FROM apps');
      
      const response = await axios.get('YOUR_API_URL/apps', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'If-Modified-Since': new Date(lastUpdate.last).toUTCString()
        }
      });

      if (response.status === 304) {
        return { updated: false };
      }

      // Update local database with new data
      const apps = response.data;
      for (const app of apps) {
        await db.run(`
          INSERT OR REPLACE INTO apps (id, name, description, version, last_updated, metadata)
          VALUES (?, ?, ?, ?, ?, ?)
        `, [app.id, app.name, app.description, app.version, Date.now(), JSON.stringify(app.metadata)]);
      }

      return { updated: true, count: apps.length };
    } catch (error) {
      console.error('Sync failed:', error);
      return { updated: false, error: error.message };
    }
  });
};
