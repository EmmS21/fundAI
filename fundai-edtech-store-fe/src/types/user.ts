export interface User {
  id?: number;
  email?: string;
  full_name?: string | null;
  address?: string | null;
  city?: string | null;
  country?: string | null;
  created_at?: string;
  status?: 'active' | 'inactive';
  subscription_status?: 'active' | 'inactive';
  subscription_start?: string;    
} 