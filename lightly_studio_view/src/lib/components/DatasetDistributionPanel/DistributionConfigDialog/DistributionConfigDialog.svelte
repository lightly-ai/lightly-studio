<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Input } from '$lib/components/ui/input';
    import { Select, type SelectItem } from '$lib/components/Select';
    import {
        DISTRIBUTION_SORT_LABELS,
        type DistributionConfig,
        type DistributionSortOption
    } from '../types';

    interface Props {
        /** Two-way bound flag controlling dialog visibility. */
        open: boolean;
        /** Upper bound for top-N, typically the total class count. */
        maxN: number;
        /** The currently applied config. Copied into a draft each time the dialog opens. */
        config: DistributionConfig;
        /** Invoked with the new config when the user clicks Apply. The dialog then closes itself. */
        onApply: (config: DistributionConfig) => void;
    }

    let { open = $bindable(), maxN, config, onApply }: Props = $props();

    // Draft state, synced from the applied config every time the dialog opens.
    let draft: DistributionConfig = $state({ ...config });
    $effect(() => {
        if (open) draft = { ...config };
    });

    // The number input can be cleared into a non-finite value; fall back to 1.
    const normalizedN = $derived(
        Number.isFinite(draft.n) ? Math.min(Math.max(draft.n, 1), maxN) : 1
    );

    const sortItems: SelectItem[] = (
        Object.keys(DISTRIBUTION_SORT_LABELS) as DistributionSortOption[]
    ).map((value) => ({ value, label: DISTRIBUTION_SORT_LABELS[value] }));

    const apply = () => {
        onApply({ ...draft, n: normalizedN });
        open = false;
    };
</script>

<Dialog.Root bind:open>
    <Dialog.Content class="max-w-[420px]">
        <Dialog.Header>
            <Dialog.Title>Configure classes</Dialog.Title>
            <Dialog.Description>
                Choose which classes the distribution chart shows.
            </Dialog.Description>
        </Dialog.Header>
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
                        data-testid="distribution-config-top-n"
                    />
                    <Button
                        variant="ghost"
                        size="sm"
                        class="h-8"
                        onclick={() => (draft.n = maxN)}
                        data-testid="distribution-config-all"
                    >
                        All
                    </Button>
                </span>
            </label>
            <label class="flex items-center justify-between gap-2 text-sm">
                Sort by
                <Select
                    items={sortItems}
                    value={draft.sortBy}
                    size="xs"
                    class="w-44"
                    testId="distribution-config-sort-by"
                    onValueChange={(value) => (draft.sortBy = value as DistributionSortOption)}
                />
            </label>
        </div>
        <Dialog.Footer>
            <Button variant="ghost" onclick={() => (open = false)}>Cancel</Button>
            <Button onclick={apply} data-testid="distribution-config-apply">Apply</Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
