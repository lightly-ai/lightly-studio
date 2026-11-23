import { describe, expect, it } from 'vitest';
import { readOnlyText, roundText, turnText } from './workflowFileTexts';

const file = {
    state: 'in_progress' as const,
    round: 1,
    labeler: 'pedro@example.com',
    reviewer: 'marta@example.com',
    your_role: 'labeler' as const,
    can_edit: true,
    your_turn: true,
    waiting_for: 'pedro@example.com'
};

describe('roundText', () => {
    it('shows --- until the file is first submitted, then the round', () => {
        expect(roundText({ state: 'not_started', round: 1 })).toBe('---');
        expect(roundText({ state: 'in_progress', round: 1 })).toBe('---');
        expect(roundText({ state: 'in_review', round: 1 })).toBe('Round 1');
        expect(roundText({ state: 'rework', round: 2 })).toBe('Round 2');
    });
});

describe('turnText', () => {
    it('says whose turn it is', () => {
        expect(turnText(file)).toEqual({ text: 'Your turn', yourTurn: true });
        expect(
            turnText({
                ...file,
                state: 'in_review',
                your_turn: false,
                waiting_for: 'marta@example.com'
            })
        ).toEqual({ text: 'Waiting for marta@example.com', yourTurn: false });
        expect(
            turnText({
                ...file,
                state: 'accepted',
                your_turn: false,
                waiting_for: null
            })
        ).toEqual({ text: 'Done', yourTurn: false });
        expect(turnText({ ...file, your_turn: false, waiting_for: null })).toEqual({
            text: 'Waiting for an assignee',
            yourTurn: false
        });
    });

    it('shows whose turn it really is when an unassigned admin can edit', () => {
        expect(turnText({ ...file, your_turn: false })).toEqual({
            text: 'Waiting for pedro@example.com',
            yourTurn: false
        });
    });
});

describe('readOnlyText', () => {
    it('is empty when the user can edit', () => {
        expect(readOnlyText(file)).toBeNull();
    });

    it('explains why the file is read-only', () => {
        expect(readOnlyText({ ...file, state: 'in_review', can_edit: false })).toBe(
            'You submitted this file. It’s read-only while marta@example.com reviews it.'
        );
        expect(readOnlyText({ ...file, your_role: 'reviewer', can_edit: false })).toBe(
            'pedro@example.com is working on this file. You can edit it once it’s submitted for review.'
        );
        expect(readOnlyText({ ...file, state: 'accepted', can_edit: false })).toBe(
            'Accepted by marta@example.com. Only an admin can change an accepted file.'
        );
        expect(readOnlyText({ ...file, your_role: null, can_edit: false })).toBe(
            'You aren’t assigned to this batch, so this file is read-only for you.'
        );
    });
});
