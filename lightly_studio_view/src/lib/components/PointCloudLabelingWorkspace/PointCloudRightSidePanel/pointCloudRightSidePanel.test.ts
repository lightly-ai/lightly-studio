import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import * as hooks from '$lib/hooks';
import { createAnnotationFixture } from '$lib/components/PointCloudLabelingWorkspace/domain/fixtures';
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
});
