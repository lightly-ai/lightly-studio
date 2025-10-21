<script lang="ts">
    const {
        id,
        label,
        value
    }: {
        label: string;
        id: string;
        value: string;
    } = $props();
</script>

<span class="text-sm">{label}</span>
<span class="break-all text-sm" data-testid={`annotation-metadata-${id}`}>{value}</span>
