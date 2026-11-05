import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import ClassPredictionStrip from './ClassPredictionStrip.svelte';

const mocks = vi.hoisted(() => ({
    state: { status: 'hidden' } as Record<string, unknown>,
    hide: vi.fn(),
    selectedAnnotationId: null as string | null,
    setAnnotationLabel: vi.fn(),
    updateLastAnnotationLabel: vi.fn(),
    addReversibleAction: vi.fn(),
    updateAnnotations: vi.fn(),
    addAnnotationLabelChangeToUndoStack: vi.fn(),
    invalidateQueries: vi.fn()
}));

vi.mock('@tanstack/svelte-query', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@tanstack/svelte-query')>()),
    useQueryClient: () => ({ invalidateQueries: mocks.invalidateQueries })
}));

vi.mock('$lib/hooks/useAnnotationClassPrediction/useAnnotationClassPrediction.svelte', () => ({
    useAnnotationClassPredictionContext: () => ({
        get state() {
            return mocks.state;
        },
        predict: vi.fn(),
        hide: mocks.hide
    })
}));

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        context: {
            get annotationId() {
                return mocks.selectedAnnotationId;
            }
        },
        setAnnotationLabel: mocks.setAnnotationLabel
    })
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        addReversibleAction: mocks.addReversibleAction,
        updateLastAnnotationLabel: mocks.updateLastAnnotationLabel
    })
}));

vi.mock('$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation', () => ({
    useUpdateAnnotationsMutation: () => ({ updateAnnotations: mocks.updateAnnotations })
}));

vi.mock('$lib/services/addAnnotationLabelChangeToUndoStack', () => ({
    addAnnotationLabelChangeToUndoStack: mocks.addAnnotationLabelChangeToUndoStack
}));

const prediction = (label_name: string, score: number) => ({
    annotation_label_id: `id-${label_name}`,
    label_name,
    score
});

const READY_STATE = {
    status: 'ready',
    annotationId: 'ann-1',
    top: [prediction('car', 0.824), prediction('truck', 0.11), prediction('bus', 0.04)]
};

const refetch = vi.fn();
const defaultProps = {
    collectionId: 'col-1',
    annotations: [{ sample_id: 'ann-1', annotation_label: { annotation_label_name: 'car' } }],
    refetch
};

describe('ClassPredictionStrip', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.state = { status: 'hidden' };
        mocks.selectedAnnotationId = 'ann-1';
        mocks.updateAnnotations.mockResolvedValue(undefined);
    });

    it('shows a spinner and "Predicting class…" while loading', () => {
        mocks.state = { status: 'loading', annotationId: 'ann-1' };
        render(ClassPredictionStrip, { props: defaultProps });

        expect(screen.getByText('Predicting class…')).toBeInTheDocument();
        expect(screen.getByTestId('class-prediction-spinner')).toBeInTheDocument();
    });

    it('shows the top 3 with key number, name and rounded percent', () => {
        mocks.state = READY_STATE;
        render(ClassPredictionStrip, { props: defaultProps });

        expect(screen.getByTestId('class-prediction-strip')).toHaveTextContent(
            '1 car 82% · 2 truck 11% · 3 bus 4%'
        );
    });

    it('relabels the annotation on key 2 and pushes an undo entry', async () => {
        mocks.state = READY_STATE;
        render(ClassPredictionStrip, { props: defaultProps });

        await fireEvent.keyDown(window, { key: '2' });

        expect(mocks.addAnnotationLabelChangeToUndoStack).toHaveBeenCalledWith(
            expect.objectContaining({
                annotations: [
                    { sample_id: 'ann-1', annotation_label: { annotation_label_name: 'car' } }
                ],
                collectionId: 'col-1'
            })
        );
        expect(mocks.updateAnnotations).toHaveBeenCalledWith([
            { annotation_id: 'ann-1', collection_id: 'col-1', label_name: 'truck' }
        ]);
        expect(mocks.setAnnotationLabel).toHaveBeenCalledWith('truck');
        expect(mocks.updateLastAnnotationLabel).toHaveBeenCalledWith('col-1', 'truck');
        expect(refetch).toHaveBeenCalled();
    });

    it('refreshes the views that read the relabeled annotation', async () => {
        mocks.state = READY_STATE;
        render(ClassPredictionStrip, { props: defaultProps });

        await fireEvent.keyDown(window, { key: '2' });

        expect(mocks.invalidateQueries).toHaveBeenCalledOnce();
        const { predicate } = mocks.invalidateQueries.mock.calls[0][0];
        const query = (key: unknown) => ({ queryKey: [key] });
        expect(
            predicate(
                query({
                    _id: 'getAnnotation',
                    path: { annotation_id: 'ann-1', collection_id: 'x' }
                })
            )
        ).toBe(true);
        expect(
            predicate(
                query({
                    _id: 'getAnnotation',
                    path: { annotation_id: 'ann-2', collection_id: 'x' }
                })
            )
        ).toBe(false);
        expect(predicate(query({ _id: 'getImage', path: { annotation_id: 'ann-1' } }))).toBe(false);
    });

    it('refreshes the annotation views on undo', async () => {
        mocks.state = READY_STATE;
        render(ClassPredictionStrip, { props: defaultProps });
        await fireEvent.keyDown(window, { key: '2' });
        mocks.invalidateQueries.mockClear();
        refetch.mockClear();

        mocks.addAnnotationLabelChangeToUndoStack.mock.calls[0][0].refresh();

        expect(mocks.invalidateQueries).toHaveBeenCalledOnce();
        expect(refetch).toHaveBeenCalledOnce();
    });

    it('ignores keys when the selected annotation is not the predicted one', async () => {
        mocks.state = READY_STATE;
        mocks.selectedAnnotationId = 'ann-2';
        render(ClassPredictionStrip, { props: defaultProps });

        await fireEvent.keyDown(window, { key: '2' });

        expect(mocks.updateAnnotations).not.toHaveBeenCalled();
    });

    it('ignores keys typed into an input or textarea', async () => {
        mocks.state = READY_STATE;
        render(ClassPredictionStrip, { props: defaultProps });
        const input = document.createElement('input');
        const textarea = document.createElement('textarea');
        document.body.append(input, textarea);

        await fireEvent.keyDown(input, { key: '2' });
        await fireEvent.keyDown(textarea, { key: '3' });

        expect(mocks.updateAnnotations).not.toHaveBeenCalled();
        input.remove();
        textarea.remove();
    });

    it('ignores keys pressed inside a dialog', async () => {
        mocks.state = READY_STATE;
        render(ClassPredictionStrip, { props: defaultProps });
        const dialog = document.createElement('div');
        dialog.setAttribute('role', 'dialog');
        const button = document.createElement('button');
        dialog.append(button);
        document.body.append(dialog);

        await fireEvent.keyDown(button, { key: '2' });

        expect(mocks.updateAnnotations).not.toHaveBeenCalled();
        dialog.remove();
    });

    it('ignores keys with a modifier held', async () => {
        mocks.state = READY_STATE;
        render(ClassPredictionStrip, { props: defaultProps });

        await fireEvent.keyDown(window, { key: '2', ctrlKey: true });
        await fireEvent.keyDown(window, { key: '2', metaKey: true });

        expect(mocks.updateAnnotations).not.toHaveBeenCalled();
    });

    it('hides when another annotation is selected', () => {
        mocks.state = READY_STATE;
        mocks.selectedAnnotationId = 'ann-2';

        render(ClassPredictionStrip, { props: defaultProps });

        expect(mocks.hide).toHaveBeenCalled();
    });

    it('stays when the predicted annotation is selected', () => {
        mocks.state = READY_STATE;

        render(ClassPredictionStrip, { props: defaultProps });

        expect(mocks.hide).not.toHaveBeenCalled();
    });

    it('hides on Escape', async () => {
        mocks.state = READY_STATE;
        render(ClassPredictionStrip, { props: defaultProps });

        await fireEvent.keyDown(window, { key: 'Escape' });

        expect(mocks.hide).toHaveBeenCalled();
    });
});
