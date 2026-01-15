<script lang="ts">
    import { ClassifiersMenu } from '$lib/components';
    import type { PageData } from './$types';

    const { data }: { data: PageData } = $props();
    const { collectionId } = data;
</script>

<ClassifiersMenu {collectionId} />
