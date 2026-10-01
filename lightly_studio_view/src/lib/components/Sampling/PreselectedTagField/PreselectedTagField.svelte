<script lang="ts">
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';
    import { Select } from '$lib/components/Select';
    import { Label } from '$lib/components/ui/label';

    type PreselectionValidationStatus = 'idle' | 'loading' | 'eligible' | 'ineligible' | 'error';

    interface TagOption {
        tag_id: string;
        name: string;
    }

    interface Props {
        tags: TagOption[];
        value?: string;
        onValueChange: (value: string | undefined) => void;
        status?: PreselectionValidationStatus;
        error?: string | null;
    }

    let { tags, value, onValueChange, status = 'idle', error = null }: Props = $props();
    const items = $derived(tags.map((tag) => ({ value: tag.tag_id, label: tag.name })));
</script>

<div class="grid gap-2">
    <div class="flex items-center gap-1.5">
        <Label for="preselected-tag">Preselected Tag (Optional)</Label>
        <FieldTooltip
            content="Samples in this tag are treated as already selected and included in the result. Only additional samples count toward the requested number."
        />
    </div>
    <Select
        {items}
        {value}
        placeholder={tags.length === 0 ? 'No sample tags available' : 'Select a tag'}
        allowDeselect
        class="w-full"
        testId="sampling-preselected-tag-select"
        selectProps={{ id: 'preselected-tag' }}
        onValueChange={(selected) => onValueChange(selected || undefined)}
    />
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
        <p class="text-xs text-destructive-text" data-testid="preselected-tag-error">
            {error ?? 'Unable to validate this preselected tag. Please retry.'}
        </p>
    {/if}
</div>
