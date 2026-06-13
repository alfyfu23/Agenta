/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#6da34d',
        secondary: '#f1f5f9',
        neutral: '#64748b',
        placeholder: '#94a3b8',
        light: '#f8fafc',
        border: '#e2e8f0',
        speaker1: '#9CC932', // 张小明-绿色
        speaker2: '#3B82F6', // 李华-蓝色
        speaker3: '#F97316', // 王芳-橙色
        export: '#8B5CF6', // 紫色用于导出按钮
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
} 
