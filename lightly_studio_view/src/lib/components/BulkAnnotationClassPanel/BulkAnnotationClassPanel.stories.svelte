<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import BulkAnnotationClassPanel from './BulkAnnotationClassPanel.svelte';

    const annotationClasses = [
        { id: '1', name: 'dog' },
        { id: '2', name: 'cat' },
        { id: '3', name: 'horse' }
    ];

    const { Story } = defineMeta({
        title: 'Components/BulkAnnotationClassPanel',
        component: BulkAnnotationClassPanel,
        tags: ['autodocs'],
        args: {
            selectedCount: 12,
            annotationClasses,
            annotationSources: ['ground_truth', 'predictions'],
            selectedSource: 'ground_truth',
            isApplying: false,
            onSourceChange: () => {},
            onApply: () => {}
        }
    });
</script>

{#snippet sidePanel(args)}
    <!-- Mimics the right side-panel width from the collection layout. -->
    <div class="w-[320px]">
        <BulkAnnotationClassPanel {...args} />
    </div>
{/snippet}

<Story name="No selection" args={{ selectedCount: 0 }} template={sidePanel} />

<Story name="Selection" template={sidePanel} />

<Story name="Single image" args={{ selectedCount: 1 }} template={sidePanel} />

<Story name="Applying" args={{ isApplying: true }} template={sidePanel} />
