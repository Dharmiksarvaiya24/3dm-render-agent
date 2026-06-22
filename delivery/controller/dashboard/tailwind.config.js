/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: '#db6a6a',
        'on-surface': '#eddfe0',
        'on-surface-variant': '#d7c1c3',
        'outline-variant': 'rgba(219, 106, 106, 0.15)',
        error: '#ffb4ab',
        tertiary: '#98d4a8',
        surface: '#181212',
        'surface-container': 'rgba(37, 30, 31, 0.6)',
        'surface-container-low': 'rgba(32, 26, 27, 0.4)',
        'surface-container-high': 'rgba(47, 40, 41, 0.5)',
        'surface-bright': '#1a1a1a',
        outline: 'rgba(159, 140, 142, 0.5)',
      },
      fontFamily: {
        display: ['Inter', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      spacing: {
        xs: '4px',
        sm: '8px',
        md: '16px',
        lg: '24px',
        xl: '32px',
        '2xl': '48px',
        '3xl': '64px',
        margin: '24px',
        gutter: '24px',
      },
      borderRadius: {
        DEFAULT: '2px',
        lg: '4px',
        xl: '8px',
        full: '9999px',
      },
    },
  },
  plugins: [],
};
