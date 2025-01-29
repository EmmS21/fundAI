export interface Book {
  id: string;
  title: string;
  author: string;
  year: number;
  embedding_status: string;
  is_embedded: boolean;
  added_date: Date;
  updated_date: Date;
}
