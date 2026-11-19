<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import ExtensionSlot from './ExtensionSlot.svelte';

    const { Story } = defineMeta({
        title: 'Extensions/ExtensionSlot',
        component: ExtensionSlot,
        tags: ['autodocs']
    });
</script>

<Story
    name="Default Content"
    args={{
        name: 'dataset.toolbar',
        props: { datasetId: 'dataset-1', collectionId: 'collection-1' }
    }}
>
    Shown when nothing is registered for the slot.
</Story>
