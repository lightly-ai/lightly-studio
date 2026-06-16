<script lang="ts">
    type Props = {
        colorBySource: boolean;
        onToggle: (val: boolean) => void;
    };

    let { colorBySource, onToggle }: Props = $props();
</script>

<div class="flex items-center gap-1 text-xs">
    <span class="text-muted-foreground mr-1">Color by</span>
    <div class="bg-muted flex rounded-md p-0.5">
        <button
            class="rounded px-2 py-0.5 transition-colors {colorBySource
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'}"
            onclick={() => onToggle(true)}
        >
            Source
        </button>
        <button
            class="rounded px-2 py-0.5 transition-colors {!colorBySource
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'}"
            onclick={() => onToggle(false)}
        >
            Label
        </button>
    </div>
</div>
