export interface NullString {
  String: string;
  Valid: boolean;
}

export interface App {
  id: string;
  name: string;
  description: string;
  version: string;
  size: number;
  category: string;
  thumbnail?: string;
  type?: string;
  app_version?: string;
  release_date?: string;
  app_type?: string;
  file_path?: string;
  storage_key?: NullString;
  content_type?: NullString;
  created_at?: string;
  updated_at?: string;
}
