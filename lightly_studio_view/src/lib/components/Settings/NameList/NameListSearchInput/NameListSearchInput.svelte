<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { Search } from '@lucide/svelte';

    interface Props {
        value: string;
        onkeydown: (event: KeyboardEvent) => void;
        // The placeholder and accessible name, for example "Find or add an annotation class".
        label: string;
    }

    let { value = $bindable(), onkeydown, label }: Props = $props();
</script>

<div class="relative">
    <Search
        class="pointer-events-none absolute left-3 top-1/2 z-10 size-4 -translate-y-1/2 text-muted-foreground"
    />
    <Input bind:value placeholder={label} aria-label={label} class="pl-9" autofocus {onkeydown} />
</div>
