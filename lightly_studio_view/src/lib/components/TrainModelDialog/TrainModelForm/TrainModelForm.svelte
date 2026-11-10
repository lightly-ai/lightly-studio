<script lang="ts">
    import { Button } from '$lib/components';
    import { Select } from '$lib/components/Select';
    import { Input } from '$lib/components/ui/input';
    import { Label } from '$lib/components/ui/label';
    import type { CreateTrainingRunData } from '$lib/api/lightly_studio_local/types.gen';
    import {
        DEFAULT_TRAINING_STEPS,
        TRAINING_MODELS,
        canStartTraining
    } from '../TrainModelDialog.helpers';

    interface Option {
        value: string;
        label: string;
    }

    interface Props {
        tagOptions: Option[];
        sourceOptions: Option[];
        isStarting: boolean;
        onStart: (body: CreateTrainingRunData['body']) => void;
    }

    let { tagOptions, sourceOptions, isStarting, onStart }: Props = $props();

    let trainTagId = $state<string | undefined>(undefined);
    let valTagId = $state<string | undefined>(undefined);
    let gtSourceId = $state<string | undefined>(undefined);
    let modelName = $state(TRAINING_MODELS[0].value);
    let steps = $state(DEFAULT_TRAINING_STEPS);

    const canStart = $derived(
        canStartTraining({ trainTagId, valTagId, gtSourceId, steps, isStarting })
    );
    const tagItems = (excluded: string | undefined) =>
        tagOptions.map((tag) => ({ ...tag, disabled: tag.value === excluded }));

    const handleSubmit = (event: SubmitEvent) => {
        event.preventDefault();
        if (!canStart) return;
        onStart({
            train_tag_id: trainTagId!,
            val_tag_id: valTagId!,
            gt_annotation_collection_id: gtSourceId!,
            model_name: modelName,
            steps
        });
    };
</script>

<form class="grid gap-4" onsubmit={handleSubmit} data-testid="train-model-form">
    <div class="grid gap-2">
        <Label class="text-foreground">Train tag</Label>
        <Select
            items={tagItems(valTagId)}
            value={trainTagId}
            placeholder={tagOptions.length === 0 ? 'No tags. Use "Split dataset".' : 'Select a tag'}
            onValueChange={(value) => (trainTagId = value)}
            testId="train-tag-select"
        />
    </div>
    <div class="grid gap-2">
        <Label class="text-foreground">Val tag</Label>
        <Select
            items={tagItems(trainTagId)}
            value={valTagId}
            placeholder="Select a tag"
            onValueChange={(value) => (valTagId = value)}
            testId="val-tag-select"
        />
    </div>
    <div class="grid gap-2">
        <Label class="text-foreground">Ground truth annotation source</Label>
        <Select
            items={sourceOptions}
            value={gtSourceId}
            placeholder={sourceOptions.length === 0
                ? 'No object detection annotation sources'
                : 'Select a source'}
            onValueChange={(value) => (gtSourceId = value)}
            testId="gt-source-select"
        />
    </div>
    <div class="grid gap-2">
        <Label class="text-foreground">Model</Label>
        <Select
            items={TRAINING_MODELS}
            value={modelName}
            onValueChange={(value) => (modelName = value)}
            testId="model-select"
        />
    </div>
    <div class="grid gap-2">
        <Label for="training-steps" class="text-foreground">Steps</Label>
        <Input
            id="training-steps"
            type="number"
            min="1"
            bind:value={steps}
            data-testid="training-steps-input"
        />
    </div>
    <Button
        variant="default"
        isPending={isStarting}
        buttonProps={{ type: 'submit', disabled: !canStart, 'data-testid': 'train-model-submit' }}
    >
        Start training
    </Button>
</form>
