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
            return `Showing: ${filtered.toLocaleString()} of ${total.toLocaleString()} ${itemType}`;
        }

        return `Total: ${total.toLocaleString()} ${itemType}`;
    });
</script>

<div class="fixed inset-x-0 bottom-0 z-20">
    <div class="h-[2px] bg-black/60"></div>
    <div
        class="bg-border px-4 py-0.5 text-[10px] leading-none text-muted-foreground backdrop-blur-sm"
    >
        <div class="mx-auto flex max-w-[1800px] items-center justify-between gap-5 pr-14">
            <div class="flex items-center gap-2">
                {#if statsText}
                    <span class="text-foreground/80">{statsText}</span>
                {/if}
            </div>
            <div class="flex items-center gap-5">
                <a
                    class="flex items-center gap-1 hover:text-foreground hover:underline"
                    href="https://www.lightly.ai/contact"
                >
                    <Mail class="size-3" />
                    Upgrade / Contact
                </a>
                <a
                    class="flex items-center gap-1 hover:text-foreground hover:underline"
                    href="https://docs.lightly.ai/studio/"
                    target="_blank"
                    rel="noreferrer"
                >
                    <BookOpen class="size-3" />
                    Docs
                </a>
                <span class="text-foreground/80">© Lightly Inc.</span>
            </div>
        </div>
    </div>
</div>
