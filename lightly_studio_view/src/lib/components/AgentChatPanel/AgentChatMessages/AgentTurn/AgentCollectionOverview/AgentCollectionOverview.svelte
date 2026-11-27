<script lang="ts">
    import type { CollectionOverview } from './collectionOverview';

    interface Props {
        overview: CollectionOverview;
    }

    const { overview }: Props = $props();
    const number = new Intl.NumberFormat();
    const DETAIL_PREVIEW_LENGTH = 3;

    function formatNames(names: string[]): string {
        if (!names.length) return 'None';
        const preview = names.slice(0, DETAIL_PREVIEW_LENGTH).join(', ');
        return names.length > DETAIL_PREVIEW_LENGTH ? `${preview}, …` : preview;
    }
</script>

<section
    class="min-w-0 overflow-hidden rounded-xl border border-border bg-background/40"
    aria-label="Collection overview"
>
    <div class="border-b border-border px-4 py-3">
        <h3 class="mb-2 text-sm font-semibold">Collection overview</h3>
        <dl class="flex flex-wrap gap-x-6 gap-y-1">
            <div class="flex items-baseline gap-1.5">
                <dt class="order-last text-xs text-muted-foreground">Images</dt>
                <dd class="text-xl font-semibold tabular-nums">
                    {number.format(overview.imageCount)}
                </dd>
            </div>
            {#if overview.classCount !== undefined}
                <div class="flex items-baseline gap-1.5">
                    <dt class="order-last text-xs text-muted-foreground">Annotation classes</dt>
                    <dd class="text-xl font-semibold tabular-nums">
                        {number.format(overview.classCount)}
                    </dd>
                </div>
            {/if}
        </dl>
    </div>
    <div class="space-y-3 px-4 py-3 text-sm">
        {#if overview.mostCommon.length}
            <h4 class="text-xs font-semibold">Most common annotation classes</h4>
            <dl class="space-y-1.5">
                {#each overview.mostCommon as annotation (annotation.name)}
                    <div class="flex items-baseline justify-between gap-3">
                        <dt class="min-w-0 break-words">{annotation.name}</dt>
                        <dd class="shrink-0 text-xs tabular-nums text-muted-foreground">
                            {number.format(annotation.imageCount)}
                            {annotation.imageCount === 1 ? 'image' : 'images'}
                        </dd>
                    </div>
                {/each}
            </dl>
        {:else}
            <p class="text-xs text-muted-foreground">No annotation classes found.</p>
        {/if}

        {#if overview.rareClass}
            <p class="rounded-md bg-primary/10 px-2.5 py-2 text-xs leading-relaxed">
                Explore the rare class <strong class="break-words">
                    {overview.rareClass.name}
                </strong>, found in one image.
            </p>
        {/if}
        <dl class="space-y-1.5 border-t border-border pt-3 text-xs">
            {#each [{ label: 'Tags', names: overview.tags }, { label: 'Metadata', names: overview.metadata }, { label: 'Embedding models', names: overview.embeddingModels }] as detail (detail.label)}
                <div class="flex justify-between gap-3">
                    <dt class="shrink-0 text-muted-foreground">{detail.label}</dt>
                    <dd class="min-w-0 break-words text-right">{formatNames(detail.names)}</dd>
                </div>
            {/each}
        </dl>
    </div>
</section>
