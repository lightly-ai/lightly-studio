import userEvent from '@testing-library/user-event';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useRecentClasses } from '$lib/hooks';
import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { useCustomSourceColors } from '$lib/hooks/useCustomSourceColors';
import AnnotationCard from './AnnotationCard.svelte';
import { fakeLayer } from './AnnotationCardFrame/fakeLayer.testFixtures';

const mocks = vi.hoisted(() => ({
    changeClass: vi.fn(),
    moveTo: vi.fn(),
    remove: vi.fn(),
    close: vi.fn()
}));

vi.mock('$lib/hooks/useSettings', async () => {
    const { writable } = await import('svelte/store');
    return { useSettings: () => ({ settingsStore: writable({ key_hide_annotations: 'v' }) }) };
});

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({
        data: [
            { annotation_label_id: 'l1', annotation_label_name: 'bobcat' },
            { annotation_label_id: 'l2', annotation_label_name: 'coyote' }
        ]
    })
}));

const sources = {
    data: [
        { collection_id: 's1', name: 'predictions' },
        { collection_id: 's2', name: 'labels' }
    ]
};
vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: () => sources
}));
vi.mock('./useAnnotationCardActions.svelte', () => ({
    useAnnotationCardActions: () => ({
        sources,
        changeClass: mocks.changeClass,
        moveTo: mocks.moveTo,
        remove: mocks.remove,
        close: mocks.close
    })
}));

const annotation = {
    sample_id: 'a1',
    annotation_collection_id: 's1',
    annotation_type: 'object_detection',
    annotation_label: { annotation_label_name: 'bobcat' },
    object_detection_details: { x: 1, y: 2, width: 10, height: 20 }
} as unknown as AnnotationView;

// Resolves once the card has found its place on the fake canvas, so its keys act.
const renderCard = async (
    context: Record<string, unknown> = {},
    cardAnnotation: AnnotationView = annotation,
    colorBySource = true
) => {
    const { layer } = fakeLayer();
    const result = render(AnnotationCard, {
        props: {
            collectionId: 'col-1',
            annotation: cardAnnotation,
            refetch: vi.fn(),
            getLayer: () => layer,
            colorBySource
        },
        context: new Map<string, unknown>([['annotation-label', context]])
    });
    await waitFor(() => expect(screen.getByTestId('annotation-card')).toBeVisible());
    return result;
};

const withBox = (bbox: { x: number; y: number; width: number; height: number }) =>
    ({
        ...annotation,
        object_detection_details: bbox
    }) as unknown as AnnotationView;

describe('AnnotationCard', () => {
    beforeAll(() => {
        const { addRecentClass } = useRecentClasses();
        for (const name of ['fox', 'deer', 'coyote', 'bobcat']) addRecentClass('col-1', name);
    });

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('shows the class, the source and the recent classes without the current one', async () => {
        await renderCard();

        expect(screen.getByText('bobcat')).toBeInTheDocument();
        expect(screen.getByText('predictions')).toBeInTheDocument();
        const chips = screen.getAllByTestId('annotation-card-recent-class');
        expect(chips.map((chip) => chip.textContent?.trim())).toEqual(['coyote', 'deer', 'fox']);
    });

    it('relabels with a recent class', async () => {
        await renderCard();

        await fireEvent.click(screen.getByText('coyote'));

        expect(mocks.changeClass).toHaveBeenCalledWith('coyote');
    });

    it('deletes on Delete and Backspace', async () => {
        await renderCard();

        await fireEvent.keyDown(document.body, { key: 'Delete' });
        await fireEvent.keyDown(document.body, { key: 'Backspace' });

        expect(mocks.remove).toHaveBeenCalledTimes(2);
    });

    it('closes on Esc before other window listeners see it', async () => {
        const windowListener = vi.fn();
        window.addEventListener('keydown', windowListener);
        await renderCard();

        await fireEvent.keyDown(document.body, { key: 'Escape' });
        window.removeEventListener('keydown', windowListener);

        expect(mocks.close).toHaveBeenCalledOnce();
        expect(windowListener).not.toHaveBeenCalled();
    });

    it('closes on the close button', async () => {
        await renderCard();

        await fireEvent.click(screen.getByLabelText('Close'));

        expect(mocks.close).toHaveBeenCalledOnce();
    });

    it.each(['isDrawing', 'isMovingAnnotation'])(
        'ignores Delete and Enter while %s hides the card',
        async (flag) => {
            const context = $state<Record<string, unknown>>({});
            await renderCard(context);
            context[flag] = true;
            await waitFor(() => expect(screen.getByTestId('annotation-card')).not.toBeVisible());

            await fireEvent.keyDown(document.body, { key: 'Delete' });
            await fireEvent.keyDown(document.body, { key: 'Enter' });

            expect(mocks.remove).not.toHaveBeenCalled();
            expect(screen.queryByPlaceholderText('Pick a class')).not.toBeInTheDocument();
        }
    );

    it('names the class button with the current class', async () => {
        await renderCard();

        expect(
            screen.getByRole('button', { name: 'Change class, current bobcat' })
        ).toBeInTheDocument();
    });

    it('opens an empty class search on Enter', async () => {
        await renderCard();

        await fireEvent.keyDown(document.body, { key: 'Enter' });

        expect(await screen.findByPlaceholderText('Pick a class')).toHaveValue('');
        expect(screen.getByPlaceholderText('Pick a class')).toHaveFocus();
    });

    it('keeps the class on a double Enter', async () => {
        await renderCard({}, {
            ...annotation,
            annotation_label: { annotation_label_name: 'coyote' }
        } as AnnotationView);

        await fireEvent.keyDown(document.body, { key: 'Enter' });
        await fireEvent.keyDown(await screen.findByPlaceholderText('Pick a class'), {
            key: 'Enter'
        });

        expect(mocks.changeClass).toHaveBeenCalledWith('coyote');
    });

    it('moves to the dropped box before the saved box arrives', async () => {
        const context = $state<Record<string, unknown>>({});
        const { rerender } = await renderCard(context);
        const card = screen.getByTestId('annotation-card');
        await waitFor(() => expect(card).toHaveStyle({ left: '19px', top: '2px' }));

        context.movedAnnotation = {
            annotationId: 'a1',
            bbox: { x: 100, y: 50, width: 10, height: 10 }
        };
        await waitFor(() => expect(card).toHaveStyle({ left: '118px', top: '50px' }));

        // The refetched annotation wins again, so a later undo moves the card back.
        await rerender({ annotation: withBox({ x: 200, y: 60, width: 10, height: 10 }) });
        await waitFor(() => expect(card).toHaveStyle({ left: '218px', top: '60px' }));
    });

    it('ignores a drop of another box and a drop from before it opened', async () => {
        const context = $state<Record<string, unknown>>({
            movedAnnotation: { annotationId: 'a1', bbox: { x: 300, y: 0, width: 10, height: 10 } }
        });
        await renderCard(context);
        const card = screen.getByTestId('annotation-card');
        await waitFor(() => expect(card).toHaveStyle({ left: '19px' }));

        context.movedAnnotation = {
            annotationId: 'other',
            bbox: { x: 100, y: 50, width: 10, height: 10 }
        };

        await new Promise((resolve) => requestAnimationFrame(resolve));
        expect(card).toHaveStyle({ left: '19px' });
    });

    it('relabels from the class field search', async () => {
        await renderCard();

        await fireEvent.click(screen.getByTitle('Change class'));
        const input = await screen.findByPlaceholderText('Pick a class');
        expect(input).toHaveValue('');
        await fireEvent.input(input, { target: { value: 'coy' } });
        await fireEvent.keyDown(input, { key: 'Enter' });

        expect(mocks.changeClass).toHaveBeenCalledWith('coyote');
        expect(screen.getByTestId('annotation-card-hints')).toBeInTheDocument();
    });

    it('moves from the source list', async () => {
        mocks.moveTo.mockResolvedValue(true);
        await renderCard();

        await fireEvent.click(screen.getByTitle('Move to another annotation source'));
        const input = await screen.findByPlaceholderText('Pick a source');
        expect(screen.getByText('Move to…')).toBeInTheDocument();
        expect(input).toHaveFocus();
        await fireEvent.input(input, { target: { value: 'lab' } });
        await fireEvent.keyDown(input, { key: 'Enter' });

        expect(mocks.moveTo).toHaveBeenCalledWith('labels');
        expect(await screen.findByTestId('annotation-card-hints')).toBeInTheDocument();
    });

    it('offers no move when the annotation is in the only source', async () => {
        const allSources = sources.data;
        sources.data = [{ collection_id: 's1', name: 'predictions' }];
        try {
            await renderCard();

            const sourceButton = screen.getByTitle('No other annotation source to move to');
            expect(sourceButton).toBeDisabled();
            expect(sourceButton).toHaveTextContent('predictions');
            await userEvent.click(sourceButton);
            expect(screen.queryByPlaceholderText('Pick a source')).not.toBeInTheDocument();
        } finally {
            sources.data = allSources;
        }
    });

    it('returns to the compact view on Esc in the move list without closing', async () => {
        await renderCard();

        await fireEvent.click(screen.getByTitle('Move to another annotation source'));
        await fireEvent.keyDown(await screen.findByPlaceholderText('Pick a source'), {
            key: 'Escape'
        });

        expect(screen.getByTestId('annotation-card-hints')).toBeInTheDocument();
        expect(mocks.close).not.toHaveBeenCalled();
    });

    it('leaves letters to the shortcuts', async () => {
        await renderCard();

        await fireEvent.keyDown(document.body, { key: 'd' });
        await fireEvent.keyDown(document.body, { key: 'k' });

        expect(screen.queryByPlaceholderText('Pick a class')).not.toBeInTheDocument();
        expect(screen.getByTestId('annotation-card-hints')).toBeInTheDocument();
    });

    it.each([
        ['search', async () => fireEvent.keyDown(document.body, { key: 'Enter' })],
        [
            'move',
            async () => fireEvent.click(screen.getByTitle('Move to another annotation source'))
        ]
    ])(
        'leaves the %s view on Esc with the focus outside the input, without closing',
        async (_name, open) => {
            await renderCard();
            await open();
            const input = await screen.findByPlaceholderText(/^Pick a (class|source)$/);
            input.blur();
            expect(input).not.toHaveFocus();

            await fireEvent.keyDown(document.body, { key: 'Escape' });

            expect(screen.getByTestId('annotation-card-hints')).toBeInTheDocument();
            expect(mocks.close).not.toHaveBeenCalled();
        }
    );

    it('labels the confidence', async () => {
        await renderCard({}, { ...annotation, confidence: 0.876 } as AnnotationView);

        expect(screen.getByText('Confidence 0.88')).toBeInTheDocument();
    });

    it('colors the source dot with the custom source color', async () => {
        const { setCustomColor, deleteCustomColor } = useCustomSourceColors();
        await renderCard();

        setCustomColor('predictions', '#112233');

        await waitFor(() =>
            expect(
                screen.getByTitle('Move to another annotation source').firstElementChild
            ).toHaveStyle({
                backgroundColor: '#112233'
            })
        );
        deleteCustomColor('predictions');
    });

    it('shows the class color, not the source color, when boxes are colored by class', async () => {
        const { setCustomColor, deleteCustomColor } = useCustomLabelColors();
        setCustomColor('bobcat', '#445566');

        await renderCard({}, annotation, false);

        expect(screen.getByTestId('annotation-card-class-dot')).toHaveStyle({
            backgroundColor: '#445566'
        });
        expect(screen.queryByTestId('annotation-card-source-dot')).not.toBeInTheDocument();
        expect(screen.getByTitle('Move to another annotation source')).toHaveTextContent(
            'predictions'
        );
        deleteCustomColor('bobcat');
    });

    it('shows the source color, not the class color, when boxes are colored by source', async () => {
        await renderCard();

        expect(screen.getByTestId('annotation-card-source-dot')).toBeInTheDocument();
        expect(screen.queryByTestId('annotation-card-class-dot')).not.toBeInTheDocument();
    });

    it('shows the shortcut keys as keys, not plain text', async () => {
        await renderCard();

        const hints = within(screen.getByTestId('annotation-card-hints'));
        expect(hints.getByText('Enter').tagName).toBe('KBD');
        expect(hints.getByText('Del').tagName).toBe('KBD');
        expect(hints.getByText('Esc').tagName).toBe('KBD');
    });
});
