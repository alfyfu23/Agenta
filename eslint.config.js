import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'

export default [
    js.configs.recommended,
    ...pluginVue.configs['flat/recommended'],
    {
        files: ['src/**/*.{js,vue}', 'vite.config.js'],
        languageOptions: {
            ecmaVersion: 2020,
            sourceType: 'module',
            globals: {
                window: 'readonly',
                document: 'readonly',
                console: 'readonly',
                setTimeout: 'readonly',
                setInterval: 'readonly',
                clearInterval: 'readonly',
                clearTimeout: 'readonly',
                URL: 'readonly',
                Blob: 'readonly',
                fetch: 'readonly',
                alert: 'readonly',
                confirm: 'readonly',
                FormData: 'readonly',
                File: 'readonly',
                navigator: 'readonly',
                location: 'readonly',
            },
        },
        rules: {
            'vue/multi-word-component-names': 'off',
            'vue/no-unused-vars': 'warn',
            'vue/require-default-prop': 'off',
            'vue/require-explicit-emits': 'off',
            'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
            'no-console': 'warn',
            'no-empty': ['error', { allowEmptyCatch: true }],
        },
    },
    {
        ignores: ['dist/**', 'node_modules/**'],
    },
]
