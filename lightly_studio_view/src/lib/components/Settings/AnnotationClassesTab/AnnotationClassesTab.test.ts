import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as appState from '$app/state';
import AnnotationClassesTab from './AnnotationClassesTab.svelte';

const mocks = vi.hoisted(() => ({
    addClass: vi.fn(),
    data: [] as unknown[] | undefined,
    isError: false
}));

vi.mock('./useAnnotationClasses', () => ({
    useAnnotationClasses: () => ({
        query: {
            data: mocks.data,
            isLoading: mocks.data === undefined && !mocks.isError,
            isError: mocks.isError
        },
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
        mocks.isError = false;
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

    it('does not add on Enter while the classes load', async () => {
        mocks.data = undefined;
        render(AnnotationClassesTab);
        await fireEvent.input(input(), { target: { value: 'bear' } });

        await fireEvent.keyDown(input(), { key: 'Enter' });

        expect(mocks.addClass).not.toHaveBeenCalled();
        expect(screen.queryByText(/Add new annotation class/)).not.toBeInTheDocument();
        expect(screen.queryByText(/No annotation class matches/)).not.toBeInTheDocument();
    });

    it('does not add a class twice while adding', async () => {
        mocks.addClass.mockReturnValue(new Promise(() => {}));
        render(AnnotationClassesTab);
        await fireEvent.input(input(), { target: { value: 'wolf' } });

        await fireEvent.keyDown(input(), { key: 'Enter' });
        await fireEvent.keyDown(input(), { key: 'Enter' });

        expect(mocks.addClass).toHaveBeenCalledTimes(1);
    });

    it('keeps text typed while a class is being added', async () => {
        let resolveAdd: (value: unknown) => void = () => {};
        mocks.addClass.mockReturnValue(new Promise((resolve) => (resolveAdd = resolve)));
        render(AnnotationClassesTab);
        await fireEvent.input(input(), { target: { value: 'wolf' } });
        await fireEvent.keyDown(input(), { key: 'Enter' });

        await fireEvent.input(input(), { target: { value: 'fox' } });
        resolveAdd({ annotation_label_id: 'new' });
        await new Promise((resolve) => setTimeout(resolve));

        expect(input()).toHaveValue('fox');
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

    it('shows an error and no add when the classes fail to load', async () => {
        mocks.data = undefined;
        mocks.isError = true;
        render(AnnotationClassesTab);
        await fireEvent.input(input(), { target: { value: 'wolf' } });

        expect(screen.getByText('Could not load the annotation classes.')).toBeInTheDocument();
        expect(screen.queryByText(/no annotation classes yet/)).not.toBeInTheDocument();
        expect(screen.queryByText(/Add new annotation class/)).not.toBeInTheDocument();
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
});
