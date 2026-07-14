<script lang="ts">
    import type { Snippet } from 'svelte';
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Input } from '$lib/components/ui/input';
    import * as Tabs from '$lib/components/ui/tabs';
    import { Select, type SelectItem } from '$lib/components/Select';
    import ManualClassSelector from './ManualClassSelector.svelte';
    import type { ClassSetSelection } from './types';

    interface Props {
        /** Two-way bound flag controlling dialog visibility. */
        open: boolean;
        /** Every class label available; bounds top-N and populates the manual selector. */
        allClasses: string[];
        /** The currently applied selection. Copied into a draft each time the dialog opens. */
        selection: ClassSetSelection;
        /** Sort options for the top-N tab (host-specific ranking criteria). */
        sortItems: SelectItem[];
        /** Sub-title describing which chart the classes belong to. */
        description: string;
        /** Prefix for the dialog's test-ids (e.g. 'class-set', 'distribution-config'). */
        testIdPrefix: string;
        /** Shows an "All" quick action next to the number input. */
        showAllButton?: boolean;
        /** Extra controls rendered below the tabs (e.g. coloring options). */
        extraSections?: Snippet;
        /** Invoked with the new selection when the user clicks Apply. The dialog then closes itself. */
        onApply: (selection: ClassSetSelection) => void;
    }

    let {
        open = $bindable(),
        allClasses,
        selection,
        sortItems,
        description,
        testIdPrefix,
        showAllButton = false,
        extraSections,
        onApply
    }: Props = $props();

    const maxN = $derived(allClasses.length);

    const toDraft = (): ClassSetSelection => ({
        mode: selection.mode,
        n: selection.n,
        sortBy: selection.sortBy,
        manualClasses: [...selection.manualClasses]
    });

    // Draft state, synced from the applied selection every time the dialog opens.
    let draft: ClassSetSelection = $state(toDraft());
    $effect(() => {
        if (open) draft = toDraft();
    });

    // The number input can be cleared into a non-finite value; fall back to 1.
    const normalizedN = $derived(
        Number.isFinite(draft.n) ? Math.min(Math.max(draft.n, 1), maxN) : 1
    );
    const canApply = $derived(
        draft.mode === 'topN' ? Number.isFinite(draft.n) : draft.manualClasses.length > 0
    );

    const apply = () => {
        onApply({ ...draft, n: normalizedN });
        open = false;
    };
</script>

<Dialog.Root bind:open>
    <Dialog.Content class="max-w-[420px]">
        <Dialog.Header>
            <Dialog.Title>Configure classes</Dialog.Title>
            <Dialog.Description>{description}</Dialog.Description>
        </Dialog.Header>
        <Tabs.Root bind:value={draft.mode}>
            <Tabs.List class="grid w-full grid-cols-2">
                <Tabs.Trigger value="topN">Top N</Tabs.Trigger>
                <Tabs.Trigger value="manual">Manual</Tabs.Trigger>
            </Tabs.List>
            <Tabs.Content value="topN">
                <div class="space-y-3 pt-2">
                    <label class="flex items-center justify-between gap-2 text-sm">
                        Number of classes
                        <span class="flex items-center gap-1">
                            <Input
                                type="number"
                                min={1}
                                max={maxN}
                                bind:value={draft.n}
                                class="h-8 w-24"
                                data-testid={`${testIdPrefix}-top-n`}
                            />
                            {#if showAllButton}
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    class="h-8"
                                    onclick={() => (draft.n = maxN)}
                                    data-testid={`${testIdPrefix}-all`}
                                >
                                    All
                                </Button>
                            {/if}
                        </span>
                    </label>
                    <label class="flex items-center justify-between gap-2 text-sm">
                        Sort by
                        <Select
                            items={sortItems}
                            value={draft.sortBy}
                            size="xs"
                            class="w-44"
                            testId={`${testIdPrefix}-sort-by`}
                            onValueChange={(value) => (draft.sortBy = value)}
                        />
                    </label>
                </div>
            </Tabs.Content>
            <Tabs.Content value="manual">
                <ManualClassSelector
                    bind:selected={draft.manualClasses}
                    {allClasses}
                    searchTestId={`${testIdPrefix}-search`}
                />
            </Tabs.Content>
        </Tabs.Root>
        {@render extraSections?.()}
        <Dialog.Footer>
            <Button variant="ghost" onclick={() => (open = false)}>Cancel</Button>
            <Button onclick={apply} disabled={!canApply} data-testid={`${testIdPrefix}-apply`}>
                Apply
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
