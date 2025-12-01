<script lang="ts">
    import { BookOpen, Mail } from '@lucide/svelte';
    import { page } from '$app/state';
    import version from '$lib/version.json';
    import { isAnnotationsRoute } from '$lib/routes';

    type FooterProps = {
        totalSamples?: number;
        filteredSamples?: number;
        totalAnnotations?: number;
        filteredAnnotations?: number;
    };

    const {
        totalSamples = 0,
        filteredSamples = 0,
        totalAnnotations = 0,
        filteredAnnotations = 0
    }: FooterProps = $props();

    const statsText = $derived.by(() => {
        const isAnnotationView = isAnnotationsRoute(page.route.id);
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

<div class="border-border-hard bg-card mt-3 border-t px-6 py-1.5 text-sm">
    <div class="mx-auto flex items-center justify-between gap-5">
        <div class="flex items-center gap-2">
            {#if statsText}
                <span class="text-foreground font-medium">{statsText}</span>
            {/if}
        </div>
        <div class="flex items-center gap-2">
            <a
                class="text-foreground/80 hover:text-foreground flex items-center gap-2 transition-colors"
                href="https://www.lightly.ai/contact"
            >
                <Mail class="size-4" />
                <span>Contact Us</span>
            </a>
        </div>
        <div class="flex items-center gap-2">
            <a
                class="text-foreground/80 hover:text-foreground flex items-center gap-2 transition-colors"
                href="https://docs.lightly.ai/studio/"
                target="_blank"
                rel="noreferrer"
            >
                <BookOpen class="size-4" />
                <span>Docs</span>
            </a>
        </div>
        <div>
            version: {version.version}
        </div>
    </div>
</div>
