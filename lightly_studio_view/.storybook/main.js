/** @type { import('@storybook/sveltekit').StorybookConfig } */
const config = {
    stories: ['../src/**/*.mdx', '../src/**/*.stories.@(js|ts|svelte)'],
    addons: ['@storybook/addon-svelte-csf', '@storybook/addon-docs'],
    framework: {
        name: '@storybook/sveltekit',
        options: {}
    }
};
export default config;
