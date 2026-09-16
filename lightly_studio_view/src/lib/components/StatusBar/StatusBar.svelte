<script lang="ts">
    import { page } from '$app/state';
    import {
        isAnnotationsRoute,
        isCaptionsRoute,
        isVideoFramesRoute,
        isVideosRoute
    } from '$lib/routes';
    import { formatContextText, formatShowingText } from './statusBarText';

    interface Props {
        totalSamples?: number;
        filteredSamples?: number;
        totalAnnotations?: number;
        filteredAnnotations?: number;
        selectedCount?: number;
        sourceCount?: number;
        classCount?: number;
    }

    const {
        totalSamples = 0,
        filteredSamples = 0,
        totalAnnotations = 0,
        filteredAnnotations = 0,
        selectedCount = 0,
        sourceCount = 0,
        classCount = 0
    }: Props = $props();

    const itemType = $derived.by(() => {
        if (isAnnotationsRoute(page.route.id)) return 'annotations';
        if (isVideoFramesRoute(page.route.id)) return 'video frames';
        if (isVideosRoute(page.route.id)) return 'videos';
        if (isCaptionsRoute(page.route.id)) return 'captions';
        return 'images';
    });

    const isAnnotationView = $derived(isAnnotationsRoute(page.route.id));

    const showingText = $derived(
        formatShowingText({
            total: isAnnotationView ? totalAnnotations : totalSamples,
            filtered: isAnnotationView ? filteredAnnotations : filteredSamples,
            itemType
        })
    );

    const contextText = $derived(formatContextText({ selectedCount, sourceCount, classCount }));
</script>

<div
    class="flex h-8 shrink-0 items-center justify-between gap-4 border-t border-border-hard px-3.5 text-[11.5px] tabular-nums text-muted-foreground"
    data-testid="status-bar"
>
    <span class="truncate" data-testid="status-bar-showing">{showingText}</span>
    <span class="truncate" data-testid="status-bar-context">{contextText}</span>
</div>
