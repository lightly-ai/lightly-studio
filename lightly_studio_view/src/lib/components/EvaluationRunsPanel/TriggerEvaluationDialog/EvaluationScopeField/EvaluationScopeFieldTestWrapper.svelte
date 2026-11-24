<script lang="ts">
    import EvaluationScopeField from './EvaluationScopeField.svelte';

    let {
        tags,
        selectedTagIds = $bindable([])
    }: {
        tags: { tag_id: string; name: string }[];
        selectedTagIds?: string[];
    } = $props();
</script>

<EvaluationScopeField {tags} bind:selectedTagIds />

<span data-testid="selected-tag-ids">{selectedTagIds.join(',')}</span>
