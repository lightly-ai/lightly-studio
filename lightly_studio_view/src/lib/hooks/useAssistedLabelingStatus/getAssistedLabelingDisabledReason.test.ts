import { describe, expect, it } from 'vitest';
import { getAssistedLabelingDisabledReason } from './getAssistedLabelingDisabledReason';

describe('getAssistedLabelingDisabledReason', () => {
    it('enables the tools if assisted labeling is usable', () => {
        expect(
            getAssistedLabelingDisabledReason({
                status: { unavailable_reason: null },
                isError: false
            })
        ).toBeNull();
    });

    it('disables the tools with the unavailable reason', () => {
        expect(
            getAssistedLabelingDisabledReason({
                status: { unavailable_reason: 'Set the FAL_KEY environment variable.' },
                isError: false
            })
        ).toBe('Set the FAL_KEY environment variable.');
    });

    it('keeps the loaded status after a failed refetch', () => {
        expect(
            getAssistedLabelingDisabledReason({
                status: { unavailable_reason: null },
                isError: true
            })
        ).toBeNull();
    });

    it('disables the tools while loading or after a failed request', () => {
        expect(getAssistedLabelingDisabledReason({ status: undefined, isError: false })).toBe(
            'Loading the assisted labeling status…'
        );
        expect(getAssistedLabelingDisabledReason({ status: undefined, isError: true })).toBe(
            'Could not load the assisted labeling status.'
        );
    });
});
