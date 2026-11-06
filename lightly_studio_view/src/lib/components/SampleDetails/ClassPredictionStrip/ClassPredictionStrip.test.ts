import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import { writable } from 'svelte/store';
import { getColorByLabel } from '$lib/utils';
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
    invalidateQueries: vi.fn(),
    enforceColoringByClass: undefined as unknown as ReturnType<typeof writable<boolean>>
}));
mocks.enforceColoringByClass = writable(false);

vi.mock('$lib/hooks/useSettings', () => ({
    useSettings: () => ({ enforceColoringByClassStore: mocks.enforceColoringByClass })
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
    annotations: [
        {
            sample_id: 'ann-1',
            annotation_collection_id: 'source-a',
            annotation_label: { annotation_label_name: 'car' }
        }
    ],
    refetch
};
const TWO_SOURCES_PROPS = {
    ...defaultProps,
    annotations: [
        ...defaultProps.annotations,
        {
            sample_id: 'ann-2',
            annotation_collection_id: 'source-b',
            annotation_label: { annotation_label_name: 'bus' }
        }
    ]
};
// The DOM normalizes colors, for example rgba(r, g, b, 1) to rgb(r, g, b).
const asDomColor = (color: string) => {
    const element = document.createElement('span');
    element.style.backgroundColor = color;
    return element.style.backgroundColor;
};
const entryText = (entry: HTMLElement) => entry.textContent?.replace(/\s+/g, ' ').trim();
const classColors = () =>
    screen
        .queryAllByTestId('class-prediction-swatch')
        .map((swatch) => swatch.style.backgroundColor);

describe('ClassPredictionStrip', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.state = { status: 'hidden' };
        mocks.selectedAnnotationId = 'ann-1';
        mocks.updateAnnotations.mockResolvedValue(undefined);
        mocks.enforceColoringByClass.set(false);
    });

    it('shows a spinner and "Predicting class…" while loading', () => {
        mocks.state = { status: 'loading', annotationId: 'ann-1' };
        render(ClassPredictionStrip, { props: defaultProps });

        expect(screen.getByText('Predicting class…')).toBeInTheDocument();
        expect(screen.getByTestId('class-prediction-spinner')).toBeInTheDocument();
    });

    it('shows the top 3 with key number and name, without scores', () => {
        mocks.state = READY_STATE;
        render(ClassPredictionStrip, { props: defaultProps });

        expect(screen.getAllByTestId('class-prediction-entry').map(entryText)).toEqual([
            '1 car',
            '2 truck',
            '3 bus'
        ]);
        expect(screen.getByTestId('class-prediction-strip')).not.toHaveTextContent('%');
    });

    it('relabels the annotation on key 2 and pushes an undo entry', async () => {
        mocks.state = READY_STATE;
        render(ClassPredictionStrip, { props: defaultProps });

        await fireEvent.keyDown(window, { key: '2' });

        expect(mocks.addAnnotationLabelChangeToUndoStack).toHaveBeenCalledWith(
            expect.objectContaining({
                annotations: defaultProps.annotations,
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

    it('hides when the predicted annotation is deleted, for example by undo', async () => {
        mocks.state = READY_STATE;
        const view = render(ClassPredictionStrip, { props: defaultProps });

        await view.rerender({ ...defaultProps, annotations: [] });

        expect(mocks.hide).toHaveBeenCalled();
    });

    it('hides when the predicted annotation is deleted while predicting', async () => {
        mocks.state = { status: 'loading', annotationId: 'ann-1' };
        const view = render(ClassPredictionStrip, { props: defaultProps });

        await view.rerender({ ...defaultProps, annotations: [] });

        expect(mocks.hide).toHaveBeenCalled();
    });

    it('stays while a new annotation is not loaded into the sample yet', () => {
        mocks.state = READY_STATE;

        render(ClassPredictionStrip, { props: { ...defaultProps, annotations: [] } });

        expect(mocks.hide).not.toHaveBeenCalled();
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

    it('shows each class in its class color when coloring by class', () => {
        mocks.state = READY_STATE;
        render(ClassPredictionStrip, { props: defaultProps });

        expect(classColors()).toEqual(
            ['car', 'truck', 'bus'].map((name) => asDomColor(getColorByLabel(name).color))
        );
    });

    it('shows no class colors when coloring by source', () => {
        mocks.state = READY_STATE;
        render(ClassPredictionStrip, { props: TWO_SOURCES_PROPS });

        expect(classColors()).toEqual([]);
    });

    it('shows class colors with several sources when class coloring is enforced', () => {
        mocks.state = READY_STATE;
        mocks.enforceColoringByClass.set(true);
        render(ClassPredictionStrip, { props: TWO_SOURCES_PROPS });

        expect(classColors()).toHaveLength(3);
    });

    it('shows that Esc skips the prediction', () => {
        mocks.state = READY_STATE;
        render(ClassPredictionStrip, { props: defaultProps });

        expect(screen.getByTestId('class-prediction-strip')).toHaveTextContent('Esc skip');
    });

    it('marks the class the annotation has now as selected', () => {
        mocks.state = READY_STATE;
        render(ClassPredictionStrip, { props: defaultProps });

        const selected = screen
            .getAllByTestId('class-prediction-entry')
            .filter((entry) => entry.getAttribute('aria-current') === 'true');
        expect(selected.map(entryText)).toEqual(['1 car']);
    });

    it('marks nothing as selected when the current class is not in the top 3', () => {
        mocks.state = READY_STATE;
        const annotations = [
            {
                ...defaultProps.annotations[0],
                annotation_label: { annotation_label_name: 'horse' }
            }
        ];
        render(ClassPredictionStrip, { props: { ...defaultProps, annotations } });

        const entries = screen.getAllByTestId('class-prediction-entry');
        expect(entries.filter((entry) => entry.getAttribute('aria-current') === 'true')).toEqual(
            []
        );
    });

    it('underlines the selected class in its class color when coloring by class', () => {
        mocks.state = READY_STATE;
        render(ClassPredictionStrip, { props: defaultProps });

        const selected = screen
            .getAllByTestId('class-prediction-entry')
            .find((entry) => entry.getAttribute('aria-current') === 'true');
        expect(selected?.style.borderBottomColor).toBe(asDomColor(getColorByLabel('car').color));
    });

    it('keeps the swatch on the selected class so entries keep their width', () => {
        mocks.state = READY_STATE;
        render(ClassPredictionStrip, { props: defaultProps });

        expect(screen.getAllByTestId('class-prediction-swatch')).toHaveLength(3);
    });
});
