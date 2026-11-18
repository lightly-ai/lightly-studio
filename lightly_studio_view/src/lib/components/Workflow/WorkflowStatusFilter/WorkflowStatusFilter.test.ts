import { fireEvent, render, screen } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useWorkflowStatusFilter } from '$lib/hooks/useWorkflowStatusFilter/useWorkflowStatusFilter';
import WorkflowStatusFilter from './WorkflowStatusFilter.svelte';

const workflowProject = vi.hoisted(() => ({ projectId: null as string | null }));
const workflowCounts = vi.hoisted(() => ({
    counts: null as Record<string, number> | null,
    params: [] as { collectionId: string; projectId: string | null }[]
}));
const navigation = vi.hoisted(() => ({ goto: vi.fn(), replaceState: vi.fn(), pushState: vi.fn() }));

vi.mock('$lib/hooks/useWorkflowProject/useWorkflowProject.svelte', () => ({
    useWorkflowProject: () => ({
        get projectId() {
            return workflowProject.projectId;
        }
    })
}));
vi.mock('$lib/hooks/useWorkflowStatusCounts/useWorkflowStatusCounts.svelte', () => ({
    useWorkflowStatusCounts: (
        getParams: () => { collectionId: string; projectId: string | null }
    ) => {
        workflowCounts.params.push(getParams());
        return {
            get counts() {
                return workflowCounts.counts;
            },
            refreshIfOlderThan: vi.fn()
        };
    }
}));
vi.mock('$app/navigation', () => navigation);

const OPTIONS = [
    'Not in workflow',
    'Not started',
    'In progress',
    'In review',
    'Rework',
    'Accepted'
];

describe('WorkflowStatusFilter', () => {
    beforeEach(() => {
        workflowProject.projectId = null;
        workflowCounts.counts = null;
        workflowCounts.params = [];
        useWorkflowStatusFilter('collection-1').clearWorkflowStates();
        vi.clearAllMocks();
    });

    it('is hidden when the dataset has no workflow project', () => {
        render(WorkflowStatusFilter, { collectionId: 'collection-1' });

        expect(screen.queryByText('Workflow status')).not.toBeInTheDocument();
    });

    it('shows the six options when the dataset has a workflow project', () => {
        workflowProject.projectId = 'project-1';

        render(WorkflowStatusFilter, { collectionId: 'collection-1' });

        expect(screen.getByText('Workflow status')).toBeInTheDocument();
        expect(
            screen.getAllByTestId('workflow-status-filter-name').map((row) => row.textContent)
        ).toEqual(OPTIONS);
    });

    it('selects several options, in memory and not in the URL', async () => {
        workflowProject.projectId = 'project-1';
        render(WorkflowStatusFilter, { collectionId: 'collection-1' });

        await fireEvent.click(screen.getByRole('checkbox', { name: 'In review' }));
        await fireEvent.click(screen.getByRole('checkbox', { name: 'Not in workflow' }));

        const { selectedWorkflowStates } = useWorkflowStatusFilter('collection-1');
        expect(get(selectedWorkflowStates)).toEqual(['in_review', 'not_in_workflow']);
        expect(navigation.goto).not.toHaveBeenCalled();
        expect(navigation.replaceState).not.toHaveBeenCalled();
        expect(navigation.pushState).not.toHaveBeenCalled();
    });

    it('shows the project-wide count of each option', () => {
        workflowProject.projectId = 'project-1';
        workflowCounts.counts = {
            not_in_workflow: 1200,
            not_started: 5,
            in_progress: 0,
            in_review: 3,
            rework: 1,
            accepted: 40
        };

        render(WorkflowStatusFilter, { collectionId: 'collection-1' });

        expect(workflowCounts.params[0]).toEqual({
            collectionId: 'collection-1',
            projectId: 'project-1'
        });
        expect(
            screen
                .getAllByTestId('workflow-status-filter-count')
                .map((row) => row.textContent?.trim())
        ).toEqual(['1,200', '5', '0', '3', '1', '40']);
    });

    it('shows no counts while they load', () => {
        workflowProject.projectId = 'project-1';

        render(WorkflowStatusFilter, { collectionId: 'collection-1' });

        expect(screen.queryAllByTestId('workflow-status-filter-count')).toHaveLength(0);
    });

    it('passes no project to the counts when the dataset has none', () => {
        render(WorkflowStatusFilter, { collectionId: 'collection-1' });

        expect(workflowCounts.params[0]).toEqual({ collectionId: 'collection-1', projectId: null });
    });
});
