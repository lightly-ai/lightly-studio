import { describe, expect, it } from 'vitest';
import { parseClassNames, readOnnxMetadata } from './onnxMetadata';
import { encodeModel } from './testHelpers';

describe('readOnnxMetadata', () => {
    it('reads metadata_props and skips other fields', () => {
        const bytes = encodeModel({ classes: '{"0":"person"}', model_name: 'ltdetrv2-s-coco' });

        expect(readOnnxMetadata(bytes)).toEqual({
            classes: '{"0":"person"}',
            model_name: 'ltdetrv2-s-coco'
        });
    });
});

describe('parseClassNames', () => {
    it('keeps insertion order of class ids', () => {
        expect(parseClassNames('{"5":"b","1":"a"}')).toEqual(['b', 'a']);
    });

    it('decodes escaped characters in class names', () => {
        expect(parseClassNames('{"0":"say \\"hi\\""}')).toEqual(['say "hi"']);
    });
});
