<script lang="ts">
    type LazyTriggerProps = {
        onIntersect: () => void;
        rootMargin?: string;
        threshold?: number;
        disabled?: boolean;
    };

    const {
        onIntersect,
        rootMargin = '200px',
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
                rootMargin,
                threshold
            }
        );

        observer.observe(triggerRef);

        return () => observer.disconnect();
    });
</script>

<div bind:this={triggerRef}></div>
