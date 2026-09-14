<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import PointCloudViewer from './PointCloudViewer.svelte';
    import { generateCube } from './mockPointCloud';

    const cloud = generateCube(10, 150_000);

    const { Story } = defineMeta({
        title: 'Components/PointCloudViewer',
        component: PointCloudViewer,
        tags: ['autodocs'],
        parameters: {
            layout: 'fullscreen'
        },
        argTypes: {
            batch: { control: false },
            colorMode: {
                control: 'select',
                options: ['none', 'intensity', 'height']
            },
            pointSize: { control: { type: 'range', min: 1, max: 10, step: 0.5 } },
            intensityRange: { control: false }
        },
        args: {
            batch: cloud,
            colorMode: 'intensity',
            pointSize: 2
        }
    });
</script>

<Story name="Default">
    {#snippet template(args)}
        <div class="h-screen w-screen bg-black p-2">
            <PointCloudViewer {...args} />
        </div>
    {/snippet}
</Story>
