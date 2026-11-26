<script lang="ts">
    import { tick, type ComponentProps } from 'svelte';
    import * as Dialog from '$lib/components/ui/dialog';
    import type ProjectionOverlay from '../ProjectionOverlay.svelte';
    import type { ProjectionSettings } from '../projectionSettings';
    import CameraDialogHeader from './CameraDialogHeader.svelte';
    import ProjectedCameraImage from './ProjectedCameraImage.svelte';
    import { isPlaybackSpace } from './isPlaybackSpace';

    interface Props {
        open?: boolean;
        label: string;
        imageUrl: string | null;
        /** The point cloud and annotations drawn over the image; the settings come separately. */
        overlay: Omit<ComponentProps<typeof ProjectionOverlay>, 'settings'>;
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
        overlay,
        projectionSettings,
        onProjectionSettingsChange,
        onPlaybackToggle,
        position,
        onPrevious,
        onNext,
        previousKey,
        nextKey
    }: Props = $props();

    let content = $state<HTMLElement | null>(null);

    // Keep focus on the dialog itself: no button gets focus, so Space toggles playback instead of
    // activating the tile that opened the dialog.
    async function focusContent(event: Event) {
        event.preventDefault();
        await tick();
        content?.focus();
    }

    function handleKeydown(event: KeyboardEvent) {
        if (!isPlaybackSpace(event)) return;
        event.preventDefault();
        event.stopPropagation();
        onPlaybackToggle?.();
    }
</script>

<Dialog.Root bind:open>
    <Dialog.Content
        bind:ref={content}
        tabindex={-1}
        class="max-w-[90vw] gap-2 p-3 outline-none sm:max-w-[90vw]"
        onOpenAutoFocus={focusContent}
        onCloseAutoFocus={(event) => event.preventDefault()}
        onkeydown={handleKeydown}
    >
        <CameraDialogHeader
            {label}
            {position}
            {onPrevious}
            {onNext}
            {previousKey}
            {nextKey}
            {projectionSettings}
            {onProjectionSettingsChange}
            {onPlaybackToggle}
        />
        <Dialog.Description class="sr-only">Enlarged camera frame</Dialog.Description>
        <ProjectedCameraImage
            {label}
            {imageUrl}
            overlay={{ ...overlay, settings: projectionSettings }}
        />
    </Dialog.Content>
</Dialog.Root>
