<script lang="ts">
    import type { AnnotationView, ImageAnnotationView } from '$lib/api/lightly_studio_local';

    interface Props {
        annotation: AnnotationView;
        image: ImageAnnotationView;
        containerWidth: number;
        containerHeight: number;
        cachedCollectionVersion: string;
        showLabel: boolean;
        selected?: boolean;
    }

    let {
        image,
        containerWidth,
        containerHeight,
        cachedCollectionVersion,
        showLabel,
        selected = false
    }: Props = $props();
</script>

<div
    data-testid="mock-image-grid-item"
    data-sample-id={image?.sample_id}
    data-container-width={containerWidth}
    data-container-height={containerHeight}
    data-cached-version={cachedCollectionVersion}
    data-show-label={showLabel}
    data-selected={selected}
></div>
