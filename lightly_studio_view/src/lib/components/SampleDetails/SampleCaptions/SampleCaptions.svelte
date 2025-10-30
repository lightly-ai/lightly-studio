<script lang="ts">
    import { Segment } from '$lib/components';

    const { captions }: { captions: { text: string }[] } = $props();
</script>

<Segment title="Captions">
    <div class="flex flex-col items-start justify-start gap-y-3 text-diffuse-foreground">
        {#each captions as { text }}
            <span class="text-sm">{text}</span>
        {/each}
    </div>
</Segment>
