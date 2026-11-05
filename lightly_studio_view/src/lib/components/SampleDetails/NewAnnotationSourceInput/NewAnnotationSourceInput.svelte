<script lang="ts">
    import { Plus } from '@lucide/svelte';

    interface Props {
        /** Names already taken; typing one of them selects it instead of creating a duplicate. */
        existingNames: string[];
        onSubmit: (name: string) => void;
    }

    let { existingNames, onSubmit }: Props = $props();

    let isOpen = $state(false);
    let name = $state('');

    const close = () => {
        isOpen = false;
        name = '';
    };

    const submit = () => {
        const trimmed = name.trim();
        if (trimmed) onSubmit(trimmed);
        close();
    };

    const isExisting = $derived(existingNames.includes(name.trim()));
</script>

{#if isOpen}
    <form
        class="flex flex-col gap-1"
        onsubmit={(e) => {
            e.preventDefault();
            submit();
        }}
    >
        <!-- svelte-ignore a11y_autofocus -->
        <input
            class="h-8 w-full rounded-md border border-border bg-transparent px-2 text-sm outline-none focus:border-primary"
            placeholder="Source name"
            aria-label="New annotation source name"
            autofocus
            bind:value={name}
            onkeydown={(e) => e.key === 'Escape' && close()}
            onblur={close}
            data-testid="new-annotation-source-input"
        />
        <p class="text-xs text-muted-foreground">
            {isExisting
                ? 'Enter selects this existing source.'
                : 'Created when you add the first annotation.'}
        </p>
    </form>
{:else}
    <button
        type="button"
        class="flex items-center gap-2 py-1 text-sm text-muted-foreground hover:text-foreground"
        onclick={() => (isOpen = true)}
        data-testid="new-annotation-source-button"
    >
        <Plus class="size-4" />
        New source
    </button>
{/if}
