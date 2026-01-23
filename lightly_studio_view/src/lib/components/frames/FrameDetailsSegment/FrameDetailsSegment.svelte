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
    <div class="grid grid-cols-[6rem_1fr] gap-y-3 text-diffuse-foreground">
        <span class="text-sm" title="Width">Number:</span>
        <span class="break-all text-sm">{sample.frame_number}</span>
        <span class="text-sm" title="Timestamp">Timestamp:</span>
        <span class="break-all text-sm">{sample.frame_timestamp_s.toFixed(2)} seconds</span>
        <span class="text-sm" title="Video file path">Video file path:</span>
        <span class="break-all text-sm" data-testid="frame-details-video-file-path"
            >{sample.video.file_path_abs}</span
        >
    </div>
</Segment>
