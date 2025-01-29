import React, { useState, useEffect } from 'react';
import { BookList } from '../components/library/BookList';
import { BookPreview } from '../components/library/BookPreview';
import { BookSkeleton } from '../components/library/BookSkeleton';
import { useBooks } from '../hooks/useBooks';
import { useViewStore } from '../stores/viewStore';
import { Book } from '../types/book';

export default function Library() {
  const { books, loading, error } = useBooks();
  const [selectedBook, setSelectedBook] = useState<Book | null>(null);
  const { setIsLibraryView } = useViewStore();

  // Set library view on mount
  useEffect(() => {
    setIsLibraryView(true);
    // Cleanup when component unmounts
    return () => setIsLibraryView(false);
  }, [setIsLibraryView]);

  return (
    <div className="container mx-auto px-6 py-8">
      <h2 className="text-2xl font-semibold mb-6 dark:text-white">My Library</h2>
      
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <BookSkeleton key={i} />
          ))}
        </div>
      ) : error ? (
        <div className="text-red-500 dark:text-red-400">{error}</div>
      ) : (
        <BookList 
          books={books} 
          onBookSelect={setSelectedBook}
        />
      )}

      {selectedBook && (
        <BookPreview
          book={selectedBook}
          onClose={() => setSelectedBook(null)}
        />
      )}
    </div>
  );
}
