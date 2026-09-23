<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
    import PointCloudAnnotationDetails from './PointCloudAnnotationDetails.svelte';

    const base = createAnnotationFixture();
    const baseAnnotation = {
        ...base,
        center: [10.5, -2.3, 1.8] as [number, number, number],
        size: [4.2, 1.9, 1.6] as [number, number, number],
        rotation: [0, 0, Math.sin(Math.PI / 8), Math.cos(Math.PI / 8)] as [
            number,
            number,
            number,
            number
        ]
    };

    const { Story } = defineMeta({
        title: 'Components/PointCloudLabelingWorkspace/PointCloudAnnotationDetails',
        component: PointCloudAnnotationDetails,
        tags: ['autodocs'],
        parameters: { layout: 'padded' },
        args: {
            annotation: baseAnnotation
        }
    });
</script>

<Story name="Default" />

<Story
    name="Without track ID"
    args={{
        annotation: { ...baseAnnotation, trackId: null }
    }}
/>
