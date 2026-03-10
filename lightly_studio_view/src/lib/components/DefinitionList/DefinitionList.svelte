<script lang="ts">
    export type DefinitionItem = {
        label: string;
        value: string | number | null | undefined;
        testId?: string;
    };

    const { items }: { items: DefinitionItem[] } = $props();
</script>

<dl class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-3 text-diffuse-foreground">
    {#each items as { label, value, testId }, index (index)}
        <dt class="text-sm font-medium" title={label}>{label}</dt>
        <dd class="break-all text-sm" data-testid={testId}>{value ?? '-'}</dd>
    {/each}
</dl>
