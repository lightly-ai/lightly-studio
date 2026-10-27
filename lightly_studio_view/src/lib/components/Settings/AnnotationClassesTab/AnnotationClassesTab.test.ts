import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as appState from '$app/state';
import AnnotationClassesTab from './AnnotationClassesTab.svelte';

const mocks = vi.hoisted(() => ({
    addClass: vi.fn(),
    data: [] as unknown[]
}));

vi.mock('./useAnnotationClasses', () => ({
    useAnnotationClasses: () => ({
        query: { data: mocks.data, isLoading: false },
        addClass: mocks.addClass,
        renameClass: vi.fn(),
        deleteClass: vi.fn()
    })
}));

const mockParams = (params: Record<string, string>) => {
    vi.spyOn(appState, 'page', 'get').mockReturnValue({
        params
    } as unknown as typeof appState.page);
};

describe('AnnotationClassesTab', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        mocks.addClass.mockResolvedValue({ annotation_label_id: 'new' });
        mocks.data = [
            { annotation_label_id: 'c', annotation_label_name: 'cat', annotation_count: 0 },
            { annotation_label_id: 'b', annotation_label_name: 'bear', annotation_count: 2 }
        ];
        mockParams({ dataset_id: 'd', collection_id: 'c1' });
    });

    const input = () => screen.getByLabelText('Find or add an annotation class');

    it('lists classes sorted by name', () => {
        render(AnnotationClassesTab);

        const names = screen.getAllByText(/^(bear|cat)$/).map((el) => el.textContent);
        expect(names).toEqual(['bear', 'cat']);
        expect(screen.getByText(/2 annotation classes/)).toBeInTheDocument();
    });

    it('shows a filtered count', async () => {
        render(AnnotationClassesTab);

        await fireEvent.input(input(), { target: { value: 'bea' } });

        expect(screen.getByText(/1 of\s+2 annotation classes/)).toBeInTheDocument();
    });

    it('does not add on Enter while a class matches', async () => {
        render(AnnotationClassesTab);
        await fireEvent.input(input(), { target: { value: 'bea' } });

        const notPrevented = await fireEvent.keyDown(input(), { key: 'Enter' });

        expect(notPrevented).toBe(false);
        expect(mocks.addClass).not.toHaveBeenCalled();
    });

    it('adds a new class on Enter and clears the input', async () => {
        render(AnnotationClassesTab);
        await fireEvent.input(input(), { target: { value: 'wolf' } });

        await fireEvent.keyDown(input(), { key: 'Enter' });

        expect(mocks.addClass).toHaveBeenCalledWith('wolf');
        await vi.waitFor(() => expect(input()).toHaveValue(''));
    });

    it('does not add a class twice while adding', async () => {
        mocks.addClass.mockReturnValue(new Promise(() => {}));
        render(AnnotationClassesTab);
        await fireEvent.input(input(), { target: { value: 'wolf' } });

        await fireEvent.keyDown(input(), { key: 'Enter' });
        await fireEvent.keyDown(input(), { key: 'Enter' });

        expect(mocks.addClass).toHaveBeenCalledTimes(1);
    });

    it('does not add on Enter while an IME composes text', async () => {
        render(AnnotationClassesTab);
        await fireEvent.input(input(), { target: { value: 'wolf' } });

        await fireEvent.keyDown(input(), { key: 'Enter', isComposing: true });

        expect(mocks.addClass).not.toHaveBeenCalled();
    });

    it('does not throw when adding fails', async () => {
        mocks.addClass.mockRejectedValue(new Error('boom'));
        render(AnnotationClassesTab);
        await fireEvent.input(input(), { target: { value: 'wolf' } });

        await fireEvent.keyDown(input(), { key: 'Enter' });

        await vi.waitFor(() => expect(mocks.addClass).toHaveBeenCalled());
        expect(input()).toHaveValue('wolf');
    });

    it('shows that an existing class exists and offers no add row', async () => {
        render(AnnotationClassesTab);

        await fireEvent.input(input(), { target: { value: 'Bear' } });

        expect(screen.getByText(/already exists/)).toBeInTheDocument();
        expect(screen.queryByText(/Add new annotation class/)).not.toBeInTheDocument();
    });

    it('asks to open a dataset when there is no collection', () => {
        mockParams({});
        render(AnnotationClassesTab);

        expect(
            screen.getByText('Open a dataset to manage its annotation classes.')
        ).toBeInTheDocument();
        expect(screen.queryByText('bear')).not.toBeInTheDocument();
    });

    it('says that changes save immediately', () => {
        render(AnnotationClassesTab);

        expect(
            screen.getByText('Changes to annotation classes save immediately.')
        ).toBeInTheDocument();
    });
});
