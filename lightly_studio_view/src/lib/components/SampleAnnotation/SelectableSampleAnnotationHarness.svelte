<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { SelectableSvgGroup } from '$lib/components';
    import SampleAnnotation from './SampleAnnotation.svelte';
    import { getBoundingBox } from './utils';

    interface Props {
        annotation: ComponentProps<typeof SampleAnnotation>['annotation'];
        imageWidth: number;
        prerenderedDataUrl: string;
        prerenderedHeight: number;
        onSelect: (groupId: string) => void;
    }

    let { annotation, imageWidth, prerenderedDataUrl, prerenderedHeight, onSelect }: Props =
        $props();
</script>

<svg>
    <SelectableSvgGroup groupId={annotation.sample_id} {onSelect} box={getBoundingBox(annotation)}>
        <SampleAnnotation
            {annotation}
            {imageWidth}
            {prerenderedDataUrl}
            {prerenderedHeight}
            showBoundingBox={false}
            isSelectable
        />
    </SelectableSvgGroup>
</svg>
