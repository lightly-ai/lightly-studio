import { beforeAll, describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import ClassSearchList from './ClassSearchList.svelte';

const setup = (props: Record<string, unknown> = {}) => {
    const onPick = vi.fn();
    const onCancel = vi.fn();
    render(ClassSearchList, {
        props: {
            names: ['bobcat', 'coyote', 'deer', 'raccoon'],
            recent: ['deer'],
            onPick,
            onCancel,
            ...props
        }
    });
    return { onPick, onCancel, user: userEvent.setup() };
};

const rowTexts = () => screen.getAllByRole('option').map((row) => row.textContent?.trim());

describe('ClassSearchList', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('lists recent classes first and focuses the input', () => {
        setup();
        expect(rowTexts()).toEqual(['deer', 'bobcat', 'coyote', 'raccoon']);
        expect(screen.getByRole('combobox')).toHaveFocus();
    });

    it('picks the first match on Enter and offers a create row', async () => {
        const { onPick, user } = setup();
        await user.keyboard('co');
        expect(rowTexts()).toEqual(['coyote', 'raccoon', 'Create: co']);
        await user.keyboard('{Enter}');
        expect(onPick).toHaveBeenCalledWith('coyote');
    });

    it('creates a new class on Enter when nothing matches', async () => {
        const { onPick, user } = setup();
        await user.keyboard('fox{Enter}');
        expect(onPick).toHaveBeenCalledWith('fox');
    });

    it('shows no create row for a case-insensitive exact match', async () => {
        const { onPick, user } = setup();
        await user.keyboard('DEER');
        expect(rowTexts()).toEqual(['deer']);
        await user.keyboard('{Enter}');
        expect(onPick).toHaveBeenCalledWith('deer');
    });

    it('moves the highlight with the arrow keys', async () => {
        const { onPick, user } = setup();
        await user.keyboard('{ArrowDown}{Enter}');
        expect(onPick).toHaveBeenCalledWith('bobcat');
    });

    it('cancels on Escape without leaking the key to window', async () => {
        const { onCancel, user } = setup();
        const onWindowKey = vi.fn();
        window.addEventListener('keydown', onWindowKey);
        await user.keyboard('{Escape}');
        window.removeEventListener('keydown', onWindowKey);
        expect(onCancel).toHaveBeenCalledTimes(1);
        expect(onWindowKey).not.toHaveBeenCalled();
    });

    it('hints how to go back, outside the options, only when asked', () => {
        setup({ showBackHint: true });
        const hint = screen.getByTestId('search-list-back-hint');
        expect(hint.closest('[role="option"]')).toBeNull();
        expect(hint).toHaveTextContent('Esc to go back');
        expect(within(hint).getByText('Esc').tagName).toBe('KBD');
    });

    it('does not hint going back by default, for example in a popover that Esc closes', () => {
        setup();
        expect(screen.queryByTestId('search-list-back-hint')).not.toBeInTheDocument();
    });
});
