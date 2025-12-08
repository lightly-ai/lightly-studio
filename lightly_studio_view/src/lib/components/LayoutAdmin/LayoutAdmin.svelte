<script lang="ts">
    const { data, children } = $props();
</script>

<div class="flex-none"></div>
<div class="relative flex min-h-0 flex-1 flex-col">
    {@render children()}
</div>
