<script lang="ts">
    import type { GridType } from '$lib/types';
    import { ExportSamples, Logo, CreateSelectionDialog } from '$lib/components';
    import { ClassifiersMenu } from '$lib/components/FewShotClassifier';
    import { SettingsDialog } from '$lib/components/Settings';
    import { useFeatureFlags } from '$lib/hooks/useFeatureFlags/useFeatureFlags';
    import { Pencil, Check, Undo2 } from '@lucide/svelte';
    import Button from '../ui/button/button.svelte';
    import { page } from '$app/state';
    import NavigationMenu from '../NavigationMenu/NavigationMenu.svelte';
    import { isSamplesRoute } from '$lib/routes';
    const isSamples = $derived(isSamplesRoute(page.route.id));
    const { featureFlags } = useFeatureFlags();

    const hasEmbeddingSearch = $derived.by(() => {
        return $featureFlags.some((flag) => flag === 'embeddingSearchEnabled');
    });
    const isFSCEnabled = $derived.by(() => {
        return $featureFlags.some((flag) => flag === 'fewShotClassifierEnabled');
    });

    const { setIsEditingMode, isEditingMode, reversibleActions, executeReversibleAction } =
        page.data.globalStorage;
    const { datasetId }: { datasetId: string } = $props();
</script>

<header>
    <div class="p mb-3 border-b border-border-hard bg-card px-4 py-4 pl-8 text-diffuse-foreground">
        <div class="flex justify-between">
            <div class="flex w-[320px]">
                <a href="/"><Logo /></a>
            </div>
            <div class="flex flex-1 justify-start">
                <NavigationMenu {datasetId} />
            </div>
            <div class="flex flex-auto justify-end gap-2">
                {#if isSamples && hasEmbeddingSearch && isFSCEnabled}
                    <ClassifiersMenu />
                {/if}
                {#if isSamples}
                    <CreateSelectionDialog />
                {/if}
                <ExportSamples />

                <SettingsDialog />
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
