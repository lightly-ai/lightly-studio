<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import Typography from './Typography.svelte';
    import { TYPOGRAPHY_VARIANTS, COMPONENT_TYPES } from './constants';

    const { Story } = defineMeta({
        title: 'Components/Typography',
        component: Typography,
        tags: ['autodocs'],
        argTypes: {
            variant: {
                control: 'select',
                options: [...TYPOGRAPHY_VARIANTS]
            },
            component: {
                control: 'select',
                options: [...COMPONENT_TYPES]
            }
        },
        parameters: {
            backgrounds: {
                default: 'dark'
            }
        }
    });
</script>

<Story name="H1" args={{ variant: 'h1' }}>Heading 1 - Large Page Title</Story>

<Story name="H2" args={{ variant: 'h2' }}>Heading 2 - Section Title</Story>

<Story name="H3" args={{ variant: 'h3' }}>Heading 3 - Subsection Title</Story>

<Story name="H4" args={{ variant: 'h4' }}>Heading 4 - Component Title</Story>

<Story name="H5" args={{ variant: 'h5' }}>Heading 5 - Small Section</Story>

<Story name="H6" args={{ variant: 'h6' }}>Heading 6 - Smallest Heading</Story>

<Story name="Body1" args={{ variant: 'body1' }}>
    Body 1 - This is the default body text variant. It's perfect for regular paragraphs and most
    text content in your application.
</Story>

<Story name="Body2" args={{ variant: 'body2' }}>
    Body 2 - A smaller body text variant. Great for secondary information or text that should be
    less prominent than Body1.
</Story>

<Story name="Subtitle1" args={{ variant: 'subtitle1' }}>
    Subtitle 1 - Medium-weight subtitle text for important secondary information.
</Story>

<Story name="Subtitle2" args={{ variant: 'subtitle2' }}>
    Subtitle 2 - Smaller medium-weight subtitle text.
</Story>

<Story name="Caption" args={{ variant: 'caption' }}>
    Caption - Small text for image captions, footnotes, or annotations.
</Story>

<Story name="Overline" args={{ variant: 'overline' }}>
    Overline - Small uppercase text for category labels or section markers
</Story>

<Story name="Custom Component" args={{ variant: 'h1', component: 'div' }}>
    H1 Styling on a Div Element
</Story>

<Story name="Custom Class" args={{ variant: 'body1', class: 'text-blue-500 underline' }}>
    Body text with custom styling applied via className
</Story>

<Story name="All Variants Showcase">
    {#snippet children()}
        <div class="space-y-4">
            <Typography variant="h1">H1 - Large Page Title</Typography>
            <Typography variant="h2">H2 - Section Title</Typography>
            <Typography variant="h3">H3 - Subsection Title</Typography>
            <Typography variant="h4">H4 - Component Title</Typography>
            <Typography variant="h5">H5 - Small Section</Typography>
            <Typography variant="h6">H6 - Smallest Heading</Typography>
            <Typography variant="subtitle1">Subtitle 1 - Important secondary text</Typography>
            <Typography variant="subtitle2">Subtitle 2 - Smaller subtitle</Typography>
            <Typography variant="body1"
                >Body 1 - Default body text for paragraphs and content</Typography
            >
            <Typography variant="body2">Body 2 - Smaller body text for secondary content</Typography
            >
            <Typography variant="caption"
                >Caption - Small text for footnotes and annotations</Typography
            >
            <Typography variant="overline">Overline - Category Labels</Typography>
        </div>
    {/snippet}
</Story>
