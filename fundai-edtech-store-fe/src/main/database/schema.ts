import { app } from 'electron';
import path from 'path';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';

// Get user's data directory (follows XDG spec)
const USER_DATA_PATH = process.env.XDG_DATA_HOME 
  || path.join(app.getPath('home'), '.local', 'share', 'fundaai');

// Database setup
export const initDatabase = async () => {
  const db = await open({
    filename: path.join(USER_DATA_PATH, 'store.db'),
    driver: sqlite3.Database
  });

  // Create tables if they don't exist
  await db.exec(`
    CREATE TABLE IF NOT EXISTS apps (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      description TEXT,
      version TEXT NOT NULL,
      last_updated INTEGER NOT NULL,
      metadata TEXT,
      local_path TEXT
    );

    CREATE TABLE IF NOT EXISTS cache_meta (
      url TEXT PRIMARY KEY,
      etag TEXT,
      last_modified TEXT,
      local_path TEXT NOT NULL,
      last_accessed INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS sessions (
      token TEXT PRIMARY KEY,
      expiration INTEGER NOT NULL,
      user_data TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_last_updated ON apps(last_updated);
    CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache_meta(last_accessed);
  `);

  return db;
};
