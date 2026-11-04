<script lang="ts">
    // Says which source a create button writes to, next to the button.
    interface Props {
        /** The source new annotations go to, or null when none is picked. */
        targetSource: string | null;
    }

    let { targetSource }: Props = $props();
</script>

<p
    class={targetSource ? 'text-xs text-muted-foreground' : 'text-xs text-amber-400'}
    data-testid="annotation-target-caption"
>
    {targetSource
        ? `Adds to ${targetSource}`
        : 'Pick where new annotations go in the Annotations panel.'}
</p>
