<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import ImageSearchDisplay from './ImageSearchDisplay.svelte';
    import { fn } from 'storybook/test';

    const { Story } = defineMeta({
        title: 'Components/CollectionSearch/ImageSearchDisplay',
        component: ImageSearchDisplay,
        tags: ['autodocs']
    });
</script>

<Story
    name="Default"
    args={{
        onClear: fn()
    }}
>
    {#snippet template(args)}
        <ImageSearchDisplay {...args} />
    {/snippet}
</Story>

<Story
    name="With Preview"
    args={{
        previewUrl: 'https://picsum.photos/150?random=1',
        onClear: fn()
    }}
>
    {#snippet template(args)}
        <ImageSearchDisplay {...args} />
    {/snippet}
</Story>
