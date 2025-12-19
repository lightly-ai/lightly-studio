<script lang="ts">
    import Button from '$lib/components/ui/button/button.svelte';
    import type { Snippet } from 'svelte';

    const { href, children }: { href: string; children: Snippet } = $props();
</script>

{@render children()}
<Button variant="secondary" {href}>View sample</Button>
