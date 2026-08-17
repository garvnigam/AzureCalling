/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0a0b10',
        surface: '#12141d',
        'surface-2': '#1a1d2b',
        border: '#1f2233',
        accent: '#7c5cfc',
        'accent-2': '#5b8def',
        green: '#34d399',
        red: '#f87171',
      },
      fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'] },
      boxShadow: {
        glow: '0 4px 20px rgba(124, 92, 252, 0.3)',
        'glow-green': '0 4px 20px rgba(52, 211, 153, 0.25)',
      },
    },
  },
  plugins: [],
}