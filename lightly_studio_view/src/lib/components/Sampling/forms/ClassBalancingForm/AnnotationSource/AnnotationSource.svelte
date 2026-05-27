<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import * as Select from '$lib/components/ui/select';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';
    import type { ClassBalancingAnnotationSource } from '$lib/hooks/useStrategyBuilder';

    interface Props {
        annotationSource: ClassBalancingAnnotationSource;
        onUpdate: (source: ClassBalancingAnnotationSource) => void;
    }

    let { annotationSource, onUpdate }: Props = $props();

    const ANNOTATION_SOURCE_OPTIONS: { value: ClassBalancingAnnotationSource; label: string }[] = [
        { value: 'uniform', label: 'Uniform' },
        { value: 'input', label: 'Input' },
        { value: 'dictionary', label: 'Dictionary' }
    ];
</script>

<div class="grid gap-2">
    <div class="flex items-center gap-1.5">
        <Label>Annotation source</Label>
        <FieldTooltip
            content="Where class labels come from. Choose how the target distribution is defined."
        />
    </div>
    <Select.Root
        type="single"
        value={annotationSource}
        onValueChange={(value) => onUpdate(value as ClassBalancingAnnotationSource)}
    >
        <Select.Trigger class="w-full" data-testid="class-balancing-annotation-source">
            {ANNOTATION_SOURCE_OPTIONS.find((o) => o.value === annotationSource)?.label}
        </Select.Trigger>
        <Select.Content>
            <Select.Group>
                {#each ANNOTATION_SOURCE_OPTIONS as option (option.value)}
                    <Select.Item
                        value={option.value}
                        label={option.label}
                        data-testid={`class-balancing-annotation-source-${option.value}`}
                    >
                        {option.label}
                    </Select.Item>
                {/each}
            </Select.Group>
        </Select.Content>
    </Select.Root>
</div>
