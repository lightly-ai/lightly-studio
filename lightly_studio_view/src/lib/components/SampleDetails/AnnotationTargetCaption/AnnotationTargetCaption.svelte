<script lang="ts">
    // Says which source a create button writes to, next to the button, or why it can't.
    interface Props {
        /** The source new annotations go to, or null when it is unknown or not picked. */
        targetSource: string | null;
        /** Why new annotations are blocked, or null when they are not. */
        blockedReason: string | null;
    }

    let { targetSource, blockedReason }: Props = $props();
</script>

<p
    class={blockedReason ? 'text-xs text-amber-400' : 'text-xs text-muted-foreground'}
    data-testid="annotation-target-caption"
>
    {blockedReason ?? `Adds to ${targetSource}`}
</p>
