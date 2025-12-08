import { defineConfig } from '@hey-api/openapi-ts';
import dotenv from 'dotenv';
import path from 'path';

// Load environment variables from .env files
dotenv.config({
    path: [
        // Local development environment variables
        path.resolve(process.cwd(), '.env.local'),
        // Default environment variables
        path.resolve(process.cwd(), '.env')
    ]
});

// Get the base URL from environment variables
const baseUrl = process.env.PUBLIC_LIGHTLY_STUDIO_ADMIN_API_URL;

export default defineConfig({
    input: '../../auth/openapi.json',
    output: {
        format: 'prettier',
        lint: 'eslint',
        path: './src/lib/api/lightly_studio_admin_local'
    },
    plugins: [
        '@hey-api/schemas',
        {
            dates: true,
            name: '@hey-api/transformers'
        },
        {
            enums: 'javascript',
            name: '@hey-api/typescript'
        },
        {
            baseUrl: baseUrl,
            name: '@hey-api/client-fetch'
        },
        {
            name: '@hey-api/sdk',
            transformer: true
        },
        '@tanstack/svelte-query'
    ]
});
