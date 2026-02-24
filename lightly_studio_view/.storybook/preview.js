import '../src/app.css';

/** @type { import('@storybook/sveltekit').Preview } */
const preview = {
    parameters: {
        controls: {
            matchers: {
                color: /(background|color)$/i,
                date: /Date$/i
            }
        },
        backgrounds: {
            disable: true
        }
    },
    decorators: [
        (story) => {
            // Apply dark class to html element
            document.documentElement.classList.add('dark');

            // Apply body styles like in app.html and app.css
            document.body.classList.add(
                'dark:bg-black',
                'h-screen',
                'w-screen',
                'bg-background',
                'text-foreground'
            );

            // Make storybook-root full height
            const root = document.getElementById('storybook-root');
            if (root) {
                root.classList.add('h-full');
            }

            return story();
        }
    ]
};

export default preview;
