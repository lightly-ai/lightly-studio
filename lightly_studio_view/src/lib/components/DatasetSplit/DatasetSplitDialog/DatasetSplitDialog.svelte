<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import { Input } from '$lib/components/ui/input';
    import { getSplitCounts, getSplitError } from '../splitPreview';
    import DatasetSplitRows from './DatasetSplitRows/DatasetSplitRows.svelte';

    interface Props {
        sampleCount: number;
        existingTagNames: string[];
        pending?: boolean;
        error?: string;
        onSubmit: (values: {
            splits: Parameters<typeof getSplitCounts>[1];
            seed?: number;
        }) => void | Promise<void>;
        onClose: () => void;
    }

    let {
        sampleCount,
        existingTagNames,
        pending = false,
        error,
        onSubmit,
        onClose
    }: Props = $props();
    let splits = $state([
        { tag_name: 'train', relative_size: 8 },
        { tag_name: 'val', relative_size: 1 },
        { tag_name: 'test', relative_size: 1 }
    ]);
    let seed = $state('42');
    const splitError = $derived(getSplitError({ splits, sampleCount, existingTagNames }));
    const seedError = $derived(
        seed.trim() && !Number.isSafeInteger(Number(seed))
            ? 'Seed must be a whole number within the supported range.'
            : undefined
    );
    const validationError = $derived(splitError || seedError);
    const counts = $derived(splitError ? [] : getSplitCounts(sampleCount, splits));

    let submitting = false;
    async function submit(event: SubmitEvent) {
        event.preventDefault();
        if (submitting || pending || validationError) return;
        submitting = true;
        try {
            await onSubmit({
                splits: splits.map((split) => ({ ...split, tag_name: split.tag_name.trim() })),
                ...(seed.trim() ? { seed: Number(seed) } : {})
            });
        } finally {
            submitting = false;
        }
    }
</script>

<Dialog.Root open onOpenChange={(open) => !open && onClose()}>
    <Dialog.Content class="max-h-[90dvh] overflow-y-auto">
        <Dialog.Header>
            <Dialog.Title>Split dataset</Dialog.Title>
            <Dialog.Description>
                Randomly divide the {sampleCount} samples matching your current filters into new tags.
                Each sample receives one tag. Weights set the share: 8:1:1 gives roughly 80%, 10%, 10%.
            </Dialog.Description>
        </Dialog.Header>
        <form onsubmit={submit} novalidate class="space-y-4">
            <fieldset disabled={pending} class="space-y-3">
                <DatasetSplitRows bind:splits {counts} {sampleCount} />
                <label class="block space-y-1 text-sm">
                    Seed (optional)
                    <Input
                        bind:value={seed}
                        inputmode="numeric"
                        aria-describedby="dataset-split-seed-help"
                    />
                </label>
                <p id="dataset-split-seed-help" class="text-sm text-muted-foreground">
                    Reuse a seed to repeat the split of the same samples. Leave blank for a random
                    split.
                </p>
            </fieldset>
            {#if validationError || error}
                <p role="alert" class="text-sm text-destructive">{validationError || error}</p>
            {/if}
            <Dialog.Footer>
                <Button type="button" variant="ghost" onclick={onClose}>Cancel</Button>
                <Button type="submit" disabled={pending || !!validationError}>
                    {pending ? 'Splitting…' : 'Split dataset'}
                </Button>
            </Dialog.Footer>
        </form>
    </Dialog.Content>
</Dialog.Root>
