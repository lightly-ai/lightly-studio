import { render } from '@testing-library/svelte';
import { afterEach, expect, it, vi } from 'vitest';
import { AnnotationType } from '$lib/api/lightly_studio_local';
import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { useCustomSourceColors } from '$lib/hooks';
import SampleClassificationPills from './SampleClassificationPills.svelte';

const { setSelectedCollectionIds, setCollectionIdToName } = useAnnotationCollectionsFilter();

vi.mock('$lib/hooks/useSettings', async (importOriginal) => {
    const { readable } = await import('svelte/store');
    const original = await importOriginal<typeof import('$lib/hooks/useSettings')>();
    return {
        ...original,
        useSettings: () => ({
            ...original.useSettings(),
            enforceColoringByClassStore: readable(false)
        })
    };
});

afterEach(() => {
    useCustomLabelColors().clearCustomColors();
    useCustomSourceColors().clearCustomColors();
    setSelectedCollectionIds([]);
    setCollectionIdToName({});
});

it('colors a source pill by the source color for its colorKey, not by its class', () => {
    useCustomSourceColors().setCustomColor('Source A', '#ff0000', 1);
    useCustomLabelColors().setCustomColor('car', '#0000ff', 1);
    setCollectionIdToName({ 'col-a': 'Source A', 'col-b': 'Source B' });
    setSelectedCollectionIds(['col-a', 'col-b']);
    const annotation = {
        annotation_collection_id: 'col-a',
        annotation_type: AnnotationType.CLASSIFICATION,
        annotation_label: { annotation_label_name: 'car' }
    };

    const { getByTitle } = render(SampleClassificationPills, {
        props: { sample: { annotations: [annotation] } as never }
    });

    expect(getByTitle('Source A: car').style.backgroundColor).toBe('rgba(255, 0, 0, 0.9)');
});
