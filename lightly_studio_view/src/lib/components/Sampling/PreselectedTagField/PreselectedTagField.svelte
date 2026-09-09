<script lang="ts">
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';
    import { Select } from '$lib/components/Select';
    import { Label } from '$lib/components/ui/label';

    interface TagOption {
        tag_id: string;
        name: string;
    }

    interface Props {
        tags: TagOption[];
        value?: string;
        onValueChange: (value: string | undefined) => void;
    }

    let { tags, value, onValueChange }: Props = $props();
    const items = $derived(tags.map((tag) => ({ value: tag.tag_id, label: tag.name })));
</script>

<div class="grid gap-2">
    <div class="flex items-center gap-1.5">
        <Label for="preselected-tag">Preselected Tag (Optional)</Label>
        <FieldTooltip
            content="Samples in this tag are treated as already selected and appear before the newly selected samples in the result."
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
</div>
