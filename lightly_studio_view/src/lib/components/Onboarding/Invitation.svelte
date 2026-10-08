<script lang="ts">
    interface Props {
        onStart: () => void;
        onDismiss: () => void;
    }

    let { onStart, onDismiss }: Props = $props();
</script>

<aside
    aria-label="Image tour invitation"
    class="fixed left-1/2 top-1/2 z-[10001] w-80 -translate-x-1/2 -translate-y-1/2 rounded-lg border border-border-hard bg-card p-5 shadow-lg"
>
    <h2 class="font-semibold">Explore this collection</h2>
    <p class="mt-1 text-sm text-diffuse-foreground">
        Take a short tour of the image grid and sample details.
    </p>
    <div class="mt-4 flex justify-end gap-2">
        <button type="button" class="rounded px-3 py-1 text-sm" onclick={onDismiss}>Dismiss</button>
        <button
            type="button"
            class="start-btn rounded bg-primary px-3 py-1 text-sm text-primary-foreground"
            onclick={onStart}>Start</button
        >
    </div>
</aside>

<style>
    .start-btn {
        animation: ring-pulse 1.5s ease-out infinite;
    }

    @keyframes ring-pulse {
        0% {
            box-shadow: 0 0 0 0 hsl(var(--primary) / 0.7);
        }
        70% {
            box-shadow: 0 0 0 8px hsl(var(--primary) / 0);
        }
        100% {
            box-shadow: 0 0 0 0 hsl(var(--primary) / 0);
        }
    }
</style>
