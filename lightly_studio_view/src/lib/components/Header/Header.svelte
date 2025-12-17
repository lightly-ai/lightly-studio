<script lang="ts">
    import { Logo } from '$lib/components';
    import { useFeatureFlags } from '$lib/hooks/useFeatureFlags/useFeatureFlags';
    import { useSettings } from '$lib/hooks/useSettings';
    import { isInputElement } from '$lib/utils';
    import { Pencil, Check, Undo2 } from '@lucide/svelte';
    import Button from '../ui/button/button.svelte';
    import { page } from '$app/state';
    import NavigationMenu from '../NavigationMenu/NavigationMenu.svelte';
    import { isSamplesRoute } from '$lib/routes';
    import { useRootDatasetOptions } from '$lib/hooks/useRootDataset/useRootDataset';
    import { get } from 'svelte/store';
    import Menu from '$lib/components/Header/Menu.svelte';
    import { DatasetProgressCompact } from '$lib/components/DatasetProgress';
    import { useDatasetProgress } from '$lib/hooks/useDatasetProgress';
    import { onMount, onDestroy } from 'svelte';

    const isSamples = $derived(isSamplesRoute(page.route.id));
    const { featureFlags } = useFeatureFlags();
    const { settingsStore } = useSettings();

    const hasEmbeddingSearch = $derived.by(() => {
        return $featureFlags.some((flag) => flag === 'embeddingSearchEnabled');
    });
    const isFSCEnabled = $derived.by(() => {
        return $featureFlags.some((flag) => flag === 'fewShotClassifierEnabled');
    });

    const { rootDataset } = useRootDatasetOptions();

    // Get dataset_id from URL params if available
    const dataset_id = $derived(page.params?.dataset_id);

    // Initialize progress tracking when dataset_id is available
    const progressHook = $derived.by(() => {
        if (!dataset_id) return null;
        return useDatasetProgress({
            dataset_id,
            mode: 'polling',
            pollingInterval: 3000
        });
    });

    const progress = $derived(progressHook?.progress);
    const showProgress = $derived(
        !!$progress &&
        $progress.state !== 'ready' &&
        $progress.state !== 'pending'
    );

    // Start polling when component mounts and dataset exists
    onMount(() => {
        if (progressHook && dataset_id) {
            progressHook.startProgress();
        }
    });

    // Cleanup when component unmounts
    onDestroy(() => {
        if (progressHook) {
            progressHook.stopProgress();
        }
    });

    const { setIsEditingMode, isEditingMode, reversibleActions, executeReversibleAction } =
        page.data.globalStorage;

    const handleKeyDown = (event: KeyboardEvent) => {
        if (isInputElement(event.target)) {
            return;
        }

        if (event.key === get(settingsStore).key_toggle_edit_mode) {
            setIsEditingMode(!$isEditingMode);
        }
    };
</script>

<svelte:window onkeydown={handleKeyDown} />

<header>
    <div class="p mb-3 border-b border-border-hard bg-card px-4 py-4 pl-8 text-diffuse-foreground">
        <div class="flex justify-between">
            <div class="flex w-[320px]">
                <a href="/"><Logo /></a>
            </div>
            <div class="flex flex-1 justify-start">
                {#if $rootDataset.data}
                    <NavigationMenu dataset={$rootDataset.data} />
                {/if}
            </div>
            <div class="flex flex-auto justify-end gap-2 items-center">
                {#if showProgress && $progress}
                    <div class="w-48">
                        <DatasetProgressCompact
                            state={$progress.state}
                            current={$progress.current}
                            total={$progress.total}
                        />
                    </div>
                {/if}
                <Menu {isSamples} {hasEmbeddingSearch} {isFSCEnabled} />
                {#if $isEditingMode}
                    <Button
                        data-testid="header-reverse-action-button"
                        variant="outline"
                        class="nav-button flex items-center space-x-2"
                        title={$reversibleActions[0]
                            ? $reversibleActions[0].description
                            : 'No action to undo'}
                        disabled={$reversibleActions.length === 0}
                        onclick={async () => {
                            const latestAction = $reversibleActions[0];
                            if (latestAction) {
                                await executeReversibleAction(latestAction.id);
                            }
                        }}
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
