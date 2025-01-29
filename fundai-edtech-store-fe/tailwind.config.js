module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Light mode colors
        primary: {
          50: '#f0f9ff',  // Very light blue
          100: '#e0f2fe', // Light blue
          200: '#bae6fd', // Soft blue
          300: '#7dd3fc', // Medium blue
          400: '#38bdf8', // Bright blue
          500: '#0ea5e9', // Main blue
          600: '#0284c7', // Dark blue
          700: '#0369a1', // Deeper blue
          800: '#075985', // Very dark blue
          900: '#0c4a6e', // Darkest blue
        },
        // Dark mode surface colors (educational/calm)
        surface: {
          dark: '#1a1f2e',    // Deep navy background
          'dark-lighter': '#242b3d', // Slightly lighter navy
          'dark-accent': '#2d364a', // Accent surface
        },
        // Accent colors (for both modes)
        accent: {
          teal: '#4fd1c5',    // Calm teal
          indigo: '#818cf8',  // Soft indigo
          purple: '#a78bfa',  // Gentle purple
        },
        // Neutral colors
        neutral: {
          light: '#f8fafc',
          dark: '#0f172a',
        },
        // Status colors
        status: {
          success: '#10b981', // Green
          warning: '#f59e0b', // Amber
          error: '#ef4444',   // Red
          info: '#3b82f6',    // Blue
        }
      }
    },
  },
  plugins: [],
}
