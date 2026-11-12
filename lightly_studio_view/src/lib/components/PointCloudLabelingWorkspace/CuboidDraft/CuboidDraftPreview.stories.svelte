<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { Canvas, T } from '@threlte/core';
    import { OrbitControls } from '@threlte/extras';
    import CuboidDraftPreview from './CuboidDraftPreview.svelte';

    const { Story } = defineMeta({
        title: 'Components/PointCloudLabelingWorkspace/CuboidDraftPreview',
        component: CuboidDraftPreview,
        tags: ['autodocs'],
        parameters: { layout: 'fullscreen' },
        args: { box: { center: [0, 0, 1], size: [4, 3, 2] } }
    });
</script>

<Story
    name="Preview box"
    parameters={{
        docs: {
            description: {
                story: 'Translucent white box with white edges shown while a cuboid is being drawn.'
            }
        }
    }}
>
    {#snippet template(args)}
        <div class="h-screen w-screen bg-black">
            <Canvas>
                <T.Color attach="background" args={['#10141c']} />
                <T.PerspectiveCamera position={[10, -12, 8]} makeDefault fov={50} up={[0, 0, 1]}>
                    <OrbitControls target={[0, 0, 1]} enableDamping />
                </T.PerspectiveCamera>
                <T.GridHelper
                    args={[24, 24, '#344054', '#202938']}
                    rotation={[Math.PI / 2, 0, 0]}
                />
                <CuboidDraftPreview {...args} />
            </Canvas>
        </div>
    {/snippet}
</Story>
