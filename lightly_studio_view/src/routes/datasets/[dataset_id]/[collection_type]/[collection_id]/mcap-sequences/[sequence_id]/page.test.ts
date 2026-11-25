import { beforeEach, describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { goto } from '$app/navigation';
import Page from './+page.svelte';
import { load } from './+page';
import type { PageData } from './$types';
import { workflowFile } from '$lib/components/Workflow/workflowFile.fixture';
import type { WorkflowFile } from '$lib/hooks';

let summaryData: { file_name: string; lidar_channels: []; camera_channels: [] } | undefined;
const adjacentSequences = vi.hoisted(() => ({
    data: undefined as
        | {
              previous_sample_id: string | null;
              next_sample_id: string | null;
              previous_workflow?: { project_id: string; batch_id: string; state: string } | null;
              next_workflow?: { project_id: string; batch_id: string; state: string } | null;
          }
        | undefined
}));

const SEQUENCE_URL =
    'http://localhost/datasets/dataset-1/mcap/collection-1/mcap-sequences/sequence-1';
const pageState = vi.hoisted(() => ({
    url: new URL('http://localhost/'),
    state: {} as App.PageState
}));
const workflowMocks = vi.hoisted(() => ({
    file: undefined as WorkflowFile | undefined,
    isError: false,
    params: [] as unknown[],
    mutateAsync: vi.fn()
}));

const authState = vi.hoisted(() => ({ role: undefined as 'labeler' | 'editor' | undefined }));

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: () => ({
        isAuthenticated: !!authState.role,
        user: authState.role ? { role: authState.role, email: 'a@b.c' } : undefined
    })
}));

vi.mock('@tanstack/svelte-query', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@tanstack/svelte-query')>()),
    useQueryClient: () => ({ invalidateQueries: vi.fn() })
}));

vi.mock('$lib/components/PointCloudLabelingWorkspace/useStartSequenceTrack', () => ({
    useStartSequenceTrack: () => ({ handleStartTrack: vi.fn() })
}));

vi.mock('$lib/components/PointCloudLabelingWorkspace/useExtendSequenceTrack', () => ({
    useExtendSequenceTrack: () => ({ handleExtendTrack: vi.fn() })
}));

vi.mock('$lib/components/PointCloudLabelingWorkspace/useDeleteSequenceTrack', () => ({
    useDeleteSequenceTrack: () => ({ handleDeleteTrack: vi.fn() })
}));

vi.mock(
    '$lib/components/PointCloudLabelingWorkspace/FrameTimeline/useSequenceTracks.svelte',
    () => ({
        useSequenceTracks: () => ({ query: { data: { tracks: [] } } })
    })
);

vi.mock(
    '$lib/components/PointCloudLabelingWorkspace/FrameTimeline/useSequenceTickTags.svelte',
    () => ({
        useSequenceTickTags: () => ({ query: { data: { tags: [] } } })
    })
);

vi.mock('$app/state', () => ({
    page: {
        get url() {
            return pageState.url;
        },
        params: { dataset_id: 'dataset-1' },
        get state() {
            return pageState.state;
        }
    }
}));

vi.mock('$lib/hooks/useAdjacentMcapSequences/useAdjacentMcapSequences', () => ({
    useAdjacentMcapSequences: () => ({ query: adjacentSequences, refetch: vi.fn() })
}));

vi.mock('$lib/components/PointCloudLabelingWorkspace/useUpdateCuboidClass', () => ({
    useUpdateCuboidClass: () => ({ handleLabelChange: vi.fn() })
}));

vi.mock('$lib/components/PointCloudLabelingWorkspace/useCreateCuboidAnnotation', async () => {
    const { writable } = await import('svelte/store');
    return {
        useCreateCuboidAnnotation: () => ({
            handleCreateCuboid: vi.fn(),
            showSelectClassDialog: writable(false),
            handleClassSelected: vi.fn(),
            handleClassDialogCancel: vi.fn(),
            getRememberedLabel: () => undefined,
            labels: { data: [] },
            tracks: { data: [] }
        })
    };
});

vi.mock('$lib/hooks', async () => {
    const { readonly, writable } = await import('svelte/store');
    const featureFlags = writable<string[]>([]);
    return {
        useFeatureFlags: () => ({ featureFlags: readonly(featureFlags) }),
        useGlobalStorage: () => ({
            isEditingMode: writable(false),
            lastAnnotationSource: writable({}),
            updateLastAnnotationSource: vi.fn(),
            removeLastAnnotationSource: vi.fn(),
            addReversibleAction: vi.fn()
        }),
        useAuth: () => ({ user: undefined }),
        hasMinimumRole: () => true,
        useUpdateAnnotationsMutation: () => ({ updateAnnotations: vi.fn() }),
        useDeleteAnnotationWithUndo: () => ({ deleteWithUndo: vi.fn() }),
        useCanCreateAnnotationClass: () => true,
        // The workspace context fetches the sequence summary and tick details; stub them so no live query runs.
        useMcapSequenceSummary: () => ({
            summary: { data: summaryData, isLoading: false, isError: false },
            refetch: vi.fn()
        }),
        useMcapSequenceTicks: () => ({
            ticks: {
                data: {
                    ticks: [
                        { seq_number: 0, timestamp_ns: 1000 },
                        { seq_number: 1, timestamp_ns: 2000 }
                    ]
                }
            },
            refetch: vi.fn()
        }),
        useTickDetails: () => ({ tickDetails: { data: undefined } }),
        useCloudPointFrame: () => ({
            query: { data: undefined, isLoading: false, isError: false, refetch: vi.fn() }
        }),
        useTickCameraFrames: () => ({ query: { data: undefined } }),
        // The right panel shows the sequence tags once the summary loads; stub the tag hooks.
        useTags: () => ({ tags: writable([]), loadTags: vi.fn() }),
        useAddTagToSample: () => ({
            busy: writable(false),
            addExisting: vi.fn(),
            createAndAdd: vi.fn()
        }),
        useRemoveTagFromSample: () => ({ removeTagFromSample: vi.fn() }),
        useAnnotationCollections: () => ({ data: [] }),
        useMcapTickPrefetchScheduler: () => ({
            bufferedRanges: [],
            errors: new Map(),
            cancel: vi.fn()
        }),
        // The workspace header shows the edit, plugins and settings actions.
        // The sequence opened from a batch reads its batch file.
        useWorkflowFile: (getParams: () => unknown) => {
            const params = getParams();
            workflowMocks.params.push(params);
            return {
                query: {
                    data: params ? workflowMocks.file : undefined,
                    isError: workflowMocks.isError
                }
            };
        },
        useWorkflowFileTransition: () => ({
            mutation: { mutateAsync: workflowMocks.mutateAsync, isPending: false }
        }),
        useOperatorsDialog: () => ({ openOperatorsDialog: vi.fn() }),
        useSettings: () => ({ settingsStore: writable({ key_toggle_edit_mode: 'e' }) }),
        usePostHog: () => ({ trackEvent: vi.fn() })
    };
});

const mockPageData = {
    datasetId: 'dataset-1',
    annotationSourceCollectionId: 'group-collection-1',
    collectionId: 'collection-1',
    collectionName: 'Collection 1',
    collectionType: 'mcap',
    sequenceId: 'sequence-1'
} as unknown as PageData;

describe('[collection_type]/[collection_id]/mcap-sequences/[sequence_id] page', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        summaryData = undefined;
        adjacentSequences.data = undefined;
        pageState.url = new URL(SEQUENCE_URL);
        pageState.state = {};
        workflowMocks.file = undefined;
        workflowMocks.isError = false;
        authState.role = undefined;
        workflowMocks.params = [];
        workflowMocks.mutateAsync.mockResolvedValue(undefined);
    });

    describe('opened from a batch', () => {
        beforeEach(() => {
            pageState.url = new URL(
                `${SEQUENCE_URL}?workflow_project=project-1&workflow_batch=batch-1`
            );
        });

        it('reads the sequence’s batch file and lets the labeler submit it', async () => {
            workflowMocks.file = { ...workflowFile, sample_id: 'sequence-1' };
            const user = userEvent.setup();
            render(Page, { props: { data: mockPageData } });

            const header = await screen.findByTestId('workspace-header');
            expect(workflowMocks.params).toContainEqual({
                projectId: 'project-1',
                batchId: 'batch-1',
                sampleId: 'sequence-1'
            });
            expect(within(header).getByTestId('workflow-state-badge')).toHaveTextContent(
                'In progress'
            );
            await user.click(within(header).getByRole('button', { name: 'Submit for review' }));
            expect(workflowMocks.mutateAsync).toHaveBeenCalledWith('in_review');
        });

        it('steps through the batch in batch order when opened from the batch file list', async () => {
            workflowMocks.file = {
                ...workflowFile,
                sample_id: 'sequence-1',
                previous_sample_id: 'sequence-7',
                next_sample_id: 'sequence-9'
            };
            // The grid neighbours are not used in batch order.
            adjacentSequences.data = { previous_sample_id: 'grid-0', next_sample_id: 'grid-2' };
            const user = userEvent.setup();
            render(Page, { props: { data: mockPageData } });

            await user.click(await screen.findByRole('button', { name: 'Previous sequence' }));
            await user.click(screen.getByRole('button', { name: 'Next sequence' }));

            expect(vi.mocked(goto).mock.calls).toEqual([
                [
                    '/datasets/dataset-1/mcap/collection-1/mcap-sequences/sequence-7?workflow_project=project-1&workflow_batch=batch-1'
                ],
                [
                    '/datasets/dataset-1/mcap/collection-1/mcap-sequences/sequence-9?workflow_project=project-1&workflow_batch=batch-1'
                ]
            ]);
        });

        it('disables next at the last file of the batch', async () => {
            workflowMocks.file = {
                ...workflowFile,
                sample_id: 'sequence-1',
                previous_sample_id: 'sequence-7',
                next_sample_id: null
            };
            adjacentSequences.data = { previous_sample_id: 'grid-0', next_sample_id: 'grid-2' };
            render(Page, { props: { data: mockPageData } });

            expect(await screen.findByRole('button', { name: 'Next sequence' })).toBeDisabled();
            expect(screen.getByRole('button', { name: 'Previous sequence' })).toBeEnabled();
        });

        it('disables previous at the first file of the batch', async () => {
            workflowMocks.file = {
                ...workflowFile,
                sample_id: 'sequence-1',
                previous_sample_id: null,
                next_sample_id: 'sequence-9'
            };
            adjacentSequences.data = { previous_sample_id: 'grid-0', next_sample_id: 'grid-2' };
            render(Page, { props: { data: mockPageData } });

            expect(await screen.findByRole('button', { name: 'Previous sequence' })).toBeDisabled();
            expect(screen.getByRole('button', { name: 'Next sequence' })).toBeEnabled();
        });

        it('keeps grid order when opened from the grid', async () => {
            pageState.state = { nav: 'dataset' };
            workflowMocks.file = { ...workflowFile, sample_id: 'sequence-1' };
            adjacentSequences.data = { previous_sample_id: null, next_sample_id: 'grid-2' };
            const user = userEvent.setup();
            render(Page, { props: { data: mockPageData } });

            await user.click(await screen.findByRole('button', { name: 'Next sequence' }));

            expect(goto).toHaveBeenCalledExactlyOnceWith(
                '/datasets/dataset-1/mcap/collection-1/mcap-sequences/grid-2',
                { state: { nav: 'dataset' } }
            );
        });

        it('shows a labeler the batch path instead of the dataset path in the breadcrumb', async () => {
            authState.role = 'labeler';
            workflowMocks.file = { ...workflowFile, sample_id: 'sequence-1' };
            summaryData = { file_name: 'drive_001.mcap', lidar_channels: [], camera_channels: [] };
            render(Page, { props: { data: mockPageData } });

            const breadcrumb = await screen.findByTestId('workspace-breadcrumb');
            expect(breadcrumb).toHaveTextContent('Home');
            expect(breadcrumb).toHaveTextContent('Roads');
            expect(breadcrumb).toHaveTextContent('Batch 1');
            expect(breadcrumb).toHaveTextContent('drive_001.mcap');
            expect(breadcrumb).not.toHaveTextContent('Collection 1');
            expect(breadcrumb).not.toHaveTextContent('Point clouds');

            // The current crumb is a disabled link without an href.
            const links = within(breadcrumb)
                .getAllByRole('link')
                .filter((link) => link.hasAttribute('href'));
            expect(links.map((link) => link.getAttribute('href'))).toEqual([
                '/workspace/projects',
                '/workspace/projects/project-1',
                '/workspace/projects/project-1/batches/batch-1'
            ]);
            for (const link of links) {
                expect(link).toHaveAttribute('data-sveltekit-reload');
            }
        });

        it('shows the dataset path in the breadcrumb when opened from the grid', async () => {
            pageState.state = { nav: 'dataset' };
            authState.role = 'editor';
            workflowMocks.file = { ...workflowFile, sample_id: 'sequence-1' };
            summaryData = { file_name: 'drive_001.mcap', lidar_channels: [], camera_channels: [] };
            render(Page, { props: { data: mockPageData } });

            const breadcrumb = await screen.findByTestId('workspace-breadcrumb');
            expect(breadcrumb).toHaveTextContent('Collection 1');
            expect(breadcrumb).toHaveTextContent('Point clouds');
            expect(breadcrumb).toHaveTextContent('drive_001.mcap');
            expect(breadcrumb).not.toHaveTextContent('Roads');
            expect(breadcrumb).not.toHaveTextContent('Batch 1');
        });

        it('shows no breadcrumb while the batch file loads', async () => {
            render(Page, { props: { data: mockPageData } });

            const header = await screen.findByTestId('workspace-header');
            expect(within(header).queryByTestId('workspace-breadcrumb')).not.toBeInTheDocument();
            expect(within(header).queryAllByRole('link')).toHaveLength(0);
        });

        it('shows Home to Projects and the file name when the batch file fails to load', async () => {
            workflowMocks.isError = true;
            summaryData = { file_name: 'drive_001.mcap', lidar_channels: [], camera_channels: [] };
            render(Page, { props: { data: mockPageData } });

            const breadcrumb = await screen.findByTestId('workspace-breadcrumb');
            expect(breadcrumb).toHaveTextContent(/^Home\s*drive_001\.mcap$/);
            const home = breadcrumb.querySelectorAll('a[href]');
            expect(home).toHaveLength(1);
            expect(home[0]).toHaveTextContent('Home');
            expect(home[0]).toHaveAttribute('href', '/workspace/projects');
            expect(home[0]).toHaveAttribute('data-sveltekit-reload');
        });

        it('locks editing when it is not the user’s turn', async () => {
            workflowMocks.file = {
                ...workflowFile,
                sample_id: 'sequence-1',
                state: 'in_review',
                can_edit: false
            };
            render(Page, { props: { data: mockPageData } });

            const header = await screen.findByTestId('workspace-header');
            expect(within(header).getByRole('status')).toHaveTextContent(
                'You submitted this file. It’s read-only while marta@example.com reviews it.'
            );
            expect(within(header).getByTestId('breadcrumb-edit-button')).toBeDisabled();
        });
    });

    it('shows no workflow parts and keeps editing open outside a batch', async () => {
        render(Page, { props: { data: mockPageData } });

        const header = await screen.findByTestId('workspace-header');
        expect(within(header).queryByTestId('workflow-file-status')).not.toBeInTheDocument();
        expect(within(header).queryByRole('status')).not.toBeInTheDocument();
        expect(within(header).getByTestId('breadcrumb-edit-button')).toBeEnabled();
    });

    it('renders the workspace', async () => {
        render(Page, { props: { data: mockPageData } });

        await waitFor(() =>
            expect(screen.getByTestId('point-cloud-labeling-workspace')).toBeInTheDocument()
        );
    });

    it('shows the edit, plugins and settings actions in the workspace header', async () => {
        render(Page, { props: { data: mockPageData } });

        const header = await screen.findByTestId('workspace-header');
        expect(within(header).getByTestId('breadcrumb-edit-button')).toBeVisible();
        expect(within(header).getByRole('button', { name: 'Plugins' })).toBeInTheDocument();
        expect(within(header).getByRole('button', { name: 'Settings' })).toBeInTheDocument();
    });

    it('shows the recording file name in the breadcrumb once the summary loads', async () => {
        summaryData = { file_name: 'drive_001.mcap', lidar_channels: [], camera_channels: [] };
        render(Page, { props: { data: mockPageData } });

        const breadcrumb = await screen.findByTestId('workspace-breadcrumb');
        expect(breadcrumb).toHaveTextContent('drive_001.mcap');
    });

    it('sends a labeler home to Projects outside a batch, other crumbs as plain text', async () => {
        authState.role = 'labeler';
        summaryData = { file_name: 'drive_001.mcap', lidar_channels: [], camera_channels: [] };
        render(Page, { props: { data: mockPageData } });

        const breadcrumb = await screen.findByTestId('workspace-breadcrumb');
        expect(breadcrumb).toHaveTextContent('Home');
        expect(breadcrumb).toHaveTextContent('Collection 1');
        expect(breadcrumb).toHaveTextContent('Point clouds');
        expect(breadcrumb).toHaveTextContent('drive_001.mcap');
        const home = breadcrumb.querySelectorAll('a[href]');
        expect(home).toHaveLength(1);
        expect(home[0]).toHaveTextContent('Home');
        expect(home[0]).toHaveAttribute('href', '/workspace/projects');
        expect(home[0]).toHaveAttribute('data-sveltekit-reload');
    });

    it('keeps the dataset links for an editor outside a batch', async () => {
        authState.role = 'editor';
        render(Page, { props: { data: mockPageData } });

        const breadcrumb = await screen.findByTestId('workspace-breadcrumb');
        expect(breadcrumb.querySelectorAll('a[href]')).toHaveLength(3);
    });

    it('falls back to the sequence id in the breadcrumb while the summary loads', async () => {
        render(Page, { props: { data: mockPageData } });

        const breadcrumb = await screen.findByTestId('workspace-breadcrumb');
        expect(breadcrumb).toHaveTextContent('Point cloud sequence-1');
    });

    it('reflects timeline navigation in the one-based tick hash', async () => {
        const user = userEvent.setup();
        render(Page, { props: { data: mockPageData } });

        await user.click(await screen.findByRole('button', { name: 'Next frame' }));

        expect(goto).toHaveBeenCalledOnce();
        const [url, options] = vi.mocked(goto).mock.calls[0];
        expect(url).toBeInstanceOf(URL);
        expect((url as URL).hash).toBe('#tick=2');
        expect(options).toMatchObject({ replaceState: true, noScroll: true, keepFocus: true });
    });

    it('opens the next sequence from the timeline on its first tick', async () => {
        adjacentSequences.data = { previous_sample_id: null, next_sample_id: 'sequence-2' };
        const user = userEvent.setup();
        render(Page, {
            props: { data: mockPageData }
        });

        expect(await screen.findByRole('button', { name: 'Previous sequence' })).toBeDisabled();
        await user.click(screen.getByRole('button', { name: 'Next sequence' }));

        expect(goto).toHaveBeenCalledExactlyOnceWith(
            '/datasets/dataset-1/mcap/collection-1/mcap-sequences/sequence-2',
            { state: { nav: 'dataset' } }
        );
    });

    it('opens the previous sequence from the timeline', async () => {
        adjacentSequences.data = { previous_sample_id: 'sequence-0', next_sample_id: null };
        const user = userEvent.setup();
        render(Page, { props: { data: mockPageData } });

        expect(await screen.findByRole('button', { name: 'Next sequence' })).toBeDisabled();
        await user.click(screen.getByRole('button', { name: 'Previous sequence' }));

        expect(goto).toHaveBeenCalledExactlyOnceWith(
            '/datasets/dataset-1/mcap/collection-1/mcap-sequences/sequence-0',
            { state: { nav: 'dataset' } }
        );
    });

    it('opens each batched neighbour in workflow mode with its own batch', async () => {
        adjacentSequences.data = {
            previous_sample_id: 'sequence-0',
            next_sample_id: 'sequence-2',
            previous_workflow: { project_id: 'project-1', batch_id: 'batch-1', state: 'rework' },
            next_workflow: { project_id: 'project-1', batch_id: 'batch-2', state: 'not_started' }
        };
        const user = userEvent.setup();
        render(Page, { props: { data: mockPageData } });

        await user.click(await screen.findByRole('button', { name: 'Previous sequence' }));
        await user.click(screen.getByRole('button', { name: 'Next sequence' }));

        expect(vi.mocked(goto).mock.calls).toEqual([
            [
                '/datasets/dataset-1/mcap/collection-1/mcap-sequences/sequence-0?workflow_project=project-1&workflow_batch=batch-1',
                { state: { nav: 'dataset' } }
            ],
            [
                '/datasets/dataset-1/mcap/collection-1/mcap-sequences/sequence-2?workflow_project=project-1&workflow_batch=batch-2',
                { state: { nav: 'dataset' } }
            ]
        ]);
    });
});

describe('point-cloud sequence page load', () => {
    // The route dataset slot carries a collection id; the dataset id comes from the loaded collection.
    const loadWith = (search: string, parentData: unknown): ReturnType<typeof load> =>
        load({
            params: {
                dataset_id: 'root-collection',
                collection_type: 'group',
                collection_id: 'group-collection',
                sequence_id: 'sequence'
            },
            url: new URL(
                `http://localhost/datasets/root-collection/group/group-collection/mcap-sequences/sequence${search}`
            ),
            parent: async () => parentData
        } as unknown as Parameters<typeof load>[0]);

    it('uses the MCAP group collection for sources and keeps the sequence breadcrumb', async () => {
        const result = await loadWith('?group_id=group', {
            collection: {
                dataset_id: 'dataset',
                collection_id: 'sequence-collection',
                name: 'Sequences',
                sample_type: 'sequence',
                parent_collection_id: 'root-collection'
            },
            collectionHierarchy: [
                {
                    collection_id: 'group-collection',
                    name: 'Sequences_groups',
                    sample_type: 'group'
                }
            ]
        });

        expect(result).toEqual({
            datasetId: 'dataset',
            annotationSourceCollectionId: 'group-collection',
            collectionName: 'Sequences',
            collectionType: 'sequence',
            collectionId: 'sequence-collection',
            sequenceId: 'sequence',
            groupId: 'group'
        });
    });

    it('uses the current group collection for sources and breadcrumbs its sequence parent', async () => {
        const result = await loadWith('', {
            collection: {
                dataset_id: 'dataset',
                collection_id: 'group-collection',
                name: 'Group',
                sample_type: 'group',
                parent_collection_id: 'sequence-collection'
            },
            collectionHierarchy: [
                { collection_id: 'sequence-collection', name: 'Sequences', sample_type: 'sequence' }
            ]
        });

        expect(result).toEqual({
            datasetId: 'dataset',
            annotationSourceCollectionId: 'group-collection',
            collectionName: 'Sequences',
            collectionType: 'sequence',
            collectionId: 'sequence-collection',
            sequenceId: 'sequence',
            groupId: undefined
        });
    });
});
