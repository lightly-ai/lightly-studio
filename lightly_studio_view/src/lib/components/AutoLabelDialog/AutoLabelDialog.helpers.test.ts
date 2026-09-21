import { describe, expect, it } from 'vitest';
import { supportsTask } from './AutoLabelDialog.helpers';

describe('supportsTask', () => {
    it('supports a task the model serves directly', () => {
        expect(
            supportsTask({
                capabilities: ['object_detection_image_bytes'],
                task: 'object_detection'
            })
        ).toBe(true);
        expect(
            supportsTask({ capabilities: ['segmentation_image_bytes'], task: 'segmentation' })
        ).toBe(true);
    });

    it('supports object detection on a segmentation-only model', () => {
        expect(
            supportsTask({ capabilities: ['segmentation_image_bytes'], task: 'object_detection' })
        ).toBe(true);
    });

    it('does not support segmentation on a detection-only model', () => {
        expect(
            supportsTask({ capabilities: ['object_detection_image_bytes'], task: 'segmentation' })
        ).toBe(false);
    });

    it('supports nothing without capabilities', () => {
        expect(supportsTask({ capabilities: undefined, task: 'object_detection' })).toBe(false);
        expect(supportsTask({ capabilities: [], task: 'segmentation' })).toBe(false);
    });
});
