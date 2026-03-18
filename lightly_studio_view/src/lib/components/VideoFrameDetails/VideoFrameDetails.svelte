<script lang="ts">
    import { type FrameView } from '$lib/api/lightly_studio_local';
    import { Segment } from '$lib/components';
    import { Button } from '$lib/components/ui';

    let {
        frame,
        frameURL
    }: {
        frame: FrameView;
        frameURL: string;
    } = $props();
</script>

<Segment title="Current Frame">
    <div class="space-y-2 text-sm text-diffuse-foreground">
        <div class="flex items-center gap-2">
            <span class="font-medium">Frame #:</span>
            <span data-testid="current-frame-number">{frame.frame_number}</span>
        </div>
        <div class="flex items-center gap-2">
            <span class="font-medium">Timestamp:</span>
            <span data-testid="current-frame-timestamp">{frame.frame_timestamp_s.toFixed(3)} s</span
            >
        </div>
    </div>

    <Button variant="secondary" class="mt-4 w-full" href={frameURL} data-testid="view-frame-button">
        View frame
    </Button>
</Segment>
