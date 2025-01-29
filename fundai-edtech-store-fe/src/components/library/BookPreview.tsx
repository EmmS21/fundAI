import React from 'react';
import { Book } from '../../types/book';

interface BookPreviewProps {
  book: Book;
  onClose: () => void;
}

export const BookPreview: React.FC<BookPreviewProps> = ({ book, onClose }) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full p-6">
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            {book.title}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 
              dark:hover:text-gray-200 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Author</label>
            <p className="text-gray-900 dark:text-white">{book.author}</p>
          </div>
          
          <div>
            <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Year</label>
            <p className="text-gray-900 dark:text-white">{book.year}</p>
          </div>
          
          <div>
            <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Status</label>
            <span className={`inline-block px-2 py-1 text-sm rounded-full mt-1 ${
              book.is_embedded 
                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
            }`}>
              {book.embedding_status}
            </span>
          </div>
          
          <div>
            <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Added Date</label>
            <p className="text-gray-900 dark:text-white">
              {book.added_date.toLocaleDateString()}
            </p>
          </div>
          
          <div>
            <label className="text-sm font-medium text-gray-500 dark:text-gray-400">Last Updated</label>
            <p className="text-gray-900 dark:text-white">
              {book.updated_date.toLocaleDateString()}
            </p>
          </div>

          {/* Download Button */}
          <div className="pt-4 flex justify-center">
            <button
              onClick={() => {
                // Add download logic here
                console.log(`Downloading book: ${book.id}`);
              }}
              className="px-6 py-2.5 bg-gray-100 hover:bg-blue-500 text-gray-800 hover:text-white
                rounded-lg transition-colors duration-200 font-medium text-base
                dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-blue-600"
            >
              Download
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
