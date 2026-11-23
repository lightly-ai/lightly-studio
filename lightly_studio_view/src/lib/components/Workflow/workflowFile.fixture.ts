import type { WorkflowFile } from '$lib/hooks';

/** A realistic batch file context for component tests. */
export const workflowFile: WorkflowFile = {
    project_id: 'project-1',
    project_name: 'Roads',
    batch_id: 'batch-1',
    batch_name: 'Batch 1',
    sample_id: 'sample-3',
    state: 'in_progress',
    round: 1,
    labeler: 'pedro@example.com',
    reviewer: 'marta@example.com',
    your_role: 'labeler',
    can_edit: true,
    your_turn: true,
    allowed_transitions: ['in_review'],
    waiting_for: 'pedro@example.com',
    position: 3,
    total: 150,
    previous_sample_id: 'sample-2',
    next_sample_id: 'sample-4',
    instructions: 'Box every car.',
    instructions_updated_by: 'marta@example.com',
    instructions_updated_at: '2026-11-10T09:30:00Z'
};
