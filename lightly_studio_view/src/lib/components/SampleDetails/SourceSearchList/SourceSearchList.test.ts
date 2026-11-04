import { beforeAll, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import SourceSearchList from './SourceSearchList.svelte';

const setup = () => {
    const onPick = vi.fn();
    const onCancel = vi.fn();
    render(SourceSearchList, {
        props: {
            sources: [
                { collection_id: 's1', name: 'labels' },
                { collection_id: 's2', name: 'predictions' },
                { collection_id: 's3', name: 'model-preds' }
            ],
            excludeSourceId: 's2',
            onPick,
            onCancel
        }
    });
    return { onPick, onCancel, user: userEvent.setup() };
};

describe('SourceSearchList', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('lists sources except the excluded one', () => {
        setup();
        const rows = screen.getAllByRole('option').map((row) => row.textContent?.trim());
        expect(rows).toEqual(['labels', 'model-preds']);
        expect(screen.getByRole('combobox')).toHaveFocus();
    });

    it('picks the first match on Enter', async () => {
        const { onPick, user } = setup();
        await user.keyboard('lab{Enter}');
        expect(onPick).toHaveBeenCalledWith('labels');
    });

    it('shows an empty message and ignores Enter when nothing matches', async () => {
        const { onPick, user } = setup();
        await user.keyboard('zzz{Enter}');
        expect(screen.getByText('No annotation source matches')).toBeInTheDocument();
        expect(onPick).not.toHaveBeenCalled();
    });

    it('cancels on Escape', async () => {
        const { onCancel, user } = setup();
        await user.keyboard('{Escape}');
        expect(onCancel).toHaveBeenCalledTimes(1);
    });

    it('hints how to go back, outside the options', () => {
        setup();
        const hint = screen.getByText('Esc to go back');
        expect(hint).toBeInTheDocument();
        expect(hint.closest('[role="option"]')).toBeNull();
    });
});
