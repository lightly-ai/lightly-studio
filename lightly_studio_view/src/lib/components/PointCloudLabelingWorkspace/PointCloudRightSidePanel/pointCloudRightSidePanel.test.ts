import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import * as hooks from '$lib/hooks';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
import {
    createCuboidAnnotation,
    type CuboidAnnotation
} from '$lib/components/PointCloudLabelingWorkspace/domain';
import PointCloudRightSidePanel from './PointCloudRightSidePanel.svelte';

vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: vi.fn(() => ({ user: undefined }))
}));

vi.spyOn(hooks, 'useGlobalStorage').mockReturnValue({
    collections: writable({})
} as unknown as ReturnType<typeof hooks.useGlobalStorage>);

vi.spyOn(hooks, 'useTags').mockReturnValue({
    tags: writable([]),
    loadTags: vi.fn()
} as unknown as ReturnType<typeof hooks.useTags>);

vi.spyOn(hooks, 'useAddTagToSample').mockReturnValue({
    busy: writable(false),
    addExisting: vi.fn(),
    createAndAdd: vi.fn()
} as ReturnType<typeof hooks.useAddTagToSample>);

vi.spyOn(hooks, 'useRemoveTagFromSample').mockReturnValue({
    removeTagFromSample: vi.fn()
} as ReturnType<typeof hooks.useRemoveTagFromSample>);

const defaultProps = {
    cuboids: [],
    annotationClasses: [{ id: 'vehicle', name: 'Vehicle', color: '#3b82f6' }],
    annotationSources: [{ id: 'ground-truth', name: 'Ground Truth' }],
    selectedCuboidId: null
};

describe('PointCloudRightSidePanel', () => {
    it('shows the empty message when there are no cuboids', () => {
        render(PointCloudRightSidePanel, { props: defaultProps });

        expect(screen.getByText('No annotations')).toBeInTheDocument();
    });

    it('renders a row for each cuboid', () => {
        const cuboid = createAnnotationFixture();
        render(PointCloudRightSidePanel, { props: { ...defaultProps, cuboids: [cuboid] } });

        expect(screen.getAllByTestId('point-cloud-annotation-list-row')).toHaveLength(1);
    });

    it('hides the tags segments until the sequence and the tick load', () => {
        render(PointCloudRightSidePanel, { props: defaultProps });

        expect(screen.queryByText('Sequence tags')).not.toBeInTheDocument();
        expect(screen.queryByText('Frame tags')).not.toBeInTheDocument();
    });

    it('shows the tags of the sequence above the tags of the tick', () => {
        render(PointCloudRightSidePanel, {
            props: {
                ...defaultProps,
                sequence: {
                    sampleId: 'sequence-1',
                    collectionId: 'sequence-collection',
                    tags: [{ tag_id: 'tag-2', name: 'night_drive' }]
                },
                tick: {
                    sampleId: 'tick-1',
                    collectionId: 'group-collection',
                    tags: [{ tag_id: 'tag-1', name: 'lidar_dropout' }]
                }
            }
        });

        expect(screen.getAllByTestId('segment-tag-name').map((tag) => tag.textContent)).toEqual([
            'night_drive',
            'lidar_dropout'
        ]);
        const sequenceTagsTitle = screen.getByText('Sequence tags');
        const frameTagsTitle = screen.getByText('Frame tags');
        expect(
            sequenceTagsTitle.compareDocumentPosition(frameTagsTitle) &
                Node.DOCUMENT_POSITION_FOLLOWING
        ).toBeTruthy();
    });

    it('shows the tags of the tick above the annotations', () => {
        render(PointCloudRightSidePanel, {
            props: {
                ...defaultProps,
                tick: {
                    sampleId: 'tick-1',
                    collectionId: 'group-collection',
                    tags: [{ tag_id: 'tag-1', name: 'lidar_dropout' }]
                }
            }
        });

        expect(screen.getByTestId('segment-tag-name')).toHaveTextContent('lidar_dropout');
        const tagsTitle = screen.getByText('Frame tags');
        const annotationsTitle = screen.getByText('Annotations');
        expect(
            tagsTitle.compareDocumentPosition(annotationsTitle) & Node.DOCUMENT_POSITION_FOLLOWING
        ).toBeTruthy();
    });

    it('keeps stale tags visible but blocks editing them', () => {
        render(PointCloudRightSidePanel, {
            props: {
                ...defaultProps,
                tick: {
                    sampleId: 'tick-1',
                    collectionId: 'group-collection',
                    tags: [{ tag_id: 'tag-1', name: 'lidar_dropout' }],
                    isStale: true
                }
            }
        });

        expect(screen.getByTestId('segment-tag-name')).toHaveTextContent('lidar_dropout');
        expect(screen.getByTestId('point-cloud-tick-tags').inert).toBe(true);
    });

    describe('annotation visibility', () => {
        const cuboid = createAnnotationFixture();
        const predictedCuboid = createCuboidAnnotation({
            ...cuboid,
            id: 'annotation-1',
            annotationSourceId: 'predictions'
        });
        const twoSourceProps = {
            ...defaultProps,
            cuboids: [cuboid, predictedCuboid],
            annotationSources: [
                { id: 'ground-truth', name: 'Ground Truth' },
                { id: 'predictions', name: 'Predictions' }
            ]
        };

        it('calls onToggleTrackVisibility with the cuboid when its eye is clicked', async () => {
            const onToggleTrackVisibility = vi.fn();
            render(PointCloudRightSidePanel, {
                props: { ...defaultProps, cuboids: [cuboid], onToggleTrackVisibility }
            });

            await fireEvent.click(screen.getByRole('button', { name: 'Hide annotation' }));

            expect(onToggleTrackVisibility).toHaveBeenCalledWith(cuboid);
        });

        it('shows "Show annotation" for a hidden cuboid', () => {
            render(PointCloudRightSidePanel, {
                props: {
                    ...defaultProps,
                    cuboids: [cuboid],
                    isCuboidHidden: () => true,
                    onToggleTrackVisibility: vi.fn()
                }
            });

            expect(screen.getByRole('button', { name: 'Show annotation' })).toBeInTheDocument();
        });

        it('toggles a source from its group header', async () => {
            const onToggleSourceVisibility = vi.fn();
            render(PointCloudRightSidePanel, {
                props: { ...twoSourceProps, onToggleSourceVisibility }
            });

            await fireEvent.click(screen.getAllByRole('button', { name: 'Hide source' })[0]);

            expect(onToggleSourceVisibility).toHaveBeenCalledWith('ground-truth');
        });

        it('shows the source toggle when only one source is on the tick', async () => {
            const onToggleSourceVisibility = vi.fn();
            render(PointCloudRightSidePanel, {
                props: { ...defaultProps, cuboids: [cuboid], onToggleSourceVisibility }
            });

            await fireEvent.click(screen.getByRole('button', { name: 'Hide source' }));

            expect(onToggleSourceVisibility).toHaveBeenCalledWith('ground-truth');
        });

        it('keeps the source toggle of a hidden source when it is the only source on the tick', () => {
            render(PointCloudRightSidePanel, {
                props: {
                    ...defaultProps,
                    cuboids: [cuboid],
                    isSourceHidden: () => true,
                    isCuboidHidden: () => true,
                    onToggleTrackVisibility: vi.fn(),
                    onToggleSourceVisibility: vi.fn()
                }
            });

            expect(screen.getByRole('button', { name: 'Show source' })).toBeEnabled();
        });

        it('disables the row toggles of a hidden source', () => {
            render(PointCloudRightSidePanel, {
                props: {
                    ...twoSourceProps,
                    isSourceHidden: (sourceId: string) => sourceId === 'ground-truth',
                    isCuboidHidden: (c: CuboidAnnotation) =>
                        c.annotationSourceId === 'ground-truth',
                    onToggleTrackVisibility: vi.fn(),
                    onToggleSourceVisibility: vi.fn()
                }
            });

            expect(screen.getByRole('button', { name: 'Show source' })).toBeInTheDocument();
            expect(screen.getByRole('button', { name: 'Show annotation' })).toBeDisabled();
            expect(screen.getByRole('button', { name: 'Hide annotation' })).toBeEnabled();
        });
    });
});

describe('PointCloudRightSidePanel source picker', () => {
    const sources = [
        { id: 'labels', name: 'labels' },
        { id: 'preds', name: 'preds' }
    ];
    const cuboid = { ...createAnnotationFixture(), id: 'c-1', annotationSourceId: 'preds' };
    const pickProps = {
        ...defaultProps,
        cuboids: [cuboid],
        annotationSources: sources,
        targetSourceName: 'labels',
        needsPick: false,
        pendingSourceName: null
    };

    it('shows one radio per source and checks the target', () => {
        render(PointCloudRightSidePanel, { props: { ...pickProps, onPickSource: vi.fn() } });

        expect(screen.getByTestId('annotation-target-radio-labels')).toHaveAttribute(
            'aria-checked',
            'true'
        );
        expect(screen.getByTestId('annotation-target-radio-preds')).toHaveAttribute(
            'aria-checked',
            'false'
        );
    });

    it('picks the clicked source', async () => {
        const onPickSource = vi.fn();
        render(PointCloudRightSidePanel, { props: { ...pickProps, onPickSource } });

        await fireEvent.click(screen.getByTestId('annotation-target-radio-preds'));

        expect(onPickSource).toHaveBeenCalledWith('preds');
    });

    it('asks for a pick while no source is picked', () => {
        render(PointCloudRightSidePanel, {
            props: { ...pickProps, targetSourceName: null, needsPick: true, onPickSource: vi.fn() }
        });

        expect(screen.getByText('Pick where new annotations go.')).toBeInTheDocument();
    });

    it('lists a source without cuboids on this tick', () => {
        render(PointCloudRightSidePanel, { props: { ...pickProps, onPickSource: vi.fn() } });

        expect(screen.getByText('No cuboids on this tick')).toBeInTheDocument();
    });

    it('picks a typed new source as new and a typed existing source as existing', async () => {
        const onPickSource = vi.fn();
        render(PointCloudRightSidePanel, { props: { ...pickProps, onPickSource } });

        await fireEvent.click(screen.getByTestId('new-annotation-source-button'));
        const input = screen.getByTestId('new-annotation-source-input');
        await fireEvent.input(input, { target: { value: 'review' } });
        await fireEvent.submit(input.closest('form')!);
        expect(onPickSource).toHaveBeenLastCalledWith('review', { isNew: true });

        await fireEvent.click(screen.getByTestId('new-annotation-source-button'));
        const again = screen.getByTestId('new-annotation-source-input');
        await fireEvent.input(again, { target: { value: 'preds' } });
        await fireEvent.submit(again.closest('form')!);
        expect(onPickSource).toHaveBeenLastCalledWith('preds');
    });

    it('shows a typed source that is not created yet as the target', () => {
        render(PointCloudRightSidePanel, {
            props: {
                ...pickProps,
                targetSourceName: 'review',
                pendingSourceName: 'review',
                onPickSource: vi.fn()
            }
        });

        expect(screen.getByTestId('annotation-target-radio-review')).toHaveAttribute(
            'aria-checked',
            'true'
        );
    });

    it('has no radios and no new source button without onPickSource', () => {
        render(PointCloudRightSidePanel, { props: pickProps });

        expect(screen.queryByTestId('annotation-target-radio-labels')).not.toBeInTheDocument();
        expect(screen.queryByTestId('new-annotation-source-button')).not.toBeInTheDocument();
    });
});
