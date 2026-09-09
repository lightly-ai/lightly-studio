<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import PointCloudLabelingWorkspace from './PointCloudLabelingWorkspace.svelte';

    const { Story } = defineMeta({
        title: 'Components/PointCloudLabelingWorkspace',
        component: PointCloudLabelingWorkspace,
        tags: ['autodocs'],
        args: {
            sampleId: 'sample-1234',
            sourcePath: [
                { label: 'Home', href: '#' },
                { label: 'City drive recordings', href: '#' },
                { label: 'run-2026-04-18 · frame 128' }
            ],
            onExit: fn(),
            onRetry: fn()
        }
    });
</script>

{#snippet frame(args)}
    <div class="h-full w-full">
        <PointCloudLabelingWorkspace {...args} />
    </div>
{/snippet}

<Story name="Empty (no frames yet, default)" args={{ status: 'empty' }} template={frame} />

<Story name="Unsupported sample" args={{ status: 'unsupported' }} template={frame} />

<Story name="Recoverable error" args={{ status: 'error' }} template={frame} />
