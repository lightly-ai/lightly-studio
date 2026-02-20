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
            document.body.classList.add('dark:bg-black', 'bg-background', 'text-foreground');

            return story();
        }
    ]
};

export default preview;
