/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // VIRTUS Brand Theme - Vermelho & Branco
        virtus: {
          bg: {
            primary: '#0c0c10',
            secondary: '#121216',
            tertiary: '#1a1a1f',
            card: '#16161b',
            hover: '#202027',
          },
          border: {
            primary: '#2a2a32',
            secondary: '#3a3a44',
            accent: '#E53935',
          },
          text: {
            primary: '#ffffff',
            secondary: '#b0b0b8',
            muted: '#707078',
          },
          accent: {
            primary: '#E53935',      // Vermelho Virtus
            secondary: '#FF5252',    // Vermelho claro
            success: '#10b981',
            warning: '#f59e0b',
            danger: '#ef4444',
            info: '#64b5f6',
          },
          gradient: {
            start: '#E53935',
            end: '#FF5252',
          },
          brand: {
            red: '#E53935',
            redLight: '#FF5252',
            redDark: '#C62828',
          }
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'virtus': '0 4px 6px -1px rgba(0, 0, 0, 0.5), 0 2px 4px -2px rgba(0, 0, 0, 0.5)',
        'virtus-lg': '0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -4px rgba(0, 0, 0, 0.5)',
        'glow': '0 0 20px rgba(229, 57, 53, 0.3)',
        'glow-red': '0 0 25px rgba(229, 57, 53, 0.4)',
        'glow-success': '0 0 20px rgba(16, 185, 129, 0.3)',
        'glow-danger': '0 0 20px rgba(239, 68, 68, 0.3)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(229, 57, 53, 0.3)' },
          '100%': { boxShadow: '0 0 20px rgba(229, 57, 53, 0.5)' },
        }
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-virtus': 'linear-gradient(135deg, #E53935 0%, #FF5252 100%)',
      },
    },
  },
  plugins: [],
}
