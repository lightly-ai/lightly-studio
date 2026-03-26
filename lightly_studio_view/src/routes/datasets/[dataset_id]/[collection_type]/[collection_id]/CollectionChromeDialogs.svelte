<script lang="ts">
    import type { CollectionViewWithCount } from '$lib/api/lightly_studio_local';
    import CreateClassifierDialog from '$lib/components/FewShotClassifier/CreateClassifierDialog.svelte';
    import RefineClassifierDialog from '$lib/components/FewShotClassifier/RefineClassifierDialog.svelte';
    import MenuDialogHost from '$lib/components/Header/MenuDialogHost.svelte';

    const {
        collection,
        hasEmbeddings,
        isSamples,
        isVideos
    }: {
        collection: CollectionViewWithCount;
        hasEmbeddings: boolean;
        isSamples: boolean;
        isVideos: boolean;
    } = $props();
</script>

<MenuDialogHost {collection} {isSamples} {isVideos} {hasEmbeddings} />

{#if hasEmbeddings}
    <CreateClassifierDialog />
    <RefineClassifierDialog />
{/if}
