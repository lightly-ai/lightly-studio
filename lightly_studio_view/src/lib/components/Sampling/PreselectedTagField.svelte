<script lang="ts">
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';
    import { Label } from '$lib/components/ui/label';
    import type { TagView } from '$lib/services/types';

    type PreselectionValidationStatus = 'idle' | 'loading' | 'eligible' | 'ineligible' | 'error';

    interface Props {
        tags: TagView[];
        selectedTagId: string | null;
        status: PreselectionValidationStatus;
        error: string | null;
        onChange: (tagId: string | null) => void;
    }

    let { tags, selectedTagId, status, error, onChange }: Props = $props();
</script>

<div class="grid gap-2">
    <div class="flex items-center gap-1.5">
        <Label for="preselected-tag" class="text-foreground">Preselected Tag</Label>
        <FieldTooltip
            content="Samples in this tag are treated as already selected and included in the result. Only additional samples count toward the requested number."
        />
    </div>
    <select
        id="preselected-tag"
        class="h-10 rounded-md border border-input bg-background px-3 text-sm"
        value={selectedTagId ?? ''}
        onchange={(event) => onChange((event.currentTarget as HTMLSelectElement).value || null)}
        data-testid="sampling-dialog-preselected-tag"
    >
        <option value="">No preselected tag</option>
        {#each tags as tag (tag.tag_id)}
            <option value={tag.tag_id}>{tag.name}</option>
        {/each}
    </select>
    {#if status === 'loading'}
        <p class="text-xs text-muted-foreground" data-testid="preselected-tag-loading">
            Checking selected samples…
        </p>
    {:else if status === 'ineligible'}
        <p class="text-xs text-destructive-text" data-testid="preselected-tag-ineligible">
            This tag contains samples outside the current filters. Choose another tag or remove the
            filters.
        </p>
    {:else if status === 'error'}
        <p class="text-xs text-destructive-text" data-testid="preselected-tag-error">{error}</p>
    {/if}
</div>
