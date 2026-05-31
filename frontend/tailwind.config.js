/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f4ff',
          100: '#e0e9ff',
          500: '#4f63d2',
          600: '#3d4fc0',
          700: '#2d3a9e',
          900: '#1a2166',
        },
      },
    },
  },
  plugins: [],
}
