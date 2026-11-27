import { describe, expect, it } from 'vitest';
import { LOAD_MODEL_FILE_VALUE, toModelSelectItems } from './modelSelectItems';

describe('toModelSelectItems', () => {
    it('groups models by where they run and offers to load a model file', () => {
        const items = toModelSelectItems([
            { id: 'coco', task: 'object_detection', class_names: [], runsIn: 'browser' },
            { id: 'seg', task: 'instance_segmentation', class_names: [], runsIn: 'server' }
        ]);

        expect(items.map(({ value, label, group }) => ({ value, label, group }))).toEqual([
            { value: 'browser:coco', label: 'coco', group: 'Browser · Object detection' },
            {
                value: LOAD_MODEL_FILE_VALUE,
                label: 'Load model file (.onnx)…',
                group: 'Browser · Object detection'
            },
            { value: 'server:seg', label: 'seg', group: 'Server · Instance segmentation' }
        ]);
    });
});
