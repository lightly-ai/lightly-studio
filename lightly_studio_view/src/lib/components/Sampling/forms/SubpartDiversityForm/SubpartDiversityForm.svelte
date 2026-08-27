<script lang="ts">
    import type { SubpartDiversityParams, StrategyParams } from '$lib/hooks/useStrategyBuilder';
    import StrengthField from '$lib/components/Sampling/forms/StrengthField/StrengthField.svelte';
    import AnnotationSourceSelect from '$lib/components/AnnotationSourceSelect/AnnotationSourceSelect.svelte';
    import { Label } from '$lib/components/ui/label';
    import FieldTooltip from '$lib/components/FieldTooltip/FieldTooltip.svelte';

    interface Props {
        instanceId: string;
        params: SubpartDiversityParams;
        annotationSourceOptions?: { id: string; name: string }[];
        onUpdate: (params: Partial<StrategyParams>) => void;
    }

    let { instanceId, params, annotationSourceOptions = [], onUpdate }: Props = $props();
</script>

<div class="grid gap-3" data-testid="subpart-diversity-form">
    <div class="grid gap-2">
        <div class="flex items-center gap-1.5">
            <Label for={`subpart-diversity-annotation-source-${instanceId}`}>
                Annotation Source
            </Label>
            <FieldTooltip
                content="Optional annotation source used to identify subparts (crops). When left blank, crop embeddings from all annotation sources are merged."
            />
        </div>
        <AnnotationSourceSelect
            id={`subpart-diversity-annotation-source-${instanceId}`}
            sourceOptions={annotationSourceOptions}
            selectedSource={params.annotation_source_id}
            allowDeselect
            onSelect={(id) => onUpdate({ annotation_source_id: id })}
        />
    </div>
    <StrengthField
        strength={params.strength}
        id={`subpart-diversity-strength-${instanceId}`}
        testid={`strategy-subpart-diversity-strength-input-${instanceId}`}
        min={0}
        onUpdate={(strength) => onUpdate({ strength })}
    />
</div>
