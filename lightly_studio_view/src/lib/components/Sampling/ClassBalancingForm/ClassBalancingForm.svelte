<script lang="ts">
    import type { AnnotationCollectionView } from '$lib/api/lightly_studio_local/types.gen';
    import { type BalancingMode } from '$lib/components/Sampling/balancingMode';
    import AnnotationSourceSelect from '$lib/components/AnnotationSourceSelect/AnnotationSourceSelect.svelte';
    import BalancingModeSelect from './BalancingModeSelect.svelte';

    interface Props {
        balancingMode: BalancingMode;
        annotationCollections: AnnotationCollectionView[];
        annotationSourceId: string;
        onBalancingModeChange: (mode: BalancingMode) => void;
        onAnnotationSourceChange: (annotationSourceId: string) => void;
    }

    let {
        balancingMode,
        annotationCollections,
        annotationSourceId,
        onBalancingModeChange,
        onAnnotationSourceChange
    }: Props = $props();

    const sourceOptions = $derived(
        annotationCollections.map((collection) => ({
            id: collection.collection_id,
            name: collection.name
        }))
    );
</script>

<BalancingModeSelect {balancingMode} {onBalancingModeChange} />

<AnnotationSourceSelect
    {sourceOptions}
    selectedSource={annotationSourceId}
    onSelect={onAnnotationSourceChange}
/>
