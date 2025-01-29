import React, { useState } from 'react';
import { adminLogin } from '../../services/auth';

interface LoginModalProps {
    onLoginSuccess: () => void;
    onClose: () => void;
}

const LoginModal: React.FC<LoginModalProps> = ({ onLoginSuccess, onClose }) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [keepSignedIn, setKeepSignedIn] = useState(false);

    const handleLogin = async () => {
        try {
            const result = await adminLogin(email, password);
            if (result.success) {
                console.log('Admin login successful');
                console.log('Login response:', result);
                
                const storedStatus = await window.electronAPI.checkAdmin();
                console.log('Stored admin status:', storedStatus);
                
                onLoginSuccess();
            } else {
                console.error('Login failed:', result.error);
            }
        } catch (error) {
            console.error('Login error:', error);
        }
    };

    return (
        <div style={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: '440px',
            backgroundColor: '#363B54',
            padding: '40px',
            borderRadius: '8px',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
            zIndex: 1000
        }}>
            <button 
                onClick={onClose}
                className="absolute top-4 right-4 text-white/60 hover:text-white/90 
                    transition-colors text-2xl leading-none w-8 h-8 flex items-center 
                    justify-center focus:outline-none"
                aria-label="Close modal"
            >
                ×
            </button>

            <h2 className="text-center text-xl text-white font-medium mb-8">
                Admin Login
            </h2>

            <div className="space-y-6">
                <div>
                    <label className="block text-gray-300 text-sm mb-2">
                        USERNAME
                    </label>
                    <input
                        type="text"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full px-4 py-3 rounded bg-[#2A2F45] border border-[#454C69] 
                        text-white focus:outline-none focus:border-blue-500 transition-colors"
                    />
                </div>

                <div>
                    <label className="block text-gray-300 text-sm mb-2">
                        PASSWORD
                    </label>
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full px-4 py-3 rounded bg-[#2A2F45] border border-[#454C69] 
                        text-white focus:outline-none focus:border-blue-500 transition-colors"
                    />
                </div>

                <div className="flex items-center">
                    <input
                        type="checkbox"
                        id="keepSignedIn"
                        checked={keepSignedIn}
                        onChange={(e) => setKeepSignedIn(e.target.checked)}
                        className="w-4 h-4 rounded bg-[#2A2F45] border border-[#454C69]"
                    />
                    <label htmlFor="keepSignedIn" className="ml-2 text-gray-300 text-sm">
                        KEEP ME SIGNED IN
                    </label>
                </div>

                <button
                    onClick={handleLogin}
                    className="w-full py-3 bg-blue-600 text-white rounded hover:bg-blue-700 
                    transition-colors font-medium"
                >
                    SIGN IN
                </button>

                <div className="text-center">
                    <a href="#" className="text-sm text-gray-400 hover:text-gray-300 transition-colors">
                        Forgot your password?
                    </a>
                </div>
            </div>
        </div>
    );
};

export default LoginModal;
