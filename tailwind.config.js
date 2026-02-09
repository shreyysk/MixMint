
// tailwind.config.js
module.exports = {
  darkMode: 'class',
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        mint: {
          dark: '#0D0214',    // Deep Obsidian
          studio: '#F9F5FF',  // Studio White
          primary: '#A855F7', // Electric Purple
          secondary: '#7E22CE', // Royal Purple
          accent: '#D8B4FE',  // Lavender Glow
          gold: '#FBBF24',    // Super-Only Accent
        },
      },
      backgroundImage: {
        'mint-gradient': 'linear-gradient(135deg, #A855F7 0%, #7E22CE 100%)',
        'super-gradient': 'linear-gradient(135deg, #7E22CE 0%, #FBBF24 100%)',
      },
      boxShadow: {
        'purple-glow': '0 0 20px -5px rgba(168, 85, 247, 0.5)',
      }
    },
  },
  plugins: [],
}
