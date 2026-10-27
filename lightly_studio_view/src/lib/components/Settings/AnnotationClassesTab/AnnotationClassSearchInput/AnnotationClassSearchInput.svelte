<script lang="ts">
    import { Input } from '$lib/components/ui/input';
    import { Search } from '@lucide/svelte';

    interface Props {
        value: string;
        onkeydown: (event: KeyboardEvent) => void;
    }

    let { value = $bindable(), onkeydown }: Props = $props();
</script>

<div class="relative">
    <Search
        class="pointer-events-none absolute left-3 top-1/2 z-10 size-4 -translate-y-1/2 text-muted-foreground"
    />
    <Input
        bind:value
        placeholder="Find or add an annotation class"
        aria-label="Find or add an annotation class"
        class="pl-9"
        autofocus
        {onkeydown}
    />
</div>
