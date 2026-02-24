<script lang="ts">
    type LazyTriggerProps = {
        onIntersect: () => void;
        preloadDistance?: string;
        threshold?: number;
        disabled?: boolean;
    };

    const {
        onIntersect,
        preloadDistance = '500px',
        threshold = 0,
        disabled = false
    }: LazyTriggerProps = $props();

    let triggerRef: HTMLDivElement | null = $state(null);

    $effect(() => {
        if (!triggerRef || disabled) return;

        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting) {
                    onIntersect();
                }
            },
            {
                rootMargin: preloadDistance,
                threshold
            }
        );

        observer.observe(triggerRef);

        return () => observer.disconnect();
    });
</script>

<div bind:this={triggerRef} style="height: 1px; width: 1px;"></div>
