<script lang="ts">
    import { Button } from '$lib/components';
    import type { Snippet } from 'svelte';

    const { href, children }: { href: string; children: Snippet } = $props();
</script>

{@render children()}
<Button variant="secondary" buttonProps={{ href }}>View sample</Button>
