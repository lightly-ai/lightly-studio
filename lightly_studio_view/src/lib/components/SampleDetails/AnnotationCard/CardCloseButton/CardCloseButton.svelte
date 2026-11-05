<script lang="ts">
    import { X } from '@lucide/svelte';

    interface Props {
        onClose: () => void;
    }

    const { onClose }: Props = $props();
</script>

<button
    type="button"
    class="inline-flex size-6 items-center justify-center rounded-md text-muted-foreground hover:text-foreground"
    aria-label="Close"
    title="Close (Esc)"
    onclick={onClose}
>
    <X class="size-4" />
</button>
