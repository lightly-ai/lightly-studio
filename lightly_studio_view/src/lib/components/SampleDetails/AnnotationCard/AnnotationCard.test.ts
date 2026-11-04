import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useRecentClasses } from '$lib/hooks';
import AnnotationCard from './AnnotationCard.svelte';

const mocks = vi.hoisted(() => ({ changeClass: vi.fn(), remove: vi.fn(), close: vi.fn() }));

vi.mock('$lib/hooks/useSettings', async () => {
    const { writable } = await import('svelte/store');
    return { useSettings: () => ({ settingsStore: writable({ key_hide_annotations: 'v' }) }) };
});

vi.mock('./useAnnotationCardActions.svelte', async () => {
    const { readable } = await import('svelte/store');
    return {
        useAnnotationCardActions: () => ({
            labels: { data: [{ annotation_label_id: 'l1', annotation_label_name: 'bobcat' }] },
            sources: { data: [{ collection_id: 's1', name: 'predictions' }] },
            isMoving: readable(false),
            changeClass: mocks.changeClass,
            moveTo: vi.fn(),
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

const renderCard = () =>
    render(AnnotationCard, {
        props: { collectionId: 'col-1', annotation, refetch: vi.fn(), getLayer: () => null },
        context: new Map<string, unknown>([['annotation-label', { isDrawing: false }]])
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

    it('keeps the compact view on a shortcut key', async () => {
        renderCard();

        await fireEvent.keyDown(document.body, { key: 'v' });

        expect(screen.queryByRole('textbox', { hidden: true })).not.toBeInTheDocument();
        expect(screen.getByText('Type to relabel · Del delete · Esc close')).toBeInTheDocument();
    });
});
