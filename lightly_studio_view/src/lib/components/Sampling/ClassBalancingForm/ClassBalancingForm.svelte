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

    const sourceNames = $derived(annotationCollections.map((collection) => collection.name));
</script>

<BalancingModeSelect {balancingMode} {onBalancingModeChange} />

<AnnotationSourceSelect
    {sourceNames}
    selectedSource={annotationSourceId}
    onSelect={onAnnotationSourceChange}
/>
