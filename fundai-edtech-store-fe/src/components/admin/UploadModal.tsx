import React, { useState, useCallback } from 'react';
import useDropzone from 'react-dropzone';

interface UploadModalProps {
  onClose: () => void;
  onUpload: (formData: FormData) => Promise<void>;
}

interface UploadFile extends File {
  preview?: string;
}

export const UploadModal: React.FC<UploadModalProps> = ({ onClose, onUpload }) => {
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [description, setDescription] = useState('');
  const [file, setFile] = useState<UploadFile | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      const uploadFile: UploadFile = file;
      uploadFile.preview = URL.createObjectURL(file);
      setFile(uploadFile);
    }
  }, []);

  const { getRootProps, getInputProps } = useDropzone({
    onDrop,
    maxFiles: 1,
    accept: {
      'application/x-executable': [], // Linux executables
      'application/x-mach-binary': [], // macOS executables
      'application/x-msdownload': [] // Windows executables (though not needed here)
    }
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name);
    formData.append('category', category);
    formData.append('description', description);

    await onUpload(formData);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 
      flex items-center justify-center" onClick={onClose}>
      <div 
        className="bg-[#363B54] p-8 rounded-lg w-[600px]" 
        onClick={e => e.stopPropagation()}
      >
        <h2 className="text-xl text-white font-medium mb-6">Upload New App</h2>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          <div {...getRootProps()} className="border-2 border-dashed border-gray-500 
            rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 transition-colors">
            <input {...getInputProps()} />
            {file ? (
              <div className="text-white">
                <p>{file.name}</p>
                <p className="text-sm text-gray-400">Size: {(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            ) : (
              <p className="text-gray-400">Drag and drop an app file, or click to select</p>
            )}
          </div>

          <div className="space-y-4">
            <input
              type="text"
              placeholder="App Name"
              value={name}
              onChange={e => setName(e.target.value)}
              className="w-full px-4 py-3 rounded bg-[#2A2F45] border border-[#454C69] 
                text-white focus:outline-none focus:border-blue-500"
            />
            
            <input
              type="text"
              placeholder="Category"
              value={category}
              onChange={e => setCategory(e.target.value)}
              className="w-full px-4 py-3 rounded bg-[#2A2F45] border border-[#454C69] 
                text-white focus:outline-none focus:border-blue-500"
            />
            
            <textarea
              placeholder="Description"
              value={description}
              onChange={e => setDescription(e.target.value)}
              className="w-full px-4 py-3 rounded bg-[#2A2F45] border border-[#454C69] 
                text-white focus:outline-none focus:border-blue-500 h-32"
            />
          </div>

          <div className="flex justify-end space-x-4">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 rounded text-gray-300 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-6 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 
                transition-colors"
            >
              Upload
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
