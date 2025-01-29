import React from 'react';
import { Book } from '../../types/book';
import { BookCard } from './BookCard';

interface BookListProps {
  books: Book[];
  onBookSelect: (book: Book) => void;
}

export const BookList: React.FC<BookListProps> = ({ books, onBookSelect }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {books.map((book) => (
        <BookCard
          key={book.id}
          book={book}
          onClick={() => onBookSelect(book)}
        />
      ))}
    </div>
  );
};
