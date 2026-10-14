<script lang="ts">
    import { Button } from '$lib/components';
    import { Input } from '$lib/components/ui/input';

    interface Props {
        goalTitle: string;
        isDeduplication?: boolean;
        configurationKey?: string;
    }

    let { goalTitle, isDeduplication = false, configurationKey = goalTitle }: Props = $props();
    let sampleCount = $state(100);
    let maximumCount = $state<number | undefined>(undefined);
    let tagName = $state('My selection');
    let reviewing = $state(false);
    let confirmed = $state(false);
    const count = $derived(isDeduplication ? maximumCount : sampleCount);
    const canReview = $derived(
        ((isDeduplication && count === undefined) ||
            (Number.isInteger(count) && count !== undefined && count > 0)) &&
            !!tagName.trim()
    );
    const selectionSummary = $derived(
        isDeduplication
            ? maximumCount === undefined
                ? 'keep distinct images with no maximum'
                : `keep up to ${maximumCount} images`
            : `select ${sampleCount} samples`
    );

    $effect(() => {
        if (!configurationKey) return;
        reviewing = false;
        confirmed = false;
    });
</script>

<div class="mt-5 space-y-4 border-t border-border pt-5">
    <h4 class="text-sm font-semibold">Selection output</h4>
    <label class="block text-sm font-medium">
        {isDeduplication ? 'Maximum images to keep (optional)' : 'Number of samples wanted'}
        {#if isDeduplication}
            <Input
                wrapperClass="mt-1"
                type="number"
                min="1"
                step="1"
                placeholder="No maximum"
                bind:value={maximumCount}
                oninput={() => {
                    reviewing = false;
                    confirmed = false;
                }}
            />
        {:else}
            <Input
                wrapperClass="mt-1"
                type="number"
                min="1"
                step="1"
                bind:value={sampleCount}
                oninput={() => {
                    reviewing = false;
                    confirmed = false;
                }}
            />
        {/if}
    </label>
    <label class="block text-sm font-medium">
        Resulting tag
        <Input
            wrapperClass="mt-1"
            type="text"
            bind:value={tagName}
            oninput={() => {
                reviewing = false;
                confirmed = false;
            }}
        />
    </label>
    <p class="text-xs text-muted-foreground">
        The selected samples would be saved to a new sample tag with this name.
    </p>

    {#if reviewing}
        <div class="rounded-md border border-primary/30 bg-primary/5 p-3 text-sm" role="status">
            Review: {selectionSummary} using “{goalTitle}” and save them as “{tagName.trim()}”.
            {#if confirmed}
                <p class="mt-2 text-xs text-muted-foreground">
                    Preview confirmed. No selection was created.
                </p>
            {/if}
        </div>
    {/if}

    <div class="flex gap-2">
        {#if reviewing}
            <Button
                variant="outline"
                buttonProps={{
                    type: 'button',
                    onclick: () => {
                        reviewing = false;
                        confirmed = false;
                    }
                }}>Edit</Button
            >
            <Button
                variant="default"
                buttonProps={{
                    type: 'button',
                    disabled: confirmed,
                    onclick: () => (confirmed = true)
                }}>Confirm preview</Button
            >
        {:else}
            <Button
                variant="default"
                buttonProps={{
                    type: 'button',
                    disabled: !canReview,
                    onclick: () => (reviewing = true)
                }}>Review selection</Button
            >
        {/if}
    </div>
</div>
