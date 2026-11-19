<script lang="ts">
    import { Logo } from '$lib/components';
    import { Button } from '$lib/components';
    import { useHasEmbeddings } from '$lib/hooks/useHasEmbeddings/useHasEmbeddings';
    import { useSettings } from '$lib/hooks/useSettings';
    import { isInputElement } from '$lib/utils';
    import Pencil from '@lucide/svelte/icons/pencil';
    import Check from '@lucide/svelte/icons/check';
    import Undo2 from '@lucide/svelte/icons/undo-2';
    import LoaderCircle from '@lucide/svelte/icons/loader-circle';
    import { toast } from 'svelte-sonner';
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
    import { usePostHog } from '$lib/hooks';

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

    const { setIsEditingMode, isEditingMode, reversibleActions, executeReversibleAction } =
        page.data.globalStorage;

    const { trackEvent } = usePostHog();

    type TriggeredBy = 'click' | 'keyboard_shortcut';

    const setEditMode = (active: boolean, triggeredBy: TriggeredBy) => {
        if (active) {
            trackEvent('edit_mode_started', {
                collection_id: collection.collection_id,
                triggered_by: triggeredBy
            });
        }
        setIsEditingMode(active);
    };

    // An undo stays in the history until it is complete, so a second undo must wait.
    let isUndoing = $state(false);

    const executeUndoAction = async (triggeredBy: TriggeredBy) => {
        const latestAction = $reversibleActions[0];
        if (!latestAction || isUndoing) return;
        trackEvent('edit_undo', {
            collection_id: collection.collection_id,
            triggered_by: triggeredBy
        });
        isUndoing = true;
        try {
            await executeReversibleAction(latestAction.id);
        } catch {
            toast.error('Failed to undo. Please try again.');
        } finally {
            isUndoing = false;
        }
    };

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
            void executeUndoAction('keyboard_shortcut');
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
                        data-testid="header-logo-link"><Logo /></a
                    >
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
                    {#if $isEditingMode}
                        <Button
                            icon={isUndoing ? LoaderCircle : Undo2}
                            iconClass={isUndoing ? 'animate-spin' : undefined}
                            buttonProps={{
                                onclick: () => executeUndoAction('click'),
                                disabled: isUndoing || $reversibleActions.length === 0,
                                'aria-busy': isUndoing,
                                title: $reversibleActions[0]
                                    ? $reversibleActions[0].description
                                    : 'No action to undo',
                                'data-testid': 'header-reverse-action-button',
                                class: 'nav-button'
                            }}
                        >
                            Undo
                        </Button>
                        <Button
                            icon={Check}
                            buttonProps={{
                                onclick: () => setEditMode(false, 'click'),
                                title: 'Finish Editing',
                                'data-testid': 'header-editing-mode-button',
                                class: 'nav-button'
                            }}
                        >
                            Finish Editing
                        </Button>
                    {:else}
                        <Button
                            icon={Pencil}
                            buttonProps={{
                                onclick: () => setEditMode(true, 'click'),
                                title: 'Edit annotations',
                                'data-testid': 'header-editing-mode-button',
                                class: 'nav-button'
                            }}
                        >
                            Edit annotations
                        </Button>
                    {/if}
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
