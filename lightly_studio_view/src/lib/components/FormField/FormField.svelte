<script lang="ts">
    import type { Snippet } from 'svelte';

    const {
        label,
        description,
        children,
        forComponent
    }: {
        label: string;
        description?: string;
        children: Snippet;
        forComponent?: string;
    } = $props();

    const labelClasses =
        'text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70';
</script>

<div class="space-y-2">
    <div class="flex justify-between">
        {#if forComponent}
            <label class={labelClasses} for={forComponent}>
                {label}
            </label>
        {:else}
            <!-- svelte-ignore a11y_label_has_associated_control -->
            <label class={labelClasses}>
                {label}
            </label>
        {/if}
    </div>

    {@render children()}

    {#if description}
        <p class="ml-4 text-xs text-muted-foreground">
            {description}
        </p>
    {/if}
</div>
