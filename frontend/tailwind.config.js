/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Su temalı marka paleti
        brand: {
          50: '#eff9ff',
          100: '#def2ff',
          200: '#b6e7ff',
          300: '#75d5ff',
          400: '#2cc0ff',
          500: '#02a8f4',
          600: '#0086d1',
          700: '#016aa9',
          800: '#065a8b',
          900: '#0b4b73',
          950: '#072f4c',
        },
        surface: {
          light: '#ffffff',
          'light-alt': '#f6f8fb',
          dark: '#0f172a',
          'dark-alt': '#1e293b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.04)',
        'card-hover': '0 4px 12px -2px rgb(0 0 0 / 0.10), 0 2px 6px -2px rgb(0 0 0 / 0.06)',
        panel: '0 10px 40px -12px rgb(0 0 0 / 0.25)',
      },
      keyframes: {
        'fade-in': { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-down': {
          '0%': { opacity: '0', transform: 'translateY(-8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: { '100%': { transform: 'translateX(100%)' } },
      },
      animation: {
        'fade-in': 'fade-in 0.2s ease-out',
        'slide-up': 'slide-up 0.25s ease-out',
        'slide-down': 'slide-down 0.2s ease-out',
      },
    },
  },
  plugins: [],
}
