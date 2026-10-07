<script lang="ts">
    interface Props {
        onStart: () => void;
        onDismiss: () => void;
    }

    let { onStart, onDismiss }: Props = $props();
</script>

<aside
    aria-label="Image tour invitation"
    class="absolute bottom-6 right-6 z-50 w-72 rounded-lg border border-border-hard bg-card p-4 shadow-lg"
>
    <h2 class="font-semibold">Explore this collection</h2>
    <p class="mt-1 text-sm text-diffuse-foreground">
        Take a short tour of the image grid and sample details.
    </p>
    <div class="mt-4 flex justify-end gap-2">
        <button type="button" class="rounded px-3 py-1 text-sm" onclick={onDismiss}>Dismiss</button>
        <button
            type="button"
            class="rounded bg-primary px-3 py-1 text-sm text-primary-foreground"
            onclick={onStart}>Start</button
        >
    </div>
</aside>
