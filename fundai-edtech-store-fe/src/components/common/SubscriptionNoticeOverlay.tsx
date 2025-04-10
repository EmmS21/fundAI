import React from 'react';
import { useUIStore } from '../../stores/uiStore'; // Import the store

export const SubscriptionNoticeOverlay = () => {
  const { hideSubNoticeOverlay } = useUIStore(); // Get hide action

  return (
    // Full-screen backdrop with high z-index
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-red-900 bg-opacity-80 backdrop-blur-sm p-4">
       {/* Content Box */}
      <div className="bg-white dark:bg-gray-800 p-8 md:p-12 rounded-lg shadow-2xl max-w-lg w-full text-center border border-red-300 dark:border-red-700">
        {/* Animated Icon (Simple Pulse) */}
        <div className="mx-auto mb-6 flex items-center justify-center h-16 w-16 rounded-full bg-red-100 dark:bg-red-900/50 animate-pulse">
           <svg className="h-10 w-10 text-red-600 dark:text-red-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
             <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.008v.008H12v-.008z" />
           </svg>
        </div>

        {/* Title */}
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          Action Required
        </h2>

        {/* Message */}
        <p className="text-gray-600 dark:text-gray-300 mb-6">
          Your subscription may be inactive or this device is not registered. Downloads are currently disabled.
        </p>

        {/* Contact Info */}
        <div className="text-sm text-gray-700 dark:text-gray-400 space-y-2 mb-8">
           <p>Please contact support to activate your subscription or register your device:</p>
           <p>Email: <a href="mailto:emmanuel@emmanuelsibanda.com" className="text-blue-600 dark:text-blue-400 hover:underline">emmanuel@emmanuelsibanda.com</a></p>
           <p>WhatsApp: <a href="https://wa.me/15512259418" target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">+1 551 225 9418</a></p>
        </div>

        {/* OK Button */}
        <button
          onClick={hideSubNoticeOverlay} // Call action to hide overlay
          className="w-full sm:w-auto inline-flex justify-center rounded-md border border-transparent bg-red-600 px-6 py-2 text-base font-medium text-white shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 sm:text-sm transition-colors"
        >
          OK
        </button>
      </div>
    </div>
  );
};
