<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import type {
        AnnotationView,
        CameraProjectionView
    } from '$lib/api/lightly_studio_local/types.gen';
    import type { PointBatch } from '$lib/components/PointCloudViewer/types';
    import ChevronLeft from '@lucide/svelte/icons/chevron-left';
    import ChevronRight from '@lucide/svelte/icons/chevron-right';
    import { Button } from '$lib/components/ui/button';
    import ProjectionControls from '../ProjectionControls.svelte';
    import ProjectionOverlay from '../ProjectionOverlay.svelte';
    import type { ProjectionSettings } from '../projectionSettings';
    import type { AnnotationClassColor } from '../projectionOverlay';

    interface Props {
        open?: boolean;
        label: string;
        imageUrl: string | null;
        batch?: PointBatch;
        annotations: readonly AnnotationView[];
        annotationClasses?: readonly AnnotationClassColor[];
        projection?: CameraProjectionView;
        projectionSettings?: ProjectionSettings;
        onProjectionSettingsChange?: (settings: ProjectionSettings) => void;
        onPlaybackToggle?: () => void;
        position: { index: number; total: number };
        onPrevious?: () => void;
        onNext?: () => void;
        previousKey: string;
        nextKey: string;
    }

    let {
        open = $bindable(false),
        label,
        imageUrl,
        batch,
        annotations,
        annotationClasses = [],
        projection,
        projectionSettings,
        onProjectionSettingsChange,
        onPlaybackToggle,
        position,
        onPrevious,
        onNext,
        previousKey,
        nextKey
    }: Props = $props();

    function handleKeydown(event: KeyboardEvent) {
        if (event.code !== 'Space' || event.repeat) return;
        const target = event.target as HTMLElement;
        if (
            target.closest(
                'button, input, select, textarea, [role="button"], [role="slider"], [role="switch"], [contenteditable="true"]'
            )
        ) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        onPlaybackToggle?.();
    }
</script>

<Dialog.Root bind:open>
    <Dialog.Content
        class="max-w-[90vw] gap-2 p-3 outline-none sm:max-w-[90vw]"
        onOpenAutoFocus={(event) => event.preventDefault()}
        onCloseAutoFocus={(event) => event.preventDefault()}
        onkeydown={handleKeydown}
    >
        <div class="flex min-w-0 items-center justify-between gap-3 pr-10">
            <Dialog.Title class="min-w-0 truncate text-sm font-medium">
                Camera: {label} · {position.index} / {position.total}
            </Dialog.Title>
            <div class="flex items-center gap-3">
                <div class="flex items-center gap-1">
                    <Button
                        variant="outline"
                        size="xs"
                        aria-label="Previous camera"
                        title={`Shortcut: ${previousKey}`}
                        disabled={!onPrevious}
                        onclick={onPrevious}
                    >
                        <ChevronLeft />
                    </Button>
                    <Button
                        variant="outline"
                        size="xs"
                        aria-label="Next camera"
                        title={`Shortcut: ${nextKey}`}
                        disabled={!onNext}
                        onclick={onNext}
                    >
                        <ChevronRight />
                    </Button>
                </div>
                {#if projectionSettings && onProjectionSettingsChange}
                    <ProjectionControls
                        settings={projectionSettings}
                        onChange={onProjectionSettingsChange}
                        {onPlaybackToggle}
                    />
                {/if}
            </div>
        </div>
        <Dialog.Description class="sr-only">Enlarged camera frame</Dialog.Description>
        <div class="relative mx-auto w-fit max-w-full">
            <img
                src={imageUrl ?? undefined}
                alt={`${label} enlarged`}
                class="block max-h-[80vh] max-w-full rounded-md object-contain"
            />
            <ProjectionOverlay
                {batch}
                {annotations}
                {annotationClasses}
                {projection}
                settings={projectionSettings}
            />
        </div>
    </Dialog.Content>
</Dialog.Root>
