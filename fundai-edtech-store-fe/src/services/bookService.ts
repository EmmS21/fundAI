import { collection, getDocs, query, orderBy } from 'firebase/firestore';
import { db } from '../config/firebase';
import { Book } from '../types/book';

export const bookService = {
  async getBooks(): Promise<Book[]> {
    const booksRef = collection(db, 'books');
    const q = query(booksRef, orderBy('added_date', 'desc'));
    const snapshot = await getDocs(q);
    return snapshot.docs.map((doc: any) => ({
      id: doc.id,
      ...doc.data(),
      added_date: doc.data().added_date?.toDate(),
      updated_date: doc.data().updated_date?.toDate(),
    })) as Book[];
  }
};
