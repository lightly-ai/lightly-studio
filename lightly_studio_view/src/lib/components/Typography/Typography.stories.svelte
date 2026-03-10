<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import Typography from './Typography.svelte';

    const { Story } = defineMeta({
        title: 'Components/Typography',
        component: Typography,
        tags: ['autodocs'],
        argTypes: {
            variant: {
                control: 'select',
                options: [
                    'h1',
                    'h2',
                    'h3',
                    'h4',
                    'h5',
                    'h6',
                    'body1',
                    'body2',
                    'caption',
                    'overline',
                    'subtitle1',
                    'subtitle2'
                ]
            },
            component: {
                control: 'select',
                options: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'div']
            }
        }
    });
</script>

<Story name="H1" args={{ variant: 'h1' }}>
    {#snippet children()}
        Heading 1 - Large Page Title
    {/snippet}
</Story>

<Story name="H2" args={{ variant: 'h2' }}>
    {#snippet children()}
        Heading 2 - Section Title
    {/snippet}
</Story>

<Story name="H3" args={{ variant: 'h3' }}>
    {#snippet children()}
        Heading 3 - Subsection Title
    {/snippet}
</Story>

<Story name="H4" args={{ variant: 'h4' }}>
    {#snippet children()}
        Heading 4 - Component Title
    {/snippet}
</Story>

<Story name="H5" args={{ variant: 'h5' }}>
    {#snippet children()}
        Heading 5 - Small Section
    {/snippet}
</Story>

<Story name="H6" args={{ variant: 'h6' }}>
    {#snippet children()}
        Heading 6 - Smallest Heading
    {/snippet}
</Story>

<Story name="Body1" args={{ variant: 'body1' }}>
    {#snippet children()}
        Body 1 - This is the default body text variant. It's perfect for regular paragraphs and most
        text content in your application.
    {/snippet}
</Story>

<Story name="Body2" args={{ variant: 'body2' }}>
    {#snippet children()}
        Body 2 - A smaller body text variant. Great for secondary information or text that should be
        less prominent than Body1.
    {/snippet}
</Story>

<Story name="Subtitle1" args={{ variant: 'subtitle1' }}>
    {#snippet children()}
        Subtitle 1 - Medium-weight subtitle text for important secondary information.
    {/snippet}
</Story>

<Story name="Subtitle2" args={{ variant: 'subtitle2' }}>
    {#snippet children()}
        Subtitle 2 - Smaller medium-weight subtitle text.
    {/snippet}
</Story>

<Story name="Caption" args={{ variant: 'caption' }}>
    {#snippet children()}
        Caption - Small text for image captions, footnotes, or annotations.
    {/snippet}
</Story>

<Story name="Overline" args={{ variant: 'overline' }}>
    {#snippet children()}
        Overline - Small uppercase text for category labels or section markers
    {/snippet}
</Story>

<Story name="Custom Component" args={{ variant: 'h1', component: 'div' }}>
    {#snippet children()}
        H1 Styling on a Div Element
    {/snippet}
</Story>

<Story name="Custom Class" args={{ variant: 'body1', class: 'text-blue-500 underline' }}>
    {#snippet children()}
        Body text with custom styling applied via className
    {/snippet}
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
