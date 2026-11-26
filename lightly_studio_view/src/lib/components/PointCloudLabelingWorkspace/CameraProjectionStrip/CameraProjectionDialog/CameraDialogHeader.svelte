<script lang="ts">
    import * as Dialog from '$lib/components/ui/dialog';
    import ProjectionControls from '../ProjectionControls.svelte';
    import type { ProjectionSettings } from '../projectionSettings';
    import CameraSwitchButtons from './CameraSwitchButtons.svelte';

    interface Props {
        label: string;
        position: { index: number; total: number };
        onPrevious?: () => void;
        onNext?: () => void;
        previousKey: string;
        nextKey: string;
        projectionSettings?: ProjectionSettings;
        onProjectionSettingsChange?: (settings: ProjectionSettings) => void;
        onPlaybackToggle?: () => void;
    }

    const {
        label,
        position,
        onPrevious,
        onNext,
        previousKey,
        nextKey,
        projectionSettings,
        onProjectionSettingsChange,
        onPlaybackToggle
    }: Props = $props();
</script>

<div class="flex min-w-0 items-center justify-between gap-3 pr-10">
    <Dialog.Title class="min-w-0 truncate text-sm font-medium">
        Camera: {label} · {position.index} / {position.total}
    </Dialog.Title>
    <div class="flex items-center gap-3">
        <CameraSwitchButtons {onPrevious} {onNext} {previousKey} {nextKey} />
        {#if projectionSettings && onProjectionSettingsChange}
            <ProjectionControls
                settings={projectionSettings}
                onChange={onProjectionSettingsChange}
                {onPlaybackToggle}
            />
        {/if}
    </div>
</div>
