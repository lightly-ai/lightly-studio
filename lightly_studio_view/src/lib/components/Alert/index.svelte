<script lang="ts">
    let { title, children } = $props();
</script>

<div class="relative rounded border border-red-400 bg-red-100 px-4 py-3 text-red-700" role="alert">
    <strong class="block font-bold">{title}</strong>
    <span class="block">{@render children()}</span>
</div>
