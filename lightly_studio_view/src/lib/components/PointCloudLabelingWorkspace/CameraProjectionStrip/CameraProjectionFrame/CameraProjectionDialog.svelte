<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import type {
        AnnotationView,
        CameraProjectionView
    } from '$lib/api/lightly_studio_local/types.gen';
    import type { PointBatch } from '$lib/components/PointCloudViewer/types';
    import ProjectionControls from '../ProjectionControls.svelte';
    import ProjectionOverlay from '../ProjectionOverlay.svelte';
    import type { ProjectionSettings } from '../projectionSettings';

    interface Props {
        open?: boolean;
        label: string;
        imageUrl: string | null;
        batch?: PointBatch;
        annotations: readonly AnnotationView[];
        projection?: CameraProjectionView;
        projectionSettings?: ProjectionSettings;
        onProjectionSettingsChange?: (settings: ProjectionSettings) => void;
        onPlaybackToggle?: () => void;
    }

    let {
        open = $bindable(false),
        label,
        imageUrl,
        batch,
        annotations,
        projection,
        projectionSettings,
        onProjectionSettingsChange,
        onPlaybackToggle
    }: Props = $props();

    function handleKeydown(event: KeyboardEvent) {
        if (event.code !== 'Space' || event.repeat) return;
        event.preventDefault();
        event.stopPropagation();
        const target = event.target as HTMLElement;
        if (
            target.closest(
                'button, input, select, textarea, [role="button"], [role="slider"], [role="switch"], [contenteditable="true"]'
            )
        ) {
            return;
        }
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
            <Dialog.Title class="min-w-0 truncate text-sm font-medium">Camera: {label}</Dialog.Title>
            {#if projectionSettings && onProjectionSettingsChange}
                <ProjectionControls
                    settings={projectionSettings}
                    onChange={onProjectionSettingsChange}
                    {onPlaybackToggle}
                />
            {/if}
        </div>
        <Dialog.Description class="sr-only">Enlarged camera frame</Dialog.Description>
        <div class="relative mx-auto w-fit max-w-full">
            <img
                src={imageUrl ?? undefined}
                alt={`${label} enlarged`}
                class="block max-h-[80vh] max-w-full rounded-md object-contain"
            />
            <ProjectionOverlay {batch} {annotations} {projection} settings={projectionSettings} />
        </div>
    </Dialog.Content>
</Dialog.Root>
