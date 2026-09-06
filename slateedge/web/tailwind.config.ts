import type { Config } from 'tailwindcss';

// SlateEdge original dark theme: graphite base, deep navy panels, teal accents
// for informative content, amber for warnings/risk. Deliberately distinct from
// any competing DFS product's palette or layout.
const config: Config = {
  darkMode: ['class'],
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        graphite: {
          950: '#0b0d10',
          900: '#111418',
          800: '#171b21',
          700: '#20252c',
          600: '#2b323b',
        },
        navy: {
          900: '#0e1b2b',
          800: '#132540',
          700: '#1a3357',
          600: '#234674',
        },
        teal: {
          500: '#2dd4bf',
          400: '#5eead4',
          300: '#99f6e4',
        },
        amber: {
          500: '#f59e0b',
          400: '#fbbf24',
          300: '#fcd34d',
        },
        rose: {
          500: '#f43f5e',
          400: '#fb7185',
        },
        ink: {
          50: '#f4f6f8',
          200: '#c9d2dc',
          400: '#8b97a6',
          600: '#5b6673',
        },
      },
      borderRadius: {
        lg: '0.75rem',
        md: '0.5rem',
        sm: '0.375rem',
      },
    },
  },
  plugins: [],
};

export default config;
