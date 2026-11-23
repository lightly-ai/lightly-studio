import { describe, expect, it } from 'vitest';
import { legacyAllowedTransitions } from './legacyAllowedTransitions';
import { workflowFile } from '../workflowFile.fixture';

describe('legacyAllowedTransitions', () => {
    it.each([
        ['labeler', 'in_progress', true, ['in_review']],
        ['labeler', 'rework', true, ['in_review']],
        ['labeler', 'not_started', true, []],
        ['labeler', 'in_review', false, []],
        ['reviewer', 'in_review', true, ['rework', 'accepted']],
        ['reviewer', 'in_progress', false, []],
        ['reviewer', 'accepted', false, []],
        [null, 'in_review', false, []]
    ] as const)(
        '%s on a %s file (can edit: %s) may move to %j',
        (role, state, canEdit, expected) => {
            expect(
                legacyAllowedTransitions({
                    ...workflowFile,
                    your_role: role,
                    state,
                    can_edit: canEdit
                })
            ).toEqual(expected);
        }
    );
});
