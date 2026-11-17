import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import SourceSearchList from './SourceSearchList.svelte';

const mocks = vi.hoisted(() => ({
    sources: undefined as { collection_id: string; name: string }[] | undefined
}));

vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: () => ({ data: mocks.sources, isPending: !mocks.sources })
}));

const setup = (props: Record<string, unknown> = {}) => {
    const onPick = vi.fn();
    const onCancel = vi.fn();
    render(SourceSearchList, {
        props: { collectionId: 'col-1', excludeSourceId: 's2', onPick, onCancel, ...props }
    });
    return { onPick, onCancel, user: userEvent.setup() };
};

const rowTexts = () => screen.getAllByRole('option').map((row) => row.textContent?.trim());

describe('SourceSearchList', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });
    beforeEach(() => {
        mocks.sources = [
            { collection_id: 's1', name: 'labels' },
            { collection_id: 's2', name: 'predictions' },
            { collection_id: 's3', name: 'model-preds' }
        ];
    });

    it('lists sources except the excluded one', () => {
        setup();
        expect(rowTexts()).toEqual(['labels', 'model-preds']);
        expect(screen.getByRole('combobox', { name: 'Annotation source' })).toHaveFocus();
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

    it('does not offer a case variant of an existing source as new', async () => {
        const { user } = setup({ allowCreate: true });
        await user.keyboard('LABELS');
        expect(rowTexts()).toEqual(['labels']);
    });

    it('offers to create a typed source when allowed, not for an existing name', async () => {
        const { onPick, user } = setup({ allowCreate: true });
        await user.keyboard('predictions');
        expect(screen.queryByRole('option', { name: /Create:/ })).not.toBeInTheDocument();

        await user.clear(screen.getByRole('combobox'));
        await user.keyboard(' review {Enter}');
        expect(onPick).toHaveBeenCalledWith('review');
    });

    it('says the sources load and offers no create row until they did', async () => {
        mocks.sources = undefined;
        const { user } = setup({ allowCreate: true });
        await user.keyboard('review');
        expect(screen.getByText('Loading annotation sources…')).toBeInTheDocument();
        expect(screen.queryByText('Create:')).not.toBeInTheDocument();
    });

    it('lists a disabled source with its note and skips it on Enter', async () => {
        const { onPick, user } = setup({ disabledSources: { names: ['labels'], note: 'Hidden' } });
        expect(rowTexts()).toEqual(['labels Hidden', 'model-preds']);
        await user.keyboard('{Enter}');
        expect(onPick).toHaveBeenCalledWith('model-preds');
    });

    it('cancels on Escape', async () => {
        const { onCancel, user } = setup();
        await user.keyboard('{Escape}');
        expect(onCancel).toHaveBeenCalledTimes(1);
    });

    it('hints how to go back only when asked', () => {
        setup({ showBackHint: true });
        expect(screen.getByTestId('search-list-back-hint').closest('[role="option"]')).toBeNull();
    });
});
