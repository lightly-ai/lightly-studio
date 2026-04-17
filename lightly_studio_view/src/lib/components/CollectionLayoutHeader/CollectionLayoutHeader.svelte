<script lang="ts">
    import { Header } from '$lib/components';
    import MenuDialogHost from '$lib/components/Header/MenuDialogHost.svelte';
    import type { useRouteType } from '$lib/hooks/useRouteType/useRouteType';
    import type { Collection } from '$lib/types';

    const {
        collection,
        routeType,
        hasEmbeddings
    }: {
        collection: Collection;
        routeType: ReturnType<typeof useRouteType>;
        hasEmbeddings: boolean;
    } = $props();
</script>

<Header {collection} />
<MenuDialogHost
    isSamples={routeType.isSamples}
    isVideos={routeType.isVideos}
    {hasEmbeddings}
    {collection}
/>
