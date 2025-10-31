<script lang="ts">
    import { Segment } from '$lib/components';

    const { captions }: { captions: { text: string }[] } = $props();
</script>

<Segment title="Captions">
    <div class="flex flex-col items-start justify-start">
        {#each captions as { text }}
            <div
                class="mb-2 gap-2 rounded-sm bg-card px-4 py-3 text-left align-baseline text-diffuse-foreground transition-colors"
            >
                <span class="text-sm">{text}</span>
            </div>
        {/each}
    </div>
</Segment>
