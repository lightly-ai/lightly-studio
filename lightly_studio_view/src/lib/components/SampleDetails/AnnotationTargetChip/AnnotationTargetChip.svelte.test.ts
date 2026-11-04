import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useCustomLabelColors } from '$lib/hooks/useCustomLabelColors';
import { getColorByLabel } from '$lib/utils';
import AnnotationTargetChip from './AnnotationTargetChip.svelte';

const mocks = vi.hoisted(() => ({
    pickClass: vi.fn(),
    setTargetSource: vi.fn(),
    sticky: {} as Record<string, string>,
    sources: [] as { collection_id: string; name: string }[]
}));

vi.mock('$lib/hooks/useSettings', async () => {
    const { writable } = await import('svelte/store');
    return { useSettings: () => ({ settingsStore: writable({ key_hide_annotations: 'v' }) }) };
});
vi.mock('$lib/hooks/useStickyClass/useStickyClass', async () => {
    const { readable } = await import('svelte/store');
    return {
        useStickyClass: () => ({
            stickyClasses: readable(mocks.sticky),
            pickClass: mocks.pickClass
        })
    };
});
vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: () => ({ data: mocks.sources })
}));
vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({
        data: [
            { annotation_label_id: 'l1', annotation_label_name: 'coyote' },
            { annotation_label_id: 'l2', annotation_label_name: 'deer' }
        ]
    })
}));
vi.mock('$lib/hooks/useAnnotationTarget/useSetTargetSource', () => ({
    useSetTargetSource: () => mocks.setTargetSource
}));

const twoSources = [
    { collection_id: 's1', name: 'labels' },
    { collection_id: 's2', name: 'predictions' }
];

// A reactive context, so the chip follows changes made after it is rendered.
const setup = (initial: AnnotationLabelContext = {}) => {
    const context: AnnotationLabelContext = $state({ ...initial });
    render(AnnotationTargetChip, {
        props: { collectionId: 'col-1' },
        context: new Map<string, unknown>([['annotation-label', context]])
    });
    return { context, user: userEvent.setup() };
};

describe('AnnotationTargetChip', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.sources = twoSources;
        mocks.sticky = { 'col-1': 'deer' };
    });

    it('shows the source and the sticky class', () => {
        setup({ annotationSource: 'labels' });

        expect(screen.getByText('labels')).toBeInTheDocument();
        expect(screen.getByText('deer')).toBeInTheDocument();
    });

    it('asks to pick a source and a class when none is set', () => {
        mocks.sticky = {};
        setup();

        expect(screen.getByText('Pick a source')).toBeInTheDocument();
        expect(screen.getByText('Pick a class')).toBeInTheDocument();
    });

    it('follows a source set elsewhere, like the radios', async () => {
        const { context } = setup({ annotationSource: 'labels' });

        context.annotationSource = 'predictions';

        expect(await screen.findByText('predictions')).toBeInTheDocument();
    });

    it('picks a class from the class popover', async () => {
        const { user } = setup({ annotationSource: 'labels' });

        await user.click(screen.getByTitle('Class for new annotations'));
        await user.click(await screen.findByRole('option', { name: 'coyote' }));

        expect(mocks.pickClass).toHaveBeenCalledWith('col-1', 'coyote');
    });

    it('picks a source from the source popover', async () => {
        const { user } = setup({ annotationSource: 'labels' });

        await user.click(screen.getByTitle('Annotation source'));
        await user.click(await screen.findByRole('option', { name: 'predictions' }));

        expect(mocks.setTargetSource).toHaveBeenCalledWith('predictions');
    });

    it('opens the class search with the typed key', async () => {
        const { user } = setup({ annotationSource: 'labels' });

        await user.keyboard('k');

        expect(await screen.findByPlaceholderText('Pick a class')).toHaveValue('k');
    });

    it('leaves the key to the card when an annotation is selected', async () => {
        const { user } = setup({ annotationSource: 'labels', annotationId: 'a1' });

        await user.keyboard('k');

        expect(screen.queryByPlaceholderText('Pick a class')).not.toBeInTheDocument();
    });

    it('leaves a shortcut key alone', async () => {
        const { user } = setup({ annotationSource: 'labels' });

        await user.keyboard('v');

        expect(screen.queryByPlaceholderText('Pick a class')).not.toBeInTheDocument();
    });

    it.each([
        ['source', 'Annotation source', 'Pick a source'],
        ['class', 'Class for new annotations', 'Pick a class']
    ])(
        'closes the %s popover on Esc with the focus outside the input',
        async (_n, title, placeholder) => {
            const { user } = setup({ annotationSource: 'labels' });
            await user.click(screen.getByTitle(title));
            const input = await screen.findByPlaceholderText(placeholder);
            input.blur();

            await user.keyboard('{Escape}');

            expect(screen.queryByPlaceholderText(placeholder)).not.toBeInTheDocument();
        }
    );

    it('colors the source dot like the card and the side panel', () => {
        setup({ annotationSource: 'labels' });

        expect(screen.getByTestId('annotation-target-source-dot')).toHaveStyle({
            backgroundColor: getColorByLabel('labels', 1).color
        });
    });

    it('shows a class dot in the class color', () => {
        setup({ annotationSource: 'labels' });

        expect(screen.getByTestId('annotation-target-class-dot')).toHaveStyle({
            backgroundColor: getColorByLabel('deer', 1).color
        });
    });

    it('shows no dots while the source and the class are unset', () => {
        mocks.sticky = {};
        setup();

        expect(screen.queryByTestId('annotation-target-source-dot')).not.toBeInTheDocument();
        expect(screen.queryByTestId('annotation-target-class-dot')).not.toBeInTheDocument();
    });

    it('uses the solid card surface', () => {
        setup();

        expect(screen.getByTestId('annotation-target-chip')).toHaveClass(
            'bg-popover',
            'text-popover-foreground'
        );
    });

    it('follows a custom source and class color', async () => {
        const { setCustomColor, deleteCustomColor } = useCustomLabelColors();
        setup({ annotationSource: 'labels' });

        setCustomColor('labels', '#112233');
        setCustomColor('deer', '#445566');

        await waitFor(() =>
            expect(screen.getByTestId('annotation-target-source-dot')).toHaveStyle({
                backgroundColor: '#112233'
            })
        );
        expect(screen.getByTestId('annotation-target-class-dot')).toHaveStyle({
            backgroundColor: '#445566'
        });
        deleteCustomColor('labels');
        deleteCustomColor('deer');
    });
});
