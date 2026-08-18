/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0b1220',
        surface: '#111a2e',
        'surface-2': '#17223b',
        border: '#1e2a45',
        accent: '#2563eb',
        'accent-2': '#0ea5e9',
        green: '#10b981',
        red: '#ef4444',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glow: '0 8px 24px -8px rgba(37, 99, 235, 0.45)',
        'glow-green': '0 8px 24px -8px rgba(16, 185, 129, 0.4)',
        card: '0 1px 0 rgba(255,255,255,0.03) inset, 0 8px 24px -12px rgba(0,0,0,0.6)',
      },
      letterSpacing: {
        tightest: '-0.02em',
      },
    },
  },
  plugins: [],
}
