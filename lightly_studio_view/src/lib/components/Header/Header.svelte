<script lang="ts">
    import { Logo } from '$lib/components';
    import { useHasEmbeddings } from '$lib/hooks/useHasEmbeddings/useHasEmbeddings';
    import { useSettings } from '$lib/hooks/useSettings';
    import { isInputElement } from '$lib/utils';
    import { page } from '$app/state';
    import NavigationMenu from '../NavigationMenu/NavigationMenu.svelte';
    import { isImagesRoute, isMcapSequencesRoute, isVideosRoute } from '$lib/routes';
    import { get } from 'svelte/store';
    import Menu from '$lib/components/Header/Menu.svelte';
    import type { CollectionView } from '$lib/api/lightly_studio_local';
    import { useCollectionWithChildren } from '$lib/hooks/useCollection/useCollection';
    import UserAvatar from '$lib/components/UserAvatar/UserAvatar.svelte';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';
    import { useCanNavigateDataset } from '$lib/hooks/useCanNavigateDataset/useCanNavigateDataset';
    import { EditModeControls, useEditModeControls } from '$lib/components/EditModeControls';

    interface Props {
        collection: CollectionView;
        showTour?: boolean;
        onShowTour?: () => void;
    }

    let { collection, showTour = false, onShowTour }: Props = $props();

    const isImages = $derived(isImagesRoute(page.route.id));
    const isVideos = $derived(isVideosRoute(page.route.id));
    const isPointClouds = $derived(isMcapSequencesRoute(page.route.id));
    const { settingsStore } = useSettings();

    const hasEmbeddingsQuery = useHasEmbeddings(() => ({ collectionId: collection.collection_id }));
    const hasEmbeddings = $derived(!!hasEmbeddingsQuery.data);

    const datasetId = $derived(page.params.dataset_id!);
    const { collection: datasetCollection } = useCollectionWithChildren({
        getCollectionId: () => datasetId
    });

    const { isEditingMode, setEditMode, undo } = useEditModeControls(
        () => collection.collection_id
    );

    const handleKeyDown = (event: KeyboardEvent) => {
        if (isInputElement(event.target)) {
            return;
        }

        if (!hasMinimumRole(user?.role, 'labeler')) {
            return;
        }
        if (event.key === get(settingsStore).key_toggle_edit_mode) {
            setEditMode(!$isEditingMode, 'keyboard_shortcut');
        } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
            void undo('keyboard_shortcut');
        }
    };

    const { user } = useAuth();
    const canNavigateDataset = useCanNavigateDataset();
</script>

<svelte:window onkeydown={handleKeyDown} />

<header>
    <div class="p mb-3 border-b border-border-hard bg-card px-4 py-4 pl-8 text-diffuse-foreground">
        <div class="flex items-center justify-between">
            <div class="flex w-[320px]">
                {#if !canNavigateDataset}
                    <!-- Labelers work in their batches: home is the workspace projects page,
                         which lives in another app on this origin. -->
                    <a
                        href="/workspace/projects"
                        data-sveltekit-reload
                        data-testid="header-logo-link"><Logo /></a
                    >
                {:else if datasetCollection.data}
                    {@const dataset = datasetCollection.data}
                    <a
                        href="/datasets/{dataset.collection_id}/{dataset.sample_type.toLowerCase()}/{dataset.collection_id}"
                        data-testid="header-logo-link"
                    >
                        <Logo />
                    </a>
                {:else}
                    <a href="/" data-testid="header-logo-link"><Logo /></a>
                {/if}
            </div>
            <div class="flex flex-1 justify-start">
                {#if canNavigateDataset && datasetCollection.data}
                    <NavigationMenu collection={datasetCollection.data} />
                {/if}
            </div>
            <div class="flex flex-auto justify-end gap-2">
                <Menu
                    {isImages}
                    {isVideos}
                    {isPointClouds}
                    {hasEmbeddings}
                    {collection}
                    {user}
                    {showTour}
                    {onShowTour}
                />
                {#if hasMinimumRole(user?.role, 'labeler')}
                    <EditModeControls
                        collectionId={collection.collection_id}
                        testIdPrefix="header"
                    />
                {/if}
                {#if user}
                    <div data-testid="header-user-avatar">
                        <UserAvatar {user} />
                    </div>
                {/if}
            </div>
        </div>
    </div>
</header>

<style>
    :global {
        @media screen and (min-width: 1101px) {
            .menu-trigger > .lucide-menu {
                display: none;
            }
        }

        @media screen and (max-width: 1100px) {
            .menu-trigger {
                width: 2.5rem;
                justify-content: center;
                padding: 0;
            }

            .nav-button > span {
                display: none;
            }

            .menu-trigger > .lucide-chevron-down {
                display: none;
            }
        }
    }
</style>
