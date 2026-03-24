<script lang="ts">
    import { browser } from '$app/environment';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import type { CollectionView, SampleType } from '$lib/api/lightly_studio_local';
    import GridHeader from '$lib/components/GridHeader/GridHeader.svelte';
    import Header from '$lib/components/Header/Header.svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage.js';
    import { useHideAnnotations } from '$lib/hooks/useHideAnnotations';
    import {
        isAnnotationDetailsRoute,
        isAnnotationsRoute,
        isCaptionsRoute,
        isGroupDetailsRoute,
        isGroupsRoute,
        isSampleDetailsRoute,
        isSamplesRoute,
        isVideoDetailsRoute,
        isVideoFramesRoute,
        isVideosRoute,
        routeHelpers
    } from '$lib/routes';
    import type { GridType } from '$lib/types';
    import { GripVertical } from '@lucide/svelte';
    import { onDestroy, onMount } from 'svelte';

    type CollectionChromeDialogsModule = typeof import('./CollectionChromeDialogs.svelte');
    type CollectionFooterModule = typeof import('./CollectionFooter.svelte');
    type CollectionSidebarModule = typeof import('./CollectionSidebar.svelte');
    type CollectionToolbarModule = typeof import('./CollectionToolbar.svelte');
    type PlotPanelModule = typeof import('$lib/components/PlotPanel/PlotPanel.svelte');
    type PaneforgeModule = typeof import('paneforge');
    type IdleWindow = Window & typeof globalThis & {
        requestIdleCallback?: (callback: () => void) => number;
    };

    const { data, children } = $props();
    const {
        collection,
        globalStorage: {
            setLastGridType,
            clearSelectedSamples,
            clearSelectedSampleAnnotationCrops
        }
    } = $derived(data);

    const datasetId = $derived(page.params.dataset_id!);
    const collectionId = $derived(page.params.collection_id!);

    const { handleKeyEvent } = useHideAnnotations();
    const { retrieveParentCollection, collections, setCollection, showPlot, setShowPlot } =
        useGlobalStorage();

    const parentCollection = $derived.by(() =>
        retrieveParentCollection($collections, collectionId)
    );

    const isSamples = $derived(isSamplesRoute(page.route.id));
    const isGroups = $derived(isGroupsRoute(page.route.id));
    const isGroupDetails = $derived(isGroupDetailsRoute(page.route.id));
    const isAnnotations = $derived(isAnnotationsRoute(page.route.id));
    const isSampleDetails = $derived(isSampleDetailsRoute(page.route.id));
    const isAnnotationDetails = $derived(isAnnotationDetailsRoute(page.route.id));
    const isCaptions = $derived(isCaptionsRoute(page.route.id));
    const isVideos = $derived(isVideosRoute(page.route.id));
    const isVideoFrames = $derived(isVideoFramesRoute(page.route.id));
    const isVideoDetails = $derived(isVideoDetailsRoute(page.route.id));
    const showLeftSidebar = $derived(
        isSamples || isAnnotations || isVideos || isVideoFrames || isGroups
    );

    let gridType = $state<GridType>('samples');
    let lastCollectionId: string | null = null;

    $effect(() => {
        let nextGridType: GridType | null = null;
        if (isAnnotations) {
            nextGridType = 'annotations';
        } else if (isSamples) {
            nextGridType = 'samples';
        } else if (isCaptions) {
            nextGridType = 'captions';
        } else if (isVideoFrames) {
            nextGridType = 'video_frames';
        } else if (isVideos) {
            nextGridType = 'videos';
        } else if (isGroups) {
            nextGridType = 'groups';
        }

        if (!nextGridType) {
            return;
        }

        if (lastCollectionId && lastCollectionId !== collectionId) {
            clearSelectedSamples(lastCollectionId);
            clearSelectedSampleAnnotationCrops(lastCollectionId);
        }

        gridType = nextGridType;
        lastCollectionId = collectionId;
        setLastGridType(gridType);
    });

    let CollectionChromeDialogsComponent = $state<CollectionChromeDialogsModule['default'] | null>(
        null
    );
    let CollectionFooterComponent = $state<CollectionFooterModule['default'] | null>(null);
    let CollectionSidebarComponent = $state<CollectionSidebarModule['default'] | null>(null);
    let CollectionToolbarComponent = $state<CollectionToolbarModule['default'] | null>(null);
    let PlotPanelComponent = $state<PlotPanelModule['default'] | null>(null);
    let PaneGroupComponent = $state<PaneforgeModule['PaneGroup'] | null>(null);
    let PaneComponent = $state<PaneforgeModule['Pane'] | null>(null);
    let PaneResizerComponent = $state<PaneforgeModule['PaneResizer'] | null>(null);
    let chromeReady = $state(false);
    let hasEmbeddings = $state(false);
    let plotEnabledInSession = $state(false);

    const loadChromeComponents = async () => {
        if (!browser || CollectionToolbarComponent) {
            return;
        }

        const [toolbarModule, sidebarModule, footerModule, dialogsModule] = await Promise.all([
            import('./CollectionToolbar.svelte'),
            import('./CollectionSidebar.svelte'),
            import('./CollectionFooter.svelte'),
            import('./CollectionChromeDialogs.svelte')
        ]);

        CollectionToolbarComponent = toolbarModule.default;
        CollectionSidebarComponent = sidebarModule.default;
        CollectionFooterComponent = footerModule.default;
        CollectionChromeDialogsComponent = dialogsModule.default;
    };

    const loadPlotLayout = async () => {
        if (!browser || PlotPanelComponent || !((isSamples || isVideos) && hasEmbeddings)) {
            return;
        }

        const [{ default: PlotPanel }, paneforge] = await Promise.all([
            import('$lib/components/PlotPanel/PlotPanel.svelte'),
            import('paneforge')
        ]);

        PlotPanelComponent = PlotPanel;
        PaneGroupComponent = paneforge.PaneGroup;
        PaneComponent = paneforge.Pane;
        PaneResizerComponent = paneforge.PaneResizer;
    };

    $effect(() => {
        if (chromeReady && plotEnabledInSession && (isSamples || isVideos) && $showPlot) {
            void loadPlotLayout();
        }
    });

    function scheduleChromeHydration() {
        const run = () => {
            chromeReady = true;
            void loadChromeComponents();
        };

        const idleWindow = window as IdleWindow;
        if (idleWindow.requestIdleCallback) {
            idleWindow.requestIdleCallback(() => {
                run();
            });
            return;
        }

        window.setTimeout(run, 1);
    }

    async function verifyRouteConsistency() {
        if (!browser) {
            return;
        }

        if (datasetId === collectionId) {
            if (collection.parent_collection_id !== null) {
                await goto(routeHelpers.toHome(), { replaceState: true });
            }
            return;
        }

        try {
            const { readCollection, readCollectionHierarchy } = await import(
                '$lib/api/lightly_studio_local/sdk.gen'
            );
            const [{ data: datasetCollection }, { data: hierarchyData }] = await Promise.all([
                readCollection({
                    path: { collection_id: datasetId }
                }),
                readCollectionHierarchy({
                    path: { collection_id: datasetId }
                })
            ]);

            if (!datasetCollection || datasetCollection.parent_collection_id !== null) {
                await goto(routeHelpers.toHome(), { replaceState: true });
                return;
            }

            setCollection(datasetCollection);

            const hierarchy = hierarchyData ?? [];
            for (const hierarchyCollection of hierarchy) {
                setCollection(hierarchyCollection);
            }

            const collectionExists = hierarchy.some(
                (candidate: CollectionView) => candidate.collection_id === collectionId
            );

            if (!collectionExists) {
                await goto(routeHelpers.toHome(), { replaceState: true });
            }
        } catch {
            await goto(routeHelpers.toHome(), { replaceState: true });
        }
    }

    onMount(() => {
        if (!browser) {
            return;
        }

        window.addEventListener('keydown', handleKeyEvent);
        window.addEventListener('keyup', handleKeyEvent);
        scheduleChromeHydration();
        void verifyRouteConsistency();
    });

    onDestroy(() => {
        if (!browser) {
            return;
        }

        window.removeEventListener('keydown', handleKeyEvent);
        window.removeEventListener('keyup', handleKeyEvent);
    });

    const toolbarProps = $derived({
        collectionId,
        isAnnotations,
        isGroups,
        isSamples,
        isVideos,
        plotEnabled: plotEnabledInSession,
        showPlot: $showPlot,
        onTogglePlot: () => {
            plotEnabledInSession = true;
            setShowPlot(!$showPlot);
        },
        onHasEmbeddingsChange: (value: boolean) => {
            hasEmbeddings = value;
        }
    });

    const parentCollectionId = $derived(parentCollection?.collectionId ?? collection.parent_collection_id);
    const parentSampleType = $derived(parentCollection?.sampleType as SampleType | null | undefined);
</script>

<div class="flex-none">
    <Header {collection} {hasEmbeddings} />
    {#if CollectionChromeDialogsComponent}
        <CollectionChromeDialogsComponent
            {collection}
            {hasEmbeddings}
            {isSamples}
            {isVideos}
        />
    {/if}
</div>

<div class="relative flex min-h-0 flex-1 flex-col">
    {#if isSampleDetails || isAnnotationDetails || isGroupDetails || isVideoDetails}
        {@render children()}
    {:else}
        <div class="flex min-h-0 flex-1 space-x-4 px-4">
            {#if showLeftSidebar}
                {#if CollectionSidebarComponent}
                    <CollectionSidebarComponent
                        {collectionId}
                        {datasetId}
                        {gridType}
                        {isAnnotations}
                        {isSamples}
                        {isVideoFrames}
                        {isVideos}
                        {parentCollectionId}
                        {parentSampleType}
                    />
                {:else}
                    <div class="flex h-full min-h-0 w-80 flex-col">
                        <div class="flex min-h-0 flex-1 flex-col rounded-[1vw] bg-card py-4">
                            <div class="space-y-3 px-4">
                                <div class="h-10 rounded-md bg-muted/60"></div>
                                <div class="h-24 rounded-md bg-muted/40"></div>
                                <div class="h-32 rounded-md bg-muted/30"></div>
                            </div>
                        </div>
                    </div>
                {/if}
            {/if}

            {#if (isSamples || isVideos) &&
            plotEnabledInSession &&
            $showPlot &&
            PaneGroupComponent &&
            PaneComponent &&
            PaneResizerComponent &&
            PlotPanelComponent}
                <PaneGroupComponent direction="horizontal" class="flex-1">
                    <PaneComponent defaultSize={50} minSize={30} class="flex">
                        <div class="flex flex-1 flex-col space-y-4 rounded-[1vw] bg-card p-4">
                            {#if CollectionToolbarComponent}
                                <CollectionToolbarComponent {...toolbarProps} />
                            {:else}
                                <GridHeader>
                                    <div class="h-10 w-full rounded-md bg-muted/40"></div>
                                </GridHeader>
                                <div class="mb-4 h-px bg-border-hard"></div>
                            {/if}
                            <div class="flex min-h-0 flex-1 overflow-hidden">
                                {@render children()}
                            </div>
                        </div>
                    </PaneComponent>

                    <PaneResizerComponent
                        class="relative mx-2 flex w-1 cursor-col-resize items-center justify-center"
                    >
                        <div class="bg-brand z-10 flex h-7 min-w-5 items-center justify-center">
                            <GripVertical class="text-diffuse-foreground" />
                        </div>
                    </PaneResizerComponent>

                    <PaneComponent defaultSize={50} minSize={30} class="flex min-h-0 flex-col">
                        <PlotPanelComponent />
                    </PaneComponent>
                </PaneGroupComponent>
            {:else}
                <div class="flex flex-1 flex-col space-y-4 rounded-[1vw] bg-card p-4 pb-2">
                    {#if CollectionToolbarComponent}
                        <CollectionToolbarComponent {...toolbarProps} />
                    {:else if isSamples || isAnnotations || isVideos || isGroups}
                        <GridHeader>
                            <div class="h-10 w-full rounded-md bg-muted/40"></div>
                        </GridHeader>
                        <div class="mb-4 h-px bg-border-hard"></div>
                    {/if}

                    <div class="flex min-h-0 flex-1">
                        {@render children()}
                    </div>
                </div>
            {/if}
        </div>
        {#if CollectionFooterComponent}
            <CollectionFooterComponent
                {collection}
                {collectionId}
                {datasetId}
                {isAnnotations}
                {isVideoFrames}
                {isVideos}
                {parentCollectionId}
                {parentSampleType}
            />
        {/if}
    {/if}
</div>
