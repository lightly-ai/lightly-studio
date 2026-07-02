import baseConfig from './eslint.config.js';

export default [
    ...baseConfig,
    {
        files: ['**/*.{js,ts,svelte}'],
        rules: {
            complexity: ['error', { max: 10 }]
        }
    }
];
