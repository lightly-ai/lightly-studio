import { describe, expect, it } from 'vitest';
import { buildDistributionSources } from './distributionSources';
import type { DistributionSource } from '$lib/components/DatasetDistributionPanel';

const classSource: DistributionSource = { id: 'classes', label: 'Annotation classes', data: [] };
const metadataSource: DistributionSource = { id: 'metadata', label: 'Metadata', data: [] };

describe('buildDistributionSources', () => {
    it('includes both sources when classes exist and metadata is available', () => {
        expect(
            buildDistributionSources({ classSource, metadataSource, hasAnnotationClasses: true })
        ).toEqual([classSource, metadataSource]);
    });

    it('drops the class source when no annotation classes exist and metadata is available', () => {
        expect(
            buildDistributionSources({ classSource, metadataSource, hasAnnotationClasses: false })
        ).toEqual([metadataSource]);
    });

    it('keeps the class source when no annotation classes exist but there is no metadata either', () => {
        // Otherwise the panel would have nothing at all to show.
        expect(
            buildDistributionSources({
                classSource,
                metadataSource: null,
                hasAnnotationClasses: false
            })
        ).toEqual([classSource]);
    });
});
