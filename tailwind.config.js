
// tailwind.config.js
module.exports = {
  darkMode: 'class',
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Light Theme
        purple: {
          50: '#FAF5FF',
          100: '#F3E8FF',
          200: '#E9D5FF',
          300: '#D8B4FE',
          400: '#C084FC',
          500: '#A855F7',
          600: '#9333EA',
          700: '#7C3AED',
          800: '#6D28D9',
          900: '#581C87',
          primary: '#8B5CF6',     // Light theme primary
          'primary-dark': '#A78BFA', // Dark theme primary
        },
        mint: {
          50: '#ECFDF5',
          100: '#D1FAE5',
          200: '#A7F3D0',
          300: '#6EE7B7',
          400: '#34D399',
          500: '#10B981',
          600: '#059669',
          700: '#047857',
          800: '#065F46',
          900: '#064E3B',
          accent: '#10B981',      // Light theme accent
          'accent-dark': '#34D399', // Dark theme accent (glowing)
          dark: '#0F0F1A',        // Dark background
          studio: '#F9FAFB',      // Light background
        },
        surface: {
          light: '#FFFFFF',
          dark: '#252538',
        },
        gold: '#FBBF24',          // Super-Only Accent
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        heading: ['Poppins', 'Inter', 'sans-serif'],
        accent: ['Space Grotesk', 'Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
      backgroundImage: {
        'gradient-purple-mint': 'linear-gradient(135deg, #8B5CF6 0%, #10B981 100%)',
        'gradient-purple': 'linear-gradient(135deg, #A855F7 0%, #7C3AED 100%)',
        'gradient-mint': 'linear-gradient(135deg, #10B981 0%, #34D399 100%)',
        'gradient-super': 'linear-gradient(135deg, #7C3AED 0%, #FBBF24 100%)',
        'gradient-dark': 'linear-gradient(180deg, #0F0F1A 0%, #1A1A2E 100%)',
        'gradient-light': 'linear-gradient(180deg, #FAFAFA 0%, #FFFFFF 100%)',
      },
      boxShadow: {
        'purple-glow': '0 0 20px -5px rgba(139, 92, 246, 0.5)',
        'mint-glow': '0 0 20px -5px rgba(16, 185, 129, 0.5)',
        'purple-glow-lg': '0 0 40px -10px rgba(139, 92, 246, 0.6)',
        'mint-glow-lg': '0 0 40px -10px rgba(16, 185, 129, 0.6)',
        'glass': '0 8px 32px 0 rgba(31, 38, 135, 0.15)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'rotate-360': 'rotate360 0.5s ease-in-out',
        'coin-drop': 'coinDrop 0.6s ease-out',
        'float': 'float 3s ease-in-out infinite',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(139, 92, 246, 0.5)' },
          '100%': { boxShadow: '0 0 20px rgba(139, 92, 246, 0.8)' },
        },
        rotate360: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        coinDrop: {
          '0%': { transform: 'translateY(-20px)', opacity: 0 },
          '50%': { transform: 'translateY(5px)', opacity: 1 },
          '100%': { transform: 'translateY(0)', opacity: 1 },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
      backdropBlur: {
        'glass': '16px',
      },
      borderRadius: {
        '4xl': '2rem',
      },
    },
  },
  plugins: [],
}
