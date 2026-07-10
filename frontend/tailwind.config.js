/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        background: '#FCFBF9',
        foreground: '#2C2C2C',
        card: { DEFAULT: '#FFFFFF', foreground: '#2C2C2C' },
        border: 'rgba(44, 44, 44, 0.09)',
        primary: { DEFAULT: '#315B4C', foreground: '#FCFBF9' },
        secondary: { DEFAULT: '#F4F0EA', foreground: '#2C2C2C' },
        muted: { DEFAULT: '#F4F0EA', foreground: '#6B6B6B' },
        accent: { DEFAULT: '#C7D7CE', foreground: '#315B4C' },
      },
      fontFamily: {
        heading: ['Manrope', 'sans-serif'],
        body: ['Plus Jakarta Sans', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
