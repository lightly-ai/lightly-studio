<script lang="ts">
    import { Segment } from '$lib/components';

    type Frame = {
        frame_number: number;
        frame_timestamp_s: number;
        video: {
            file_path_abs: string;
        };
    };

    const { sample }: { sample: Frame } = $props();
</script>

<Segment title="Video frame details">
    <div class="min-w-full space-y-3 text-diffuse-foreground">
        <div class="flex items-start gap-3">
            <span class="truncate text-sm font-medium" title="Width">Number:</span>
            <span class="text-sm">{sample.frame_number}</span>
        </div>
        <div class="flex items-start gap-3">
            <span class="truncate text-sm font-medium" title="Height">Timestamp:</span>
            <span class="text-sm">{sample.frame_timestamp_s.toFixed(2)} seconds</span>
        </div>
        <div class="flex items-start gap-3">
            <span class="text-sm font-medium" title="Height">Video file path:</span>
            <span class="w-auto break-all text-sm">{sample.video.file_path_abs}</span>
        </div>
    </div>
</Segment>
