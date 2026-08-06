<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { Input } from '$lib/components/ui/input';
    import { LoaderCircle, Plus } from '@lucide/svelte';

    let {
        existingNames,
        onAdd,
        onValueChange
    }: {
        existingNames: string[];
        onAdd: (names: string[]) => Promise<void>;
        onValueChange?: (value: string) => void;
    } = $props();

    let value = $state('');
    let isAdding = $state(false);
    let message = $state('');
    const parsedNames = $derived([
        ...new Set(
            value
                .split(',')
                .map((name) => name.trim())
                .filter(Boolean)
        )
    ]);
    const disabled = $derived(parsedNames.length === 0 || isAdding);

    async function handleSubmit(event: SubmitEvent) {
        event.preventDefault();
        const existing = new Set(existingNames.map((name) => name.toLowerCase()));
        const duplicates = parsedNames.filter((name) => existing.has(name.toLowerCase()));
        const names = parsedNames.filter((name) => !existing.has(name.toLowerCase()));
        if (!names.length) {
            message = 'All classes already exist.';
            return;
        }
        isAdding = true;
        message = duplicates.length ? `Already exist: ${duplicates.join(', ')}.` : '';
        try {
            await onAdd(names);
            value = '';
            onValueChange?.('');
        } catch {
            message = 'Failed to add classes. Please try again.';
        } finally {
            isAdding = false;
        }
    }
</script>

<form class="space-y-2" onsubmit={handleSubmit}>
    <div class="flex gap-2">
        <Input
            bind:value
            aria-label="Class names"
            placeholder="e.g. dogs, cats, people"
            disabled={isAdding}
            oninput={(e) => onValueChange?.((e.currentTarget as HTMLInputElement).value)}
        />
        <Button type="submit" {disabled}>
            {#if isAdding}<LoaderCircle class="animate-spin" />{:else}<Plus />{/if}
            {isAdding ? 'Adding...' : 'Add'}
        </Button>
    </div>
    {#if message}<p class="text-sm text-muted-foreground" role="status">{message}</p>{/if}
</form>
