<script lang="ts">
    import type { TagView } from '$lib/services/types';

    interface Props {
        options: TagView[];
        attachedTagNames: Set<string>;
        busy: boolean;
        onSelect: (name: string) => void;
    }

    let { options, attachedTagNames, busy, onSelect }: Props = $props();
</script>

<button
    type="button"
    data-testid="mock-add-existing"
    data-attached-count={attachedTagNames.size}
    disabled={busy}
    onclick={() => onSelect(options[0]?.name ?? '')}
>
    Add existing
</button>
<button
    type="button"
    data-testid="mock-add-new"
    disabled={busy}
    onclick={() => onSelect('Fresh Tag')}
>
    Add new
</button>
