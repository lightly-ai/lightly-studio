<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { Popover, PopoverContent, PopoverTrigger } from '$lib/components/ui/popover';
    import { useClassifiersMenu } from '$lib/hooks/useClassifiers/useClassifiersMenu';
    import { useSelectionDialog } from '$lib/hooks/useSelectionDialog/useSelectionDialog';
    import { useExportDialog } from '$lib/hooks/useExportDialog/useExportDialog';
    import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';
    import ChevronDown from '@lucide/svelte/icons/chevron-down';
    import ChevronRight from '@lucide/svelte/icons/chevron-right';
    import WandSparklesIcon from '@lucide/svelte/icons/wand-sparkles';
    import BrainCircuitIcon from '@lucide/svelte/icons/brain-circuit';
    import DownloadIcon from '@lucide/svelte/icons/download';
    import SettingsIcon from '@lucide/svelte/icons/settings';

    let {
        isSamples = false,
        hasEmbeddingSearch = false,
        isFSCEnabled = false
    } = $props<{
        isSamples?: boolean;
        hasEmbeddingSearch?: boolean;
        isFSCEnabled?: boolean;
    }>();

    const { openClassifiersMenu } = useClassifiersMenu();
    const { openSelectionDialog } = useSelectionDialog();
    const { openExportDialog } = useExportDialog();
    const { openSettingsDialog } = useSettingsDialog();

    let isMenuOpen = $state(false);

    const hasClassifier = $derived(isSamples && hasEmbeddingSearch && isFSCEnabled);
    const hasSelection = $derived(isSamples);
    const hasExport = $derived(isSamples);

    function handle(callback: () => void) {
        isMenuOpen = false;
        callback();
    }
</script>

<Popover bind:open={isMenuOpen}>
    <PopoverTrigger>
        <Button
            variant="ghost"
            class="nav-button flex items-center space-x-2"
            data-testid="menu-trigger"
        >
            <span>Menu</span>
            <ChevronDown class="size-4" />
        </Button>
    </PopoverTrigger>
    <PopoverContent class="w-64 p-2">
        <div class="flex flex-col">
            {#if hasClassifier}
                <button
                    type="button"
                    class="hover:bg-muted focus-visible:ring-ring flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm transition focus-visible:outline-none focus-visible:ring-2"
                    onclick={() => handle(openClassifiersMenu)}
                    data-testid="menu-classifiers"
                >
                    <div class="flex items-center gap-2">
                        <BrainCircuitIcon class="text-muted-foreground size-4" />
                        <span>Few Shot Classifier</span>
                    </div>
                    <ChevronRight class="text-muted-foreground size-4" />
                </button>
            {/if}
            {#if hasSelection}
                <button
                    type="button"
                    class="hover:bg-muted focus-visible:ring-ring flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm transition focus-visible:outline-none focus-visible:ring-2"
                    onclick={() => handle(openSelectionDialog)}
                    data-testid="menu-selection"
                >
                    <div class="flex items-center gap-2">
                        <WandSparklesIcon class="text-muted-foreground size-4" />
                        <span>Selection</span>
                    </div>
                    <ChevronRight class="text-muted-foreground size-4" />
                </button>
            {/if}
            {#if hasExport}
                <button
                    type="button"
                    class="hover:bg-muted focus-visible:ring-ring flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm transition focus-visible:outline-none focus-visible:ring-2"
                    onclick={() => handle(openExportDialog)}
                    data-testid="menu-export"
                >
                    <div class="flex items-center gap-2">
                        <DownloadIcon class="text-muted-foreground size-4" />
                        <span>Export</span>
                    </div>
                    <ChevronRight class="text-muted-foreground size-4" />
                </button>
            {/if}
            <button
                type="button"
                class="hover:bg-muted focus-visible:ring-ring flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm transition focus-visible:outline-none focus-visible:ring-2"
                onclick={() => handle(openSettingsDialog)}
                data-testid="menu-settings"
            >
                <div class="flex items-center gap-2">
                    <SettingsIcon class="text-muted-foreground size-4" />
                    <span>Settings</span>
                </div>
                <ChevronRight class="text-muted-foreground size-4" />
            </button>
        </div>
    </PopoverContent>
</Popover>
