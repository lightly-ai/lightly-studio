<script lang="ts">
    import { BookOpen, Mail } from '@lucide/svelte';
    import type { GridType } from '$lib/types';

    type FooterProps = {
        totalSamples?: number;
        filteredSamples?: number;
        totalAnnotations?: number;
        filteredAnnotations?: number;
        gridType?: GridType;
    };

    const {
        totalSamples = 0,
        filteredSamples = 0,
        totalAnnotations = 0,
        filteredAnnotations = 0,
        gridType = 'samples'
    }: FooterProps = $props();

    const statsText = $derived.by(() => {
        const isAnnotationView = gridType === 'annotations';
        const total = isAnnotationView ? totalAnnotations : totalSamples;
        const filtered = isAnnotationView ? filteredAnnotations : filteredSamples;
        const itemType = isAnnotationView ? 'annotations' : 'images';

        if (!total) return '';

        if (filtered < total) {
            return `Showing ${filtered.toLocaleString()} of ${total.toLocaleString()} ${itemType}`;
        }

        return `Showing ${total.toLocaleString()} ${itemType}`;
    });
</script>

<div class="mt-3 border-t border-border-hard bg-card px-4 py-2 text-sm">
    <div class="mx-auto flex items-center justify-between gap-5">
        <div class="flex items-center gap-2">
            {#if statsText}
                <span class="font-medium text-foreground">{statsText}</span>
            {/if}
        </div>
        <div class="flex items-center gap-2">
            <a
                class="flex items-center gap-2 text-foreground/80 transition-colors hover:text-foreground"
                href="https://docs.lightly.ai/studio/"
                target="_blank"
                rel="noreferrer"
            >
                <BookOpen class="size-4" />
                <span>Docs</span>
            </a>
        </div>
        <div class="flex items-center gap-2">
            <a
                class="flex items-center gap-2 text-foreground/80 transition-colors hover:text-foreground"
                href="https://www.lightly.ai/contact"
            >
                <Mail class="size-4" />
                <span>Contact</span>
            </a>
        </div>
    </div>
</div>
