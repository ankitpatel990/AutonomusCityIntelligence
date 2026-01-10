/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Traffic light colors
        'signal-red': '#EF4444',
        'signal-yellow': '#F59E0B',
        'signal-green': '#22C55E',
        
        // Density levels
        'density-low': '#22C55E',
        'density-medium': '#F59E0B',
        'density-high': '#EF4444',
        'density-jam': '#991B1B',
        
        // Mode colors
        'mode-normal': '#3B82F6',
        'mode-emergency': '#EF4444',
        'mode-incident': '#F59E0B',
        'mode-failsafe': '#6B7280',
        
        // UI Theme - Cyberpunk/Tech aesthetic
        'primary': '#0EA5E9',
        'secondary': '#8B5CF6',
        'accent': '#06B6D4',
        'background': '#0F172A',
        'surface': '#1E293B',
        'border': '#334155',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 3s linear infinite',
        'bounce-slow': 'bounce 2s infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px #06B6D4, 0 0 10px #06B6D4' },
          '100%': { boxShadow: '0 0 10px #06B6D4, 0 0 20px #06B6D4, 0 0 30px #06B6D4' },
        },
      },
      fontFamily: {
        'sans': ['Outfit', 'Inter', 'system-ui', 'sans-serif'],
        'mono': ['JetBrains Mono', 'Fira Code', 'monospace'],
        'display': ['Orbitron', 'sans-serif'],
      },
      backgroundImage: {
        'grid-pattern': 'linear-gradient(rgba(6, 182, 212, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(6, 182, 212, 0.03) 1px, transparent 1px)',
        'gradient-radial': 'radial-gradient(ellipse at center, var(--tw-gradient-stops))',
      },
      backgroundSize: {
        'grid': '50px 50px',
      },
    },
  },
  plugins: [],
}
