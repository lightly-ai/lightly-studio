<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { setTreeAnnotationVisibility } from '$lib/components/AnnotationTree';
    import AnnotationItem from './AnnotationItem.svelte';

    interface Props {
        itemProps: ComponentProps<typeof AnnotationItem>;
        isAnnotationVisible: (annotation: AnnotationView) => boolean;
    }

    let { itemProps, isAnnotationVisible }: Props = $props();

    setTreeAnnotationVisibility(() => isAnnotationVisible);
</script>

<AnnotationItem {...itemProps} />
