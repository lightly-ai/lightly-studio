import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useRecentClasses } from '$lib/hooks';
import AnnotationCard from './AnnotationCard.svelte';

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

vi.mock('./useAnnotationCardActions.svelte', async () => {
    const { readable } = await import('svelte/store');
    return {
        useAnnotationCardActions: () => ({
            labels: {
                data: [
                    { annotation_label_id: 'l1', annotation_label_name: 'bobcat' },
                    { annotation_label_id: 'l2', annotation_label_name: 'coyote' }
                ]
            },
            sources: {
                data: [
                    { collection_id: 's1', name: 'predictions' },
                    { collection_id: 's2', name: 'labels' }
                ]
            },
            isMoving: readable(false),
            changeClass: mocks.changeClass,
            moveTo: mocks.moveTo,
            remove: mocks.remove,
            close: mocks.close
        })
    };
});

const annotation = {
    sample_id: 'a1',
    annotation_collection_id: 's1',
    annotation_type: 'object_detection',
    annotation_label: { annotation_label_name: 'bobcat' },
    object_detection_details: { x: 1, y: 2, width: 10, height: 20 }
} as unknown as AnnotationView;

const renderCard = (isDrawing = false) =>
    render(AnnotationCard, {
        props: { collectionId: 'col-1', annotation, refetch: vi.fn(), getLayer: () => null },
        context: new Map<string, unknown>([['annotation-label', { isDrawing }]])
    });

describe('AnnotationCard', () => {
    beforeAll(() => {
        const { addRecentClass } = useRecentClasses();
        for (const name of ['fox', 'deer', 'coyote', 'bobcat']) addRecentClass('col-1', name);
    });

    beforeEach(() => {
        vi.clearAllMocks();
    });

    // jsdom has no layout, so the card never finds its place and stays hidden. Hidden elements
    // have no accessible name, so query them by label, text or test id.
    it('shows the class, the source and the recent classes without the current one', () => {
        renderCard();

        expect(screen.getByText('bobcat')).toBeInTheDocument();
        expect(screen.getByText('predictions')).toBeInTheDocument();
        const chips = screen.getAllByTestId('annotation-card-recent-class');
        expect(chips.map((chip) => chip.textContent?.trim())).toEqual(['coyote', 'deer', 'fox']);
    });

    it('relabels with a recent class', async () => {
        renderCard();

        await fireEvent.click(screen.getByText('coyote'));

        expect(mocks.changeClass).toHaveBeenCalledWith('coyote');
    });

    it('deletes on Delete and Backspace', async () => {
        renderCard();

        await fireEvent.keyDown(document.body, { key: 'Delete' });
        await fireEvent.keyDown(document.body, { key: 'Backspace' });

        expect(mocks.remove).toHaveBeenCalledTimes(2);
    });

    it('closes on Esc before other window listeners see it', async () => {
        const windowListener = vi.fn();
        window.addEventListener('keydown', windowListener);
        renderCard();

        await fireEvent.keyDown(document.body, { key: 'Escape' });
        window.removeEventListener('keydown', windowListener);

        expect(mocks.close).toHaveBeenCalledOnce();
        expect(windowListener).not.toHaveBeenCalled();
    });

    it('closes on the close button', async () => {
        renderCard();

        await fireEvent.click(screen.getByLabelText('Close'));

        expect(mocks.close).toHaveBeenCalledOnce();
    });

    it('ignores Delete while a stroke is drawn', async () => {
        renderCard(true);

        await fireEvent.keyDown(document.body, { key: 'Delete' });

        expect(mocks.remove).not.toHaveBeenCalled();
    });

    it('opens the class search with the typed key', async () => {
        renderCard();

        await fireEvent.keyDown(document.body, { key: 'k' });

        expect(await screen.findByPlaceholderText('Pick a class')).toHaveValue('k');
        expect(screen.getByPlaceholderText('Pick a class')).toHaveFocus();
    });

    it('relabels from the class field search', async () => {
        renderCard();

        await fireEvent.click(screen.getByTitle('Change class'));
        const input = await screen.findByPlaceholderText('Pick a class');
        expect(input).toHaveValue('');
        await fireEvent.input(input, { target: { value: 'coy' } });
        await fireEvent.keyDown(input, { key: 'Enter' });

        expect(mocks.changeClass).toHaveBeenCalledWith('coyote');
        expect(screen.getByText('Type to relabel · Del delete · Esc close')).toBeInTheDocument();
    });

    it('moves from the source list', async () => {
        mocks.moveTo.mockResolvedValue(true);
        renderCard();

        await fireEvent.click(screen.getByTitle('Move to another annotation source'));
        const input = await screen.findByPlaceholderText('Pick a source');
        expect(screen.getByText('Move to…')).toBeInTheDocument();
        expect(input).toHaveFocus();
        await fireEvent.input(input, { target: { value: 'lab' } });
        await fireEvent.keyDown(input, { key: 'Enter' });

        expect(mocks.moveTo).toHaveBeenCalledWith('labels');
        expect(
            await screen.findByText('Type to relabel · Del delete · Esc close')
        ).toBeInTheDocument();
    });

    it('returns to the compact view on Esc in the move list without closing', async () => {
        renderCard();

        await fireEvent.click(screen.getByTitle('Move to another annotation source'));
        await fireEvent.keyDown(await screen.findByPlaceholderText('Pick a source'), {
            key: 'Escape'
        });

        expect(screen.getByText('Type to relabel · Del delete · Esc close')).toBeInTheDocument();
        expect(mocks.close).not.toHaveBeenCalled();
    });

    it('keeps the compact view on a shortcut key', async () => {
        renderCard();

        await fireEvent.keyDown(document.body, { key: 'v' });

        expect(screen.queryByPlaceholderText('Pick a class')).not.toBeInTheDocument();
        expect(screen.getByText('Type to relabel · Del delete · Esc close')).toBeInTheDocument();
    });

    it.each([
        ['search', async () => fireEvent.keyDown(document.body, { key: 'k' })],
        [
            'move',
            async () => fireEvent.click(screen.getByTitle('Move to another annotation source'))
        ]
    ])(
        'leaves the %s view on Esc with the focus outside the input, without closing',
        async (_name, open) => {
            renderCard();
            await open();
            const input = await screen.findByPlaceholderText(/^Pick a (class|source)$/);
            input.blur();
            expect(input).not.toHaveFocus();

            await fireEvent.keyDown(document.body, { key: 'Escape' });

            expect(
                screen.getByText('Type to relabel · Del delete · Esc close')
            ).toBeInTheDocument();
            expect(mocks.close).not.toHaveBeenCalled();
        }
    );

    it('labels the confidence', () => {
        render(AnnotationCard, {
            props: {
                collectionId: 'col-1',
                annotation: { ...annotation, confidence: 0.876 } as AnnotationView,
                refetch: vi.fn(),
                getLayer: () => null
            },
            context: new Map<string, unknown>([['annotation-label', {}]])
        });

        expect(screen.getByText('Confidence 0.88')).toBeInTheDocument();
    });
});
