<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import BulkClassificationPanel from './BulkClassificationPanel.svelte';

    const { Story } = defineMeta({
        title: 'Components/BulkClassificationPanel',
        component: BulkClassificationPanel
    });
</script>

<Story
    name="Default"
    args={{
        selectedCount: 10,
        sourceName: 'ground_truth',
        className: 'dog',
        sourceNames: ['ground_truth', 'prediction'],
        classNames: ['cat', 'dog'],
        onSourceSelect: () => undefined,
        onClassSelect: () => undefined,
        onApply: () => undefined
    }}
/>
