import { render } from '@testing-library/svelte';
import { afterEach, describe, expect, it } from 'vitest';
import { AnnotationType } from '$lib/api/lightly_studio_local';
import { useAnnotationCollectionsFilter } from '$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter';
import { useCustomSourceColors } from '$lib/hooks/useCustomSourceColors/useCustomSourceColors';
import { getColorBySource } from '$lib/utils';
import SampleClassificationPills from './SampleClassificationPills.svelte';

describe('SampleClassificationPills', () => {
    const { setSelectedCollectionIds, setCollectionIdToName } = useAnnotationCollectionsFilter();

    afterEach(() => {
        useCustomSourceColors().clearCustomColors();
        setSelectedCollectionIds([]);
        setCollectionIdToName({});
    });

    it('colors a source pill by the source color for its colorKey', () => {
        useCustomSourceColors().setCustomColor('Source A', '#ff0000', 1);
        setCollectionIdToName({ 'col-a': 'Source A', 'col-b': 'Source B' });
        setSelectedCollectionIds(['col-a', 'col-b']);

        const { getByTitle } = render(SampleClassificationPills, {
            props: {
                sample: {
                    annotations: [
                        {
                            annotation_collection_id: 'col-a',
                            annotation_type: AnnotationType.CLASSIFICATION,
                            annotation_label: { annotation_label_name: 'car' }
                        }
                    ]
                } as never
            }
        });

        const pill = getByTitle('Source A: car');
        expect(pill.style.backgroundColor).toBe(getColorBySource('Source A', 0.9).color);
    });
});
