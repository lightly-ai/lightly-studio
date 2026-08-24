<script lang="ts">
    import { Button } from '$lib/components';
    import { Label } from '$lib/components/ui/label';
    import { Switch } from '$lib/components/ui/switch';

    interface Props {
        mode: 'temp' | 'existing' | null;
        pendingAction: 'continue' | 'finish' | null;
        canSubmit: boolean;
        isShowingTrainingSamples: boolean;
        onShowTrainingSamplesChange: (checked: boolean) => void;
        onCancel: () => void;
        onContinue: () => void;
        onFinish: () => void;
    }

    const {
        mode,
        pendingAction,
        canSubmit,
        isShowingTrainingSamples,
        onShowTrainingSamplesChange,
        onCancel,
        onContinue,
        onFinish
    }: Props = $props();
    const isSubmitting = $derived(pendingAction !== null);
</script>

<div class="flex flex-wrap items-center justify-between gap-3">
    <div class="flex items-center gap-3">
        <Label class="text-foreground">Show All Training Samples</Label>
        <Switch
            checked={isShowingTrainingSamples}
            onCheckedChange={onShowTrainingSamplesChange}
            disabled={isSubmitting}
        />
    </div>
    <div class="flex flex-wrap justify-end gap-2">
        <Button
            variant="outline"
            buttonProps={{
                onclick: onCancel,
                disabled: isSubmitting,
                'data-testid': 'refine-dialog-cancel'
            }}>{mode === 'temp' ? 'Cancel' : 'Close'}</Button
        >
        <Button
            variant="secondary"
            isPending={pendingAction === 'continue'}
            buttonProps={{
                onclick: onContinue,
                disabled: isSubmitting || !canSubmit,
                'data-testid': 'refine-classifier-button'
            }}>Apply Corrections & Continue</Button
        >
        <Button
            variant="default"
            isPending={pendingAction === 'finish'}
            buttonProps={{
                onclick: onFinish,
                disabled: isSubmitting || !canSubmit,
                'data-testid': 'finish-classifier-button'
            }}>{mode === 'temp' ? 'Save Classifier & Finish' : 'Apply Corrections & Finish'}</Button
        >
    </div>
</div>
