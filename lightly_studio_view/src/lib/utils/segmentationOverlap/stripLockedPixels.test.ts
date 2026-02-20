import { describe, it, expect } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { stripLockedPixels } from './stripLockedPixels';

vi.mock('$lib/components/SampleAnnotation/utils', () => ({
    decodeRLEToBinaryMask: vi.fn((mask: number[], width: number, height: number) =>
        Uint8Array.from(mask).slice(0, width * height)
    )
}));

const sample = { width: 4, height: 4 };
const baseAnn = (id: string, mask: number[]): AnnotationView =>
    ({
        sample_id: id,
        annotation_type: 'semantic_segmentation',
        segmentation_details: { segmentation_mask: mask },
        annotation_label: { annotation_label_name: 'a', annotation_label_id: 'a' },
        parent_sample_id: 'p',
        created_at: '',
        tags: []
    }) as unknown as AnnotationView;

describe('stripLockedPixels', () => {
    it('keeps mask unchanged when no locks exist', () => {
        const mask = Uint8Array.from([1, 0, 1, 0]);

        stripLockedPixels({ mask, lockedAnnotationIds: undefined, annotations: [], sample });

        // No locks means the working mask should stay identical.
        expect(Array.from(mask)).toEqual([1, 0, 1, 0]);
    });

    it('zeros pixels that intersect locked masks', () => {
        const mask = Uint8Array.from([1, 1, 0, 0]);
        const locked = new Set(['1']);

        stripLockedPixels({
            mask,
            lockedAnnotationIds: locked,
            annotations: [baseAnn('1', [1, 1, 0, 0])],
            sample
        });

        // Both drawn pixels overlapped a locked mask, so they are removed.
        expect(Array.from(mask)).toEqual([0, 0, 0, 0]);
    });
});
