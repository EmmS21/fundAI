import { DownloadQueueItem } from './types';
import Database from 'better-sqlite3';
import { getDatabasePath } from './init';

export class DatabaseManager {
  private db: Database.Database;
  private static instance: DatabaseManager;
  private constructor() {
    const dbPath = getDatabasePath();
    this.db = new Database(dbPath, { verbose: console.log });
    this.initDatabase();
  }

  static getInstance(): DatabaseManager {
    if (!DatabaseManager.instance) {
      DatabaseManager.instance = new DatabaseManager();
    }
    return DatabaseManager.instance;
  }

  private initDatabase() {
    // Enable foreign keys
    this.db.pragma('foreign_keys = ON');

    // Create tables
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS apps_catalog (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        version TEXT NOT NULL,
        size INTEGER,
        last_updated TEXT,
        cached_at TEXT DEFAULT CURRENT_TIMESTAMP,
        metadata TEXT
      );

      CREATE TABLE IF NOT EXISTS download_queue (
        id TEXT PRIMARY KEY,
        app_id TEXT NOT NULL,
        status TEXT NOT NULL,
        progress INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        error_message TEXT,
        FOREIGN KEY (app_id) REFERENCES apps_catalog(id)
      );

      CREATE TABLE IF NOT EXISTS preferences (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
      );

      CREATE TABLE IF NOT EXISTS installed_apps (
        id TEXT PRIMARY KEY,
        app_id TEXT NOT NULL,
        install_path TEXT NOT NULL,
        installed_version TEXT NOT NULL,
        install_date TEXT DEFAULT CURRENT_TIMESTAMP,
        last_launched TEXT,
        FOREIGN KEY (app_id) REFERENCES apps_catalog(id)
      );
    `);
  }

  // Basic CRUD operations
  public getApps() {
    return this.db.prepare('SELECT * FROM apps_catalog').all();
  }

  public getApp(id: string) {
    return this.db.prepare('SELECT * FROM apps_catalog WHERE id = ?').get(id);
  }

  public addApp(app: any) {
    const stmt = this.db.prepare(`
      INSERT INTO apps_catalog (id, name, description, version, size, last_updated, metadata)
      VALUES (@id, @name, @description, @version, @size, @last_updated, @metadata)
    `);
    return stmt.run(app);
  }

  public updateApp(id: string, app: any) {
    const stmt = this.db.prepare(`
      UPDATE apps_catalog 
      SET name = @name, 
          description = @description, 
          version = @version, 
          size = @size, 
          last_updated = @last_updated, 
          metadata = @metadata
      WHERE id = @id
    `);
    return stmt.run({ ...app, id });
  }

  public getPreference(key: string) {
    return this.db.prepare('SELECT value FROM preferences WHERE key = ?').get(key);
  }

  public setPreference(key: string, value: string) {
    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO preferences (key, value, updated_at)
      VALUES (?, ?, CURRENT_TIMESTAMP)
    `);
    return stmt.run(key, value);
  }

  public addToDownloadQueue(download: any) {
    const stmt = this.db.prepare(`
      INSERT INTO download_queue (id, app_id, status)
      VALUES (@id, @app_id, @status)
    `);
    return stmt.run(download);
  }

  public updateDownloadStatus(id: string, status: string, progress: number) {
    const stmt = this.db.prepare(`
      UPDATE download_queue 
      SET status = ?, progress = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `);
    return stmt.run(status, progress, id);
  }

  public getDownloadQueue(): DownloadQueueItem[] {
    return this.db.prepare(
      'SELECT * FROM download_queue WHERE status IN ("pending", "downloading")'
    ).all() as DownloadQueueItem[];
  }

  public addInstalledApp(data: { 
    appId: string; 
    installPath: string; 
    version: string; 
  }): void {
    this.db.prepare(`
      INSERT INTO installed_apps (id, app_id, install_path, installed_version)
      VALUES (?, ?, ?, ?)
    `).run(`inst_${Date.now()}`, data.appId, data.installPath, data.version);
  }
}
