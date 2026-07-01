<script lang="ts">
    import { BookOpen, Mail } from '@lucide/svelte';
    import { page } from '$app/state';
    import { version, git_sha, is_tagged_commit } from '$lib/version.json';
    import {
        isAnnotationsRoute,
        isEvaluationMatchesRoute,
        isVideoFramesRoute,
        isVideosRoute
    } from '$lib/routes';

    type FooterProps = {
        totalSamples?: number;
        filteredSamples?: number;
        totalAnnotations?: number;
        filteredAnnotations?: number;
        filteredMatches?: number;
    };

    const {
        totalSamples = 0,
        filteredSamples = 0,
        totalAnnotations = 0,
        filteredAnnotations = 0,
        filteredMatches = 0
    }: FooterProps = $props();

    function getItemType(): string {
        if (isEvaluationMatchesRoute(page.route.id)) {
            return 'matches';
        } else if (isAnnotationsRoute(page.route.id)) {
            return 'annotations';
        } else if (isVideoFramesRoute(page.route.id)) {
            return 'video frames';
        } else if (isVideosRoute(page.route.id)) {
            return 'videos';
        } else {
            return 'images';
        }
    }

    const statsText = $derived.by(() => {
        const itemType = getItemType();

        // Matches are paired annotations, not collection samples, and the listing
        // has no separate unfiltered baseline — show how many the filters resolve to.
        if (isEvaluationMatchesRoute(page.route.id)) {
            if (!filteredMatches) return '';
            return `Showing ${filteredMatches.toLocaleString()} ${itemType}`;
        }

        const isAnnotationView = isAnnotationsRoute(page.route.id);
        const total = isAnnotationView ? totalAnnotations : totalSamples;
        const filtered = isAnnotationView ? filteredAnnotations : filteredSamples;

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
