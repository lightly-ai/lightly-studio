<script lang="ts">
    import { page } from '$app/state';
    import { Input } from '$lib/components/ui/input';
    import { cn } from '$lib/utils';
    import { Plus, Search } from '@lucide/svelte';
    import type { SettingsDialogState } from '../settingsDialogState.svelte';
    import { AnnotationClassRow } from './AnnotationClassRow';
    import { useAnnotationClasses } from './useAnnotationClasses.svelte';

    interface Props {
        // This tab saves its changes immediately, not with the settings form.
        dialogState?: Pick<SettingsDialogState, 'isSaving'>;
    }

    const { dialogState }: Props = $props();

    const collectionId = $derived(page.params.collection_id);
    const datasetId = $derived(page.params.dataset_id);
    const classes = useAnnotationClasses(() => ({
        collectionId: collectionId ?? '',
        datasetId: datasetId ?? ''
    }));

    let query = $state('');

    const trimmedQuery = $derived(query.trim());
    const sortedClasses = $derived(
        [...(classes.query.data ?? [])].sort((a, b) =>
            a.annotation_label_name.localeCompare(b.annotation_label_name)
        )
    );
    const visibleClasses = $derived(
        sortedClasses.filter((c) =>
            c.annotation_label_name.toLowerCase().includes(trimmedQuery.toLowerCase())
        )
    );
    const exactMatch = $derived(
        sortedClasses.find(
            (c) => c.annotation_label_name.toLowerCase() === trimmedQuery.toLowerCase()
        )
    );
    const canAdd = $derived(trimmedQuery.length > 0 && !exactMatch);
    // Enter adds only when nothing matches, so a partial search like "bea" for "bear"
    // never adds a class by accident.
    const canAddWithEnter = $derived(canAdd && visibleClasses.length === 0);

    // The last added class is highlighted and scrolled into view, so the user can
    // edit it, for example its color, straight away.
    let addedId = $state<string | null>(null);

    const add = async () => {
        if (!canAdd || dialogState?.isSaving) return;
        const name = trimmedQuery;
        const created = await classes.addClass(name);
        query = '';
        addedId = created.annotation_label_id ?? null;
    };
    // The input is inside the settings form, so Enter must not submit it.
    const onKeyDown = (event: KeyboardEvent) => {
        if (event.key !== 'Enter') return;
        event.preventDefault();
        if (canAddWithEnter) add();
    };
</script>

{#if !collectionId}
    <p class="text-sm text-muted-foreground">Open a dataset to manage its annotation classes.</p>
{:else}
    <!-- Only the list scrolls, so the search stays visible. -->
    <div class="flex h-full flex-col gap-3">
        <div class="mx-auto flex w-full max-w-lg shrink-0 flex-col gap-3">
            <div class="relative">
                <Search
                    class="pointer-events-none absolute left-3 top-1/2 z-10 size-4 -translate-y-1/2 text-muted-foreground"
                />
                <Input
                    bind:value={query}
                    placeholder="Find or add an annotation class"
                    aria-label="Find or add an annotation class"
                    class="pl-9"
                    autofocus
                    onkeydown={onKeyDown}
                />
            </div>
            <p class="px-2 text-xs text-muted-foreground">
                {#if exactMatch}
                    <span class="font-medium text-foreground"
                        >{exactMatch.annotation_label_name}</span
                    >
                    already exists.
                {:else if trimmedQuery && visibleClasses.length === 0}
                    No annotation class matches.
                {:else}
                    {#if trimmedQuery}
                        {visibleClasses.length} of
                    {/if}
                    {sortedClasses.length} annotation {sortedClasses.length === 1
                        ? 'class'
                        : 'classes'}
                {/if}
            </p>
        </div>
        <!-- Full width, so the scrollbar is at the dialog edge. -->
        <div
            class="-mx-6 -mb-4 min-h-0 flex-1 overflow-y-auto border-t border-border/40 px-6 pb-4 pt-1"
        >
            <ul class="mx-auto flex max-w-lg flex-col">
                {#if canAddWithEnter}
                    {@render addRow()}
                {/if}
                {#if classes.query.isLoading}
                    <li class="px-2 py-3 text-sm text-muted-foreground">
                        Loading annotation classes…
                    </li>
                {:else if sortedClasses.length === 0 && !canAdd}
                    <li class="px-2 py-6 text-sm text-muted-foreground">
                        This dataset has no annotation classes yet. Type a name above and press
                        Enter to add the first one.
                    </li>
                {/if}
                {#each visibleClasses as annotationClass (annotationClass.annotation_label_id)}
                    <AnnotationClassRow
                        name={annotationClass.annotation_label_name}
                        isHighlighted={annotationClass.annotation_label_id === addedId}
                        annotationCount={annotationClass.annotation_count}
                        onRename={(name) =>
                            classes.renameClass(
                                annotationClass.annotation_label_id!,
                                annotationClass.annotation_label_name,
                                name
                            )}
                        onDelete={() => classes.deleteClass(annotationClass.annotation_label_id!)}
                    />
                {/each}
                {#if canAdd && !canAddWithEnter}
                    {@render addRow()}
                {/if}
            </ul>
        </div>
    </div>
{/if}

{#snippet addRow()}
    <li class={cn(!canAddWithEnter && 'mt-1 border-t border-border/40 pt-1')}>
        <button
            type="button"
            class={cn(
                'flex h-10 w-full items-center gap-3 rounded-md px-2 text-left text-sm hover:bg-accent',
                canAddWithEnter ? 'bg-accent/50' : 'text-muted-foreground hover:text-foreground'
            )}
            onclick={add}
        >
            <Plus class="size-3 shrink-0 text-primary" />
            <span class="min-w-0 flex-1 truncate">
                Add new annotation class
                <span class="font-medium text-foreground">"{trimmedQuery}"</span>
            </span>
            {#if canAddWithEnter}
                <kbd class="rounded border border-border px-1.5 text-xs text-muted-foreground"
                    >Enter</kbd
                >
            {/if}
        </button>
    </li>
{/snippet}
