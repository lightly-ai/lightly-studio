<script lang="ts">
    interface Props {
        onSelectAll: () => void;
        onClear: () => void;
    }

    const { onSelectAll, onClear }: Props = $props();

    const actionClass = 'text-xs text-diffuse-foreground hover:text-foreground hover:underline';
</script>

<div class="flex items-center gap-3">
    <button type="button" class={actionClass} onclick={onSelectAll}>Select all</button>
    <button type="button" class={actionClass} onclick={onClear}>Clear</button>
</div>
