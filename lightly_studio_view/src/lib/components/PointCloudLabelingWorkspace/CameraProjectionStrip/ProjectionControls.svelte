<script lang="ts">
    import { Settings2 } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import * as Popover from '$lib/components/ui/popover';
    import ProjectionSettingsFields from './ProjectionControls/ProjectionSettingsFields.svelte';
    import type { ProjectionSettings } from './projectionSettings';

    interface Props {
        settings: ProjectionSettings;
        onChange: (settings: ProjectionSettings) => void;
        onPlaybackToggle?: () => void;
    }

    let { settings, onChange, onPlaybackToggle }: Props = $props();
    let open = $state(false);

    const preventSpaceActivation = (event: KeyboardEvent) => {
        if (event.code !== 'Space' || event.repeat) return;
        event.preventDefault();
        event.stopPropagation();
        onPlaybackToggle?.();
        (event.target as HTMLElement).blur();
        setTimeout(() => {
            (document.activeElement as HTMLElement | null)?.blur();
        }, 0);
    };
</script>

<Popover.Root bind:open>
    <Popover.Trigger>
        {#snippet child({ props })}
            <Button
                {...props}
                variant="outline"
                size="xs"
                class="px-3"
                aria-label="Projection settings"
                aria-expanded={open}
                onkeydown={preventSpaceActivation}
            >
                <Settings2 />
                Settings
            </Button>
        {/snippet}
    </Popover.Trigger>
    <Popover.Content
        class="max-h-[calc(100vh-2rem)] w-72 space-y-4 overflow-y-auto p-4"
        onkeydown={preventSpaceActivation}
    >
        <div class="space-y-1">
            <h3 class="text-sm font-medium">Camera projection settings</h3>
            <p class="text-xs text-muted-foreground">Adjust the camera overlay visibility.</p>
        </div>
        <ProjectionSettingsFields
            {settings}
            onChange={onChange}
            onKeydown={preventSpaceActivation}
        />
    </Popover.Content>
</Popover.Root>
