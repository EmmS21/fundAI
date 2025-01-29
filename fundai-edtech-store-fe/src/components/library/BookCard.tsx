import React from 'react';
import { Book } from '../../types/book';

interface BookCardProps {
  book: Book;
  onClick: () => void;
}

export const BookCard: React.FC<BookCardProps> = ({ book, onClick }) => {
  return (
    <div 
      className="bg-white dark:bg-gray-800 rounded-lg shadow-md hover:shadow-lg 
        transition-shadow duration-200 p-6 relative"
    >
      <div 
        onClick={onClick}
        className="cursor-pointer"
      >
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
          {book.title}
        </h3>
        <p className="text-gray-600 dark:text-gray-300 mb-2">
          {book.author}
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Year: {book.year}
        </p>
        <div className="mt-4 flex items-center">
          <span className={`px-2 py-1 text-xs rounded-full ${
            book.is_embedded 
              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
              : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
          }`}>
            {book.embedding_status}
          </span>
        </div>
      </div>
      
      {/* Download Button */}
      <div className="mt-6 flex justify-center">
        <button
          onClick={(e) => {
            e.stopPropagation();
            // Add download logic here
            console.log(`Downloading book: ${book.id}`);
          }}
          className="px-4 py-2 bg-gray-100 hover:bg-blue-500 text-gray-800 hover:text-white
            rounded-lg transition-colors duration-200 font-medium
            dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-blue-600"
        >
          Download
        </button>
      </div>
    </div>
  );
};
