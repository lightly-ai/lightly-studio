<script lang="ts">
    import { Logo } from '$lib/components';
    import { useHasEmbeddings } from '$lib/hooks/useHasEmbeddings/useHasEmbeddings';
    import { useSettings } from '$lib/hooks/useSettings';
    import { isInputElement } from '$lib/utils';
    import { Pencil, Check, Undo2 } from '@lucide/svelte';
    import Button from '../ui/button/button.svelte';
    import { page } from '$app/state';
    import NavigationMenu from '../NavigationMenu/NavigationMenu.svelte';
    import { isSamplesRoute } from '$lib/routes';
    import { get } from 'svelte/store';
    import Menu from '$lib/components/Header/Menu.svelte';
    import type { CollectionView } from '$lib/api/lightly_studio_local';
    import { useCollectionWithChildren } from '$lib/hooks/useCollection/useCollection';
    import UserAvatar from '$lib/components/UserAvatar/UserAvatar.svelte';
    import useAuth from '$lib/hooks/useAuth/useAuth';

    let { collection }: { collection: CollectionView } = $props();

    const isSamples = $derived(isSamplesRoute(page.route.id));
    const { settingsStore } = useSettings();

    const hasEmbeddingsQuery = useHasEmbeddings({ collectionId: collection.collection_id });
    const hasEmbeddings = $derived(!!$hasEmbeddingsQuery.data);

    const datasetId = $derived(page.params.dataset_id!);
    const { collection: datasetCollection } = $derived.by(() => useCollectionWithChildren({ collectionId: datasetId }));

    const { setIsEditingMode, isEditingMode, reversibleActions, executeReversibleAction } =
        page.data.globalStorage;

    const handleKeyDown = (event: KeyboardEvent) => {
        if (isInputElement(event.target)) {
            return;
        }
        if (event.key === get(settingsStore).key_toggle_edit_mode) {
            setIsEditingMode(!$isEditingMode);
        } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
            executeUndoAction();
        }
    };

    const executeUndoAction = async () => {
        const latestAction = $reversibleActions[0];
        if (latestAction) {
            await executeReversibleAction(latestAction.id);
        }
    };

    const { user } = useAuth();
</script>

<svelte:window onkeydown={handleKeyDown} />

<header>
    <div class="p mb-3 border-b border-border-hard bg-card px-4 py-4 pl-8 text-diffuse-foreground">
        <div class="flex justify-between">
            <div class="flex w-[320px]">
                {#if $datasetCollection.data && !Array.isArray($datasetCollection.data)}
                    {@const dataset = $datasetCollection.data}
                    <a
                        href="/datasets/{dataset.collection_id}/{dataset.sample_type.toLowerCase()}/{dataset.collection_id}"><Logo /></a
                    >
                {:else}
                    <a href="/"><Logo /></a>
                {/if}
            </div>
            <div class="flex flex-1 justify-start">
                {#if $datasetCollection.data && !Array.isArray($datasetCollection.data)}
                    <NavigationMenu collection={$datasetCollection.data} />
                {/if}
            </div>
            <div class="flex flex-auto justify-end gap-2">
                <Menu {isSamples} {hasEmbeddings} {collection} />
                {#if $isEditingMode}
                    <Button
                        data-testid="header-reverse-action-button"
                        variant="outline"
                        class="nav-button flex items-center space-x-2"
                        title={$reversibleActions[0]
                            ? $reversibleActions[0].description
                            : 'No action to undo'}
                        disabled={$reversibleActions.length === 0}
                        onclick={executeUndoAction}
                    >
                        <Undo2 class="size-4" />
                        <span>Undo</span>
                    </Button>
                    <Button
                        data-testid="header-editing-mode-button"
                        class="nav-button flex items-center space-x-2"
                        onclick={() => setIsEditingMode(false)}
                        title="Finish Editing"
                    >
                        <Check class="size-4" />
                        <span>Finish Editing</span>
                    </Button>
                {:else}
                    <Button
                        data-testid="header-editing-mode-button"
                        variant="outline"
                        class="nav-button flex items-center space-x-2"
                        onclick={() => setIsEditingMode(true)}
                        title="Edit Annotations"
                    >
                        <Pencil class="size-4" />
                        <span>Edit Annotations</span>
                    </Button>
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
        @media screen and (max-width: 1300px) {
            .nav-button > span {
                display: none;
            }
        }
    }
</style>
