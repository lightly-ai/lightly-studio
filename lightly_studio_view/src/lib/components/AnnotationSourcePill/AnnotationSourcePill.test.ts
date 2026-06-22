import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { type Writable } from 'svelte/store';
import AnnotationSourcePill from './AnnotationSourcePill.svelte';

// Control the source list, the current selection, and the persistence/setter spies.
const mocks = vi.hoisted(() => ({
    annotationSource: null as string | null,
    collections: [] as { collection_id: string; name: string }[],
    setAnnotationSource: vi.fn(),
    updateLastAnnotationSource: vi.fn(),
    enforceColoringByClassStore: null as unknown as Writable<boolean>
}));

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        context: { annotationSource: mocks.annotationSource },
        setAnnotationSource: mocks.setAnnotationSource
    })
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({ updateLastAnnotationSource: mocks.updateLastAnnotationSource })
}));

vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: () => ({
        get data() {
            return mocks.collections;
        }
    })
}));

vi.mock('$lib/hooks/useSettings', async () => {
    const { writable } = await import('svelte/store');
    mocks.enforceColoringByClassStore = writable<boolean>(false);
    return {
        useSettings: vi.fn(() => ({
            enforceColoringByClassStore: mocks.enforceColoringByClassStore
        }))
    };
});

const source = (name: string) => ({ collection_id: name, name });

describe('AnnotationSourcePill', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.annotationSource = null;
        mocks.collections = [];
        mocks.enforceColoringByClassStore.set(false);
        Element.prototype.scrollIntoView = vi.fn();
    });

    const renderPill = () => render(AnnotationSourcePill, { props: { collectionId: 'col-1' } });

    const trigger = () => screen.getByTestId('annotation-source-pill-trigger');

    it('shows the explicitly chosen source', () => {
        mocks.annotationSource = 'predictions';
        mocks.collections = [source('ground_truth'), source('predictions')];
        renderPill();

        expect(trigger()).toHaveTextContent('predictions');
    });

    it('falls back to the default "annotation" collection when none is chosen', () => {
        mocks.collections = [source('ground_truth'), source('annotation')];
        renderPill();

        expect(trigger()).toHaveTextContent('annotation');
    });

    it('falls back to the first source when no default collection exists', () => {
        mocks.collections = [source('ground_truth'), source('predictions')];
        renderPill();

        expect(trigger()).toHaveTextContent('ground_truth');
    });

    it('falls back to the literal default with no sources', () => {
        renderPill();

        expect(trigger()).toHaveTextContent('annotation');
    });

    it('selects an existing source and persists the choice', async () => {
        const user = userEvent.setup();
        mocks.annotationSource = 'ground_truth';
        mocks.collections = [source('ground_truth'), source('predictions')];
        renderPill();

        await user.click(trigger());
        await user.click(await screen.findByTestId('annotation-source-pill-option-predictions'));

        expect(mocks.setAnnotationSource).toHaveBeenCalledWith('predictions');
        expect(mocks.updateLastAnnotationSource).toHaveBeenCalledWith('col-1', 'predictions');
    });

    it('creates a new source from the typed name', async () => {
        const user = userEvent.setup();
        mocks.collections = [source('ground_truth')];
        renderPill();

        await user.click(trigger());
        await user.type(screen.getByTestId('annotation-source-pill-input'), 'new_source');
        await user.click(await screen.findByTestId('annotation-source-pill-create'));

        expect(mocks.setAnnotationSource).toHaveBeenCalledWith('new_source');
        expect(mocks.updateLastAnnotationSource).toHaveBeenCalledWith('col-1', 'new_source');
    });

    it('seeds the context with the displayed source on a fresh session', () => {
        mocks.collections = [source('ground_truth'), source('predictions')];
        renderPill();

        // Without an explicit pick, the first draw must land in the shown source, not the default.
        expect(mocks.setAnnotationSource).toHaveBeenCalledWith('ground_truth');
    });

    it('does not seed when a source is already selected', () => {
        mocks.annotationSource = 'predictions';
        mocks.collections = [source('ground_truth'), source('predictions')];
        renderPill();

        expect(mocks.setAnnotationSource).not.toHaveBeenCalled();
    });

    it('does not seed before the source list has loaded', () => {
        renderPill();

        expect(mocks.setAnnotationSource).not.toHaveBeenCalled();
    });

    it('explains the target via an accessibly-named info tooltip on hover', async () => {
        const user = userEvent.setup();
        mocks.collections = [source('ground_truth')];
        renderPill();

        // The accessible name lives on the focusable trigger, not the decorative icon.
        const infoTrigger = screen.getByRole('button', { name: 'Annotation source help' });
        await user.hover(infoTrigger);

        expect(screen.getByRole('tooltip')).toHaveTextContent(
            'associated with the selected annotation source'
        );
    });

    it('shows color markers in trigger and options when enforce coloring by class is disabled', async () => {
        const user = userEvent.setup();
        mocks.annotationSource = 'ground_truth';
        mocks.collections = [source('ground_truth'), source('predictions')];
        mocks.enforceColoringByClassStore.set(false);
        renderPill();

        expect(screen.getByTestId('color-marker-ground_truth')).toBeInTheDocument();

        await user.click(trigger());
        expect(screen.getAllByTestId('color-marker-ground_truth')).toHaveLength(2);
        expect(screen.getByTestId('color-marker-predictions')).toBeInTheDocument();
    });

    it('hides color markers in trigger and options when enforce coloring by class is enabled', async () => {
        const user = userEvent.setup();
        mocks.annotationSource = 'ground_truth';
        mocks.collections = [source('ground_truth'), source('predictions')];
        mocks.enforceColoringByClassStore.set(true);
        renderPill();

        expect(screen.queryByTestId('color-marker-ground_truth')).not.toBeInTheDocument();

        await user.click(trigger());
        expect(screen.queryByTestId('color-marker-ground_truth')).not.toBeInTheDocument();
        expect(screen.queryByTestId('color-marker-predictions')).not.toBeInTheDocument();
    });
});
