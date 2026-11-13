<script lang="ts">
    import { Select } from '$lib/components/Select';
    import { Label } from '$lib/components/ui/label';
    import type { GoalInputKind } from '../samplingGoals';

    interface Props {
        kind: GoalInputKind;
        tags: { tag_id: string; name: string }[];
        annotationSources: { id: string; name: string }[];
        metadataFieldNames: string[];
        value?: string;
        onValueChange: (value: string | undefined) => void;
    }

    let { kind, tags, annotationSources, metadataFieldNames, value, onValueChange }: Props =
        $props();

    const LABELS: Record<GoalInputKind, { label: string; empty: string }> = {
        tag: { label: 'Similar to the samples in', empty: 'No sample tags yet' },
        annotation_source: { label: 'Using classes from', empty: 'No annotation sources yet' },
        metadata_field: { label: 'Across the values of', empty: 'No categorical metadata yet' }
    };

    const items = $derived.by(() => {
        if (kind === 'tag') return tags.map((tag) => ({ value: tag.tag_id, label: tag.name }));
        if (kind === 'annotation_source') {
            return annotationSources.map((source) => ({ value: source.id, label: source.name }));
        }
        return metadataFieldNames.map((name) => ({ value: name, label: name }));
    });
</script>

<div class="grid gap-2" data-testid="sampling-goal-input">
    <Label for="sampling-goal-input-select">{LABELS[kind].label}</Label>
    <Select
        {items}
        {value}
        placeholder={items.length === 0 ? LABELS[kind].empty : 'Choose one'}
        class="w-full"
        testId="sampling-goal-input-select"
        selectProps={{ id: 'sampling-goal-input-select' }}
        onValueChange={(selected) => onValueChange(selected || undefined)}
    />
</div>
