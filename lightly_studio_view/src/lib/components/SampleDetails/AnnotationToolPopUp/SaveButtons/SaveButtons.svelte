<script lang="ts">
    import { Button } from '$lib/components/ui/button';

    interface Props {
        saveLabel?: string;
        canSave: boolean;
        isSaving?: boolean;
        onSave: () => void;
        onClear: () => void;
    }

    let { saveLabel = 'Done', canSave, isSaving = false, onSave, onClear }: Props = $props();
</script>

<div class="flex gap-1.5">
    <Button class="h-8 flex-1" disabled={!canSave || isSaving} onclick={onSave}
        >{isSaving ? 'Saving…' : saveLabel}</Button
    >
    <Button variant="outline" class="h-8 flex-1" disabled={isSaving} onclick={onClear}>Reset</Button
    >
</div>
