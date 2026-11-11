<script lang="ts">
    import { CheckCheck, X } from '@lucide/svelte';
    import { FilterActionButton } from '$lib/components/FilterActionButton';

    interface Props {
        onSelectAll: () => void;
        onClear: () => void;
    }

    const { onSelectAll, onClear }: Props = $props();
</script>

<div class="flex flex-wrap items-center gap-1.5">
    <FilterActionButton label="Select all" icon={CheckCheck} onclick={onSelectAll} />
    <FilterActionButton label="Clear" icon={X} onclick={onClear} />
</div>
