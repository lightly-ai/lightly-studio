<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import ImageSearchDisplay from './ImageSearchDisplay.svelte';

    const { Story } = defineMeta({
        title: 'Components/CollectionSearch/ImageSearchDisplay',
        component: ImageSearchDisplay,
        tags: ['autodocs']
    });
</script>

<Story
    name="Default"
    args={{
        activeImage: 'search.png',
        previewUrl: null,
        dragOver: false,
        onClear: () => undefined
    }}
    asChild
>
    {#snippet children(args)}
        <ImageSearchDisplay {...args} />
    {/snippet}
</Story>

<Story
    name="With Preview"
    args={{
        activeImage: 'search.png',
        previewUrl: 'https://via.placeholder.com/40',
        dragOver: false,
        onClear: () => undefined
    }}
    asChild
>
    {#snippet children(args)}
        <ImageSearchDisplay {...args} />
    {/snippet}
</Story>
