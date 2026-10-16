import { describe, expect, it } from 'vitest';
import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
import {
    canInferFromPoints,
    getClassNameAtPoint,
    getPointSign
} from './SmartSelectOverlay.helpers';

const detection = (name: string, confidence: number, x: number) =>
    ({
        annotation_type: AnnotationType.OBJECT_DETECTION,
        confidence,
        object_detection_details: { x, y: 0, width: 10, height: 10 },
        annotation_label: { annotation_label_name: name }
    }) as unknown as AnnotationView;

describe('SmartSelectOverlay.helpers', () => {
    it('maps clicks to point signs based on the provider capabilities', () => {
        const all = { positivePoints: true, negativePoints: true };
        expect(getPointSign({ shiftKey: false, ...all })).toBe(true);
        expect(getPointSign({ shiftKey: true, ...all })).toBe(false);
        expect(getPointSign({ shiftKey: true, ...all, negativePoints: false })).toBeNull();
        expect(getPointSign({ shiftKey: false, ...all, positivePoints: false })).toBeNull();
    });

    it('needs a positive point to infer', () => {
        expect(canInferFromPoints([{ x: 0, y: 0, positive: false }])).toBe(false);
        expect(
            canInferFromPoints([
                { x: 0, y: 0, positive: false },
                { x: 0, y: 0, positive: true }
            ])
        ).toBe(true);
    });

    it('takes the class of the most confident detection under a positive point', () => {
        const annotations = [detection('cat', 0.4, 0), detection('dog', 0.9, 0)];
        const image = { width: 100, height: 100 };
        expect(getClassNameAtPoint(annotations, { x: 0.05, y: 0.05, positive: true }, image)).toBe(
            'dog'
        );
        expect(
            getClassNameAtPoint(annotations, { x: 0.05, y: 0.05, positive: false }, image)
        ).toBeNull();
        expect(
            getClassNameAtPoint(annotations, { x: 0.5, y: 0.5, positive: true }, image)
        ).toBeNull();
    });
});
