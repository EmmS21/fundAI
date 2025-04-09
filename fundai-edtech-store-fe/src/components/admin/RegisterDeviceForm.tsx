import React, { useState } from 'react';

interface RegisterDeviceFormProps {
  // Callback to notify parent (UsersModal) of the registration result
  onResult: (result: { success: boolean; message: string }) => void;
}

// Define the structure of the data we'll send via IPC
interface DeviceData {
  hardwareId: string;
  email: string;
  fullName?: string; // Optional fields
  address?: string;
  city?: string;
  country?: string;
}

const RegisterDeviceForm: React.FC<RegisterDeviceFormProps> = ({ onResult }) => {
  // State for each form field
  const [hardwareId, setHardwareId] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [country, setCountry] = useState('');

  // State for loading/submission status
  const [isLoading, setIsLoading] = useState(false);

  // --- ADDED: Function to clear form fields ---
  const resetForm = () => {
    setHardwareId('');
    setEmail('');
    setFullName('');
    setAddress('');
    setCity('');
    setCountry('');
  };
  // --- END ADD ---

  // Handle form submission
  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault(); // Prevent standard form submission
    setIsLoading(true);

    // Basic validation
    if (!hardwareId.trim() || !email.trim()) {
      onResult({ success: false, message: 'Hardware ID and Email are required.' });
      setIsLoading(false);
      return;
    }

    // Construct the data object to send
    const deviceData: DeviceData = {
      hardwareId: hardwareId.trim(),
      email: email.trim(),
      // Include optional fields only if they have values
      ...(fullName.trim() && { fullName: fullName.trim() }),
      ...(address.trim() && { address: address.trim() }),
      ...(city.trim() && { city: city.trim() }),
      ...(country.trim() && { country: country.trim() }),
    };

    try {
      console.log('[Admin UI] Sending device registration data:', deviceData);
      // Call the IPC function exposed via preload.js
      const result = await window.electronAPI.adminRegisterDevice(deviceData);

      // Check if result has a message, otherwise use a default
      const message = result.message || (result.success ? 'Device registered successfully.' : 'An unknown success response was received.');

      // --- MODIFIED: Reset form BEFORE calling onResult for success ---
      if (result.success) {
        resetForm(); // Clear the form fields
      }
       // --- END MODIFY ---

      onResult({ success: result.success ?? true, message: message }); // Pass success status from result if available

    } catch (error: any) {
      console.error('[Admin UI] Device registration failed:', error);
      // Pass the specific error message from the main process/backend
      onResult({ success: false, message: error.message || 'An unexpected error occurred.' });
    } finally {
      setIsLoading(false); // Reset loading state regardless of outcome
    }
  };

  // Reusable input field component or styling classes
  const inputClasses = "mt-1 block w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm text-gray-900 dark:text-gray-100";
  const labelClasses = "block text-sm font-medium text-gray-700 dark:text-gray-300";

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Grid layout for better alignment */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Required Fields */}
        <div>
          <label htmlFor="hardwareId" className={labelClasses}>
            Hardware ID <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="hardwareId"
            value={hardwareId}
            onChange={(e) => setHardwareId(e.target.value)}
            className={inputClasses}
            required
            disabled={isLoading}
            placeholder="e.g., 4cbd68de-..."
          />
        </div>
        <div>
          <label htmlFor="email" className={labelClasses}>
            User Email <span className="text-red-500">*</span>
          </label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputClasses}
            required
            disabled={isLoading}
            placeholder="user@example.com"
          />
        </div>
      </div>

       {/* Optional Fields */}
       <p className="text-xs text-gray-500 dark:text-gray-400 mt-4 -mb-2">
         Optional details (only required if creating a new user via email):
       </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="fullName" className={labelClasses}>
            Full Name
          </label>
          <input
            type="text"
            id="fullName"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className={inputClasses}
            disabled={isLoading}
          />
        </div>
        <div>
          <label htmlFor="address" className={labelClasses}>
            Address
          </label>
          <input
            type="text"
            id="address"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            className={inputClasses}
            disabled={isLoading}
          />
        </div>
        <div>
          <label htmlFor="city" className={labelClasses}>
            City
          </label>
          <input
            type="text"
            id="city"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className={inputClasses}
            disabled={isLoading}
          />
        </div>
        <div>
          <label htmlFor="country" className={labelClasses}>
            Country
          </label>
          <input
            type="text"
            id="country"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            className={inputClasses}
            disabled={isLoading}
          />
        </div>
      </div>


      {/* Submit Button */}
      <div className="flex justify-end pt-2">
        <button
          type="submit"
          disabled={isLoading}
          className={`inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white 
            ${isLoading
              ? 'bg-indigo-400 cursor-not-allowed'
              : 'bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500'
            } 
            dark:focus:ring-offset-gray-800 transition duration-150 ease-in-out`}
        >
          {isLoading ? 'Registering...' : 'Register Device'}
        </button>
      </div>
    </form>
  );
};

export default RegisterDeviceForm;
