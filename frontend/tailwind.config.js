/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        raxel: {
          indigo: '#1F1B4D',
          'indigo-deep': '#151236',
          'indigo-light': '#2D286B',
          white: '#FFFFFF',
          'soft-white': '#FFFFFF',
          'surface-subtle': '#F9FAFB',
          'surface-hover': '#F3F4F6',
          ink: '#111827',
          muted: '#667085',
          faint: '#667085',
          violet: '#1F1B4D',
          'violet-soft': '#F0EFFB',
          'violet-muted': '#DCD9F5',
          'teal-deep': '#1F1B4D',
          teal: '#1F1B4D',
          'teal-light': '#F0EFFB',
          border: '#E5E7EB',
          'border-focus': '#1F1B4D',
          'border-subtle': '#E5E7EB',
        },
        status: {
          'success-bg': '#ECFDF5',
          'success-text': '#065F46',
          'success-border': '#A7F3D0',
          'warning-bg': '#FFFBEB',
          'warning-text': '#92400E',
          'warning-border': '#FDE68A',
          'danger-bg': '#FEF2F2',
          'danger-text': '#991B1B',
          'danger-border': '#FCA5A5',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      borderRadius: {
        'xs': '4px',
        'sm': '6px',
        'md': '8px',
        'lg': '12px',
        'xl': '16px',
      },
      boxShadow: {
        'sm': '0 1px 3px rgba(27, 25, 56, 0.05)',
        'md': '0 4px 16px rgba(27, 25, 56, 0.08)',
        'lg': '0 12px 36px rgba(14, 12, 31, 0.12)',
        'glow': '0 0 24px rgba(201, 180, 250, 0.25)',
      },
      animation: {
        'fade-in': 'fadeInSlideUp 0.22s ease-out forwards',
        'float': 'floatCard 7s ease-in-out infinite',
        'glow': 'atmosphericGlow 14s ease-in-out infinite',
      },
      keyframes: {
        fadeInSlideUp: {
          'from': { opacity: '0', transform: 'translateY(8px)' },
          'to': { opacity: '1', transform: 'translateY(0)' },
        },
        floatCard: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-6px)' },
        },
        atmosphericGlow: {
          '0%, 100%': { opacity: '0.5', transform: 'scale(1) translate(0, 0)' },
          '50%': { opacity: '0.75', transform: 'scale(1.08) translate(10px, -10px)' },
        },
      }
    },
  },
  plugins: [],
}
