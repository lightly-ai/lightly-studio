<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { Popover, PopoverContent, PopoverTrigger } from '$lib/components/ui/popover';
    import { useClassifiersMenu } from '$lib/hooks/useClassifiers/useClassifiersMenu';
    import { useSelectionDialog } from '$lib/hooks/useSelectionDialog/useSelectionDialog';
    import { useExportDialog } from '$lib/hooks/useExportDialog/useExportDialog';
    import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';
    import { useOperatorsDialog } from '$lib/hooks/useOperatorsDialog/useOperatorsDialog';
    import {
        ChevronDown,
        ChevronRight,
        Puzzle as PuzzleIcon,
        Download as DownloadIcon,
        Settings as SettingsIcon,
        BrainCircuit as BrainCircuitIcon,
        WandSparkles as WandSparklesIcon
    } from '@lucide/svelte';

    import type { CollectionView } from '$lib/api/lightly_studio_local';

    let {
        isSamples = false,
        isVideos = false,
        hasEmbeddings = false,
        collection
    } = $props<{
        isSamples?: boolean;
        isVideos?: boolean;
        hasEmbeddings?: boolean;
        collection: CollectionView;
    }>();

    const { openClassifiersMenu } = useClassifiersMenu();
    const { openSelectionDialog } = useSelectionDialog();
    const { openExportDialog } = useExportDialog();
    const { openSettingsDialog } = useSettingsDialog();
    const { openOperatorsDialog } = useOperatorsDialog();

    let isMenuOpen = $state(false);

    type MenuIcon = typeof BrainCircuitIcon;
    type MenuItem = {
        icon: MenuIcon;
        label: string;
        onSelect: () => void;
        testId: string;
    };

    const hasClassifier = $derived(isSamples && hasEmbeddings);
    const hasSelection = $derived(isSamples || isVideos);
    const hasExport = $derived(collection.sample_type == 'image');

    const menuItems = $derived.by<MenuItem[]>(() => {
        const items: MenuItem[] = [];

        if (hasClassifier) {
            items.push({
                icon: BrainCircuitIcon,
                label: 'Few Shot Classifier',
                onSelect: openClassifiersMenu,
                testId: 'menu-classifiers'
            });
        }

        if (hasSelection) {
            items.push({
                icon: WandSparklesIcon,
                label: 'Selection',
                onSelect: openSelectionDialog,
                testId: 'menu-selection'
            });
        }

        items.push({
            icon: PuzzleIcon,
            label: 'Plugins',
            onSelect: openOperatorsDialog,
            testId: 'menu-operators'
        });

        if (hasExport) {
            items.push({
                icon: DownloadIcon,
                label: 'Export',
                onSelect: openExportDialog,
                testId: 'menu-export'
            });
        }

        items.push({
            icon: SettingsIcon,
            label: 'Settings',
            onSelect: openSettingsDialog,
            testId: 'menu-settings'
        });

        return items;
    });

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
            {#each menuItems as item (item.testId)}
                <button
                    type="button"
                    class="flex w-full items-center justify-between rounded px-3 py-2 text-left text-sm transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    onclick={() => handle(item.onSelect)}
                    data-testid={item.testId}
                >
                    <div class="flex items-center gap-2">
                        <item.icon class="size-4 text-muted-foreground" />
                        <span>{item.label}</span>
                    </div>
                    <ChevronRight class="size-4 text-muted-foreground" />
                </button>
            {/each}
        </div>
    </PopoverContent>
</Popover>
