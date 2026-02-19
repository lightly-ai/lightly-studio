<script lang="ts">
    import CreateCaptionField from './CreateCaptionField.svelte';

    let activeDraftId = $state<string | null>(null);

    const onCreate = async () => true;
</script>

<div data-testid="row-a">
    <CreateCaptionField
        {onCreate}
        canStartDraft={activeDraftId === null || activeDraftId === 'a'}
        isCreatingCaption={activeDraftId === 'a'}
        onCreatingCaptionChange={(isOpen) => {
            if (isOpen) {
                activeDraftId = 'a';
                return;
            }
            if (activeDraftId === 'a') {
                activeDraftId = null;
            }
        }}
    />
</div>

<div data-testid="row-b">
    <CreateCaptionField
        {onCreate}
        canStartDraft={activeDraftId === null || activeDraftId === 'b'}
        isCreatingCaption={activeDraftId === 'b'}
        onCreatingCaptionChange={(isOpen) => {
            if (isOpen) {
                activeDraftId = 'b';
                return;
            }
            if (activeDraftId === 'b') {
                activeDraftId = null;
            }
        }}
    />
</div>
