<script lang="ts">
    interface Props {
        count: number;
        total: number;
    }
    let { count, total }: Props = $props();

    const percent = $derived(total > 0 ? Math.min(100, (count / total) * 100) : 0);
</script>

<span class="h-1 w-8 overflow-hidden rounded-full bg-muted-foreground/20" aria-hidden="true">
    <span class="block h-full rounded-full bg-primary" style:width="{percent}%"></span>
</span>
