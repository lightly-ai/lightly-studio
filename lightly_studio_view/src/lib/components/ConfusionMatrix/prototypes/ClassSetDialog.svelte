<script lang="ts">
    import { Check as CheckIcon } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button/index.js';
    import { Checkbox } from '$lib/components/ui/checkbox/index.js';
    import * as Command from '$lib/components/ui/command/index.js';
    import * as Dialog from '$lib/components/ui/dialog/index.js';
    import { Input } from '$lib/components/ui/input/index.js';
    import { Slider } from '$lib/components/ui/slider/index.js';
    import * as Tabs from '$lib/components/ui/tabs/index.js';
    import { cn } from '$lib/utils';
    import {
        CLASS_SORT_LABELS,
        type ClassSetConfig,
        type ClassSortOption,
        type ColorConfig
    } from './topNMatrix';

    interface Props {
        open: boolean;
        allClasses: string[];
        config: ClassSetConfig;
        color: ColorConfig;
        onApply: (config: ClassSetConfig, color: ColorConfig) => void;
    }

    let { open = $bindable(), allClasses, config, color, onApply }: Props = $props();

    // Draft state, synced from the applied config every time the dialog opens.
    let draft: ClassSetConfig = $state({ ...config });
    let colorDraft: ColorConfig = $state({ ...color });
    $effect(() => {
        if (open) {
            draft = { ...config, manualClasses: [...config.manualClasses] };
            colorDraft = { ...color };
        }
    });

    const sortOptions = Object.keys(CLASS_SORT_LABELS) as ClassSortOption[];

    const toggleManual = (className: string) => {
        draft.manualClasses = draft.manualClasses.includes(className)
            ? draft.manualClasses.filter((c) => c !== className)
            : [...draft.manualClasses, className];
    };

    const apply = () => {
        onApply(
            { ...draft, n: Math.min(Math.max(draft.n, 1), allClasses.length) },
            { ...colorDraft }
        );
        open = false;
    };
</script>

<Dialog.Root bind:open>
    <Dialog.Content class="max-w-[420px]">
        <Dialog.Header>
            <Dialog.Title>Configure classes</Dialog.Title>
            <Dialog.Description>
                Choose which classes the confusion matrix shows.
            </Dialog.Description>
        </Dialog.Header>
        <Tabs.Root bind:value={draft.mode}>
            <Tabs.List class="grid w-full grid-cols-2">
                <Tabs.Trigger value="topN">Top N</Tabs.Trigger>
                <Tabs.Trigger value="manual">Manual</Tabs.Trigger>
            </Tabs.List>
            <Tabs.Content value="topN" class="space-y-3 pt-2">
                <label class="flex items-center justify-between gap-2 text-sm">
                    Number of classes
                    <Input
                        type="number"
                        min={1}
                        max={allClasses.length}
                        bind:value={draft.n}
                        class="h-8 w-24"
                        data-testid="class-set-top-n"
                    />
                </label>
                <label class="flex items-center justify-between gap-2 text-sm">
                    Sort by
                    <select
                        bind:value={draft.sortBy}
                        class="h-8 rounded-md border bg-background px-2 text-sm"
                        data-testid="class-set-sort-by"
                    >
                        {#each sortOptions as option (option)}
                            <option value={option}>{CLASS_SORT_LABELS[option]}</option>
                        {/each}
                    </select>
                </label>
            </Tabs.Content>
            <Tabs.Content value="manual" class="pt-2">
                <div class="mb-1 flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">
                        {draft.manualClasses.length} of {allClasses.length} selected
                    </span>
                    <div class="flex gap-1">
                        <Button
                            variant="ghost"
                            size="sm"
                            class="h-6 px-2 text-xs"
                            onclick={() => (draft.manualClasses = [...allClasses])}
                        >
                            Select all
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            class="h-6 px-2 text-xs"
                            onclick={() => (draft.manualClasses = [])}
                        >
                            Clear
                        </Button>
                    </div>
                </div>
                <Command.Root class="rounded-md border">
                    <Command.Input placeholder="Search classes..." data-testid="class-set-search" />
                    <Command.List class="max-h-[220px] dark:[color-scheme:dark]">
                        <Command.Empty>No class found.</Command.Empty>
                        {#each allClasses as className (className)}
                            <Command.Item
                                value={className}
                                onSelect={() => toggleManual(className)}
                            >
                                <CheckIcon
                                    class={cn(
                                        !draft.manualClasses.includes(className) &&
                                            'text-transparent'
                                    )}
                                />
                                <span class="min-w-0 flex-1 truncate">{className}</span>
                            </Command.Item>
                        {/each}
                    </Command.List>
                </Command.Root>
            </Tabs.Content>
        </Tabs.Root>
        <div class="space-y-3 border-t pt-3">
            <div class="text-sm font-medium">Coloring</div>
            <div>
                <div class="mb-2 flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">Color intensity</span>
                    <span class="text-xs tabular-nums text-muted-foreground">
                        {colorDraft.intensity.toFixed(1)}×
                    </span>
                </div>
                <Slider
                    type="single"
                    bind:value={colorDraft.intensity}
                    min={0.2}
                    max={3}
                    step={0.1}
                    data-testid="color-intensity-slider"
                />
            </div>
            <label class="flex items-center gap-2 text-sm">
                <Checkbox
                    bind:checked={colorDraft.logScale}
                    data-testid="color-log-scale-checkbox"
                />
                <div class="flex flex-col">
                    Logarithmic coloring
                    <span class="text-xs text-muted-foreground">
                        (keeps small counts visible next to large ones)
                    </span>
                </div>
            </label>
        </div>
        <Dialog.Footer>
            <Button variant="ghost" onclick={() => (open = false)}>Cancel</Button>
            <Button
                onclick={apply}
                disabled={draft.mode === 'manual' && draft.manualClasses.length === 0}
                data-testid="class-set-apply"
            >
                Apply
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
