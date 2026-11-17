<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import { setTreeAnnotationVisibility } from '$lib/components/AnnotationTree';
    import AnnotationClassificationGridItem from './AnnotationClassificationGridItem.svelte';

    interface Props {
        itemProps: ComponentProps<typeof AnnotationClassificationGridItem>;
        isAnnotationVisible: (annotation: AnnotationView) => boolean;
    }

    let { itemProps, isAnnotationVisible }: Props = $props();

    setTreeAnnotationVisibility(() => isAnnotationVisible);
</script>

<AnnotationClassificationGridItem {...itemProps} />
