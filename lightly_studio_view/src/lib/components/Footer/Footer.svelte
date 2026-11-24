<script lang="ts">
    import BookOpen from '@lucide/svelte/icons/book-open';
    import Mail from '@lucide/svelte/icons/mail';
    import { page } from '$app/state';
    import { version, git_sha, is_tagged_commit } from '$lib/version.json';
    import {
        isAnnotationsRoute,
        isCaptionsRoute,
        isMcapSequencesRoute,
        isVideoFramesRoute,
        isVideosRoute
    } from '$lib/routes';

    type FooterProps = {
        totalSamples?: number;
        filteredSamples?: number;
        totalAnnotations?: number;
        filteredAnnotations?: number;
        /** Show only the filtered count, not the dataset total, e.g. for a labeler. */
        hideTotal?: boolean;
    };

    const {
        totalSamples = 0,
        filteredSamples = 0,
        totalAnnotations = 0,
        filteredAnnotations = 0,
        hideTotal = false
    }: FooterProps = $props();

    function getItemType(count: number): string {
        if (isAnnotationsRoute(page.route.id)) {
            return 'annotations';
        } else if (isVideoFramesRoute(page.route.id)) {
            return 'video frames';
        } else if (isVideosRoute(page.route.id)) {
            return 'videos';
        } else if (isCaptionsRoute(page.route.id)) {
            return 'captions';
        } else if (isMcapSequencesRoute(page.route.id)) {
            return count === 1 ? 'MCAP sequence' : 'MCAP sequences';
        } else {
            return 'images';
        }
    }

    const statsText = $derived.by(() => {
        const isAnnotationView = isAnnotationsRoute(page.route.id);
        const filtered = isAnnotationView ? filteredAnnotations : filteredSamples;
        // A hidden total is the filtered count, so the dataset's size never shows.
        const total = hideTotal ? filtered : isAnnotationView ? totalAnnotations : totalSamples;
        const itemType = getItemType(total);

        if (!total) return '';

        if (filtered < total) {
            return `Showing ${filtered.toLocaleString()} of ${total.toLocaleString()} ${itemType}`;
        }

        return `Showing ${total.toLocaleString()} ${itemType}`;
    });
</script>

<div class="mt-3 border-t border-border-hard bg-card px-6 py-1.5 text-sm">
    <div class="mx-auto flex items-center justify-between gap-5">
        <div class="flex items-center gap-2">
            {#if statsText}
                <span class="font-medium text-foreground">{statsText}</span>
            {/if}
        </div>
        <div class="flex items-center gap-2">
            <a
                class="flex items-center gap-2 text-foreground/80 transition-colors hover:text-foreground"
                href="https://www.lightly.ai/contact"
                target="_blank"
                rel="noreferrer"
            >
                <Mail class="size-4" />
                <span>Contact Us</span>
            </a>
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
            <span class="text-foreground/60">
                v{version}
                {is_tagged_commit ? '' : `(dev: ${git_sha})`}
            </span>
        </div>
    </div>
</div>
