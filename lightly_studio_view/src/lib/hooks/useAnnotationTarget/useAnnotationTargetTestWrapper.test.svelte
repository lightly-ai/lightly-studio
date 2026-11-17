<script lang="ts">
    import { onMount } from 'svelte';
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import {
        createAnnotationLabelContext,
        type AnnotationLabelContext
    } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useAnnotationTarget } from './useAnnotationTarget.svelte';
    import { useSetTargetSource } from './useSetTargetSource';

    interface Props {
        annotations?: AnnotationView[];
        hiddenIds?: Set<string>;
        onReady: (
            context: AnnotationLabelContext,
            setTargetSource: ReturnType<typeof useSetTargetSource>
        ) => void;
    }

    const { annotations = [], hiddenIds = new Set(), onReady }: Props = $props();

    const context = createAnnotationLabelContext();
    useAnnotationTarget({
        getCollectionId: () => 'col-1',
        getAnnotations: () => annotations,
        getHiddenIds: () => hiddenIds
    });
    const setTargetSource = useSetTargetSource(() => 'col-1');
    onMount(() => onReady(context, setTargetSource));
</script>

<output data-testid="target-source">{context.annotationSource ?? 'none'}</output>
