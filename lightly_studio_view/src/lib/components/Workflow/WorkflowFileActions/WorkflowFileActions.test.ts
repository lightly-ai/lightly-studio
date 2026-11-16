import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { toast } from 'svelte-sonner';
import type { ComponentProps } from 'svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import WorkflowFileActions from './WorkflowFileActions.svelte';
import { workflowFile } from '../workflowFile.fixture';

vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn() } }));

const reviewerFile = {
    ...workflowFile,
    state: 'in_review' as const,
    your_role: 'reviewer' as const,
    can_edit: true
};

const renderActions = (props: Partial<ComponentProps<typeof WorkflowFileActions>> = {}) => {
    const onTransition = vi.fn().mockResolvedValue(undefined);
    render(WorkflowFileActions, {
        props: { file: workflowFile, openFlags: 0, transitioning: false, onTransition, ...props }
    });
    return { onTransition };
};

describe('WorkflowFileActions', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('lets the labeler submit a file in progress for review', async () => {
        const { onTransition } = renderActions();

        await fireEvent.click(screen.getByRole('button', { name: 'Submit for review' }));

        expect(onTransition).toHaveBeenCalledWith('in_review');
        expect(screen.queryByRole('button', { name: 'Accept' })).not.toBeInTheDocument();
    });

    it('shows a loading state and blocks other moves while waiting for the service', () => {
        renderActions({ transitioning: true });

        expect(screen.getByRole('button', { name: 'Submitting…' })).toBeDisabled();
    });

    it('tells the user when the service rejects the move', async () => {
        renderActions({
            onTransition: vi.fn().mockRejectedValue(new Error('Cannot move a file'))
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Submit for review' }));

        await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Cannot move a file'));
    });

    it('lets the labeler resubmit a file in rework and counts the flags to address', () => {
        renderActions({ file: { ...workflowFile, state: 'rework' }, openFlags: 2 });

        expect(screen.getByRole('button', { name: 'Submit for review' })).toBeEnabled();
        expect(screen.getByText('2 flags to address')).toBeInTheDocument();
    });

    it('offers no action when it is not the user’s turn', () => {
        renderActions({ file: { ...workflowFile, state: 'in_review', can_edit: false } });

        expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });

    it('lets the reviewer accept a file in review', async () => {
        const { onTransition } = renderActions({ file: reviewerFile });

        await fireEvent.click(screen.getByRole('button', { name: 'Accept' }));

        expect(onTransition).toHaveBeenCalledWith('accepted');
        expect(screen.queryByRole('button', { name: 'Submit for review' })).not.toBeInTheDocument();
        expect(screen.queryByText(/Accepting clears/)).not.toBeInTheDocument();
    });

    it('keeps send-back disabled and explains why until an object is flagged', () => {
        renderActions({ file: reviewerFile });

        const sendBack = screen.getByRole('button', { name: 'Send back to Rework (0)' });
        expect(sendBack).toBeDisabled();
        expect(sendBack).toHaveAccessibleDescription(
            'Flag at least one object to send the file back'
        );
    });

    it('lets the reviewer send a flagged file back and warns that accepting clears the flags', async () => {
        const { onTransition } = renderActions({ file: reviewerFile, openFlags: 3 });

        expect(screen.getByText('Accepting clears 3 open flags')).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'Send back to Rework (3)' }));

        expect(onTransition).toHaveBeenCalledWith('rework');
    });

    it('offers nothing once the file is accepted', () => {
        renderActions({ file: { ...reviewerFile, state: 'accepted', can_edit: false } });

        expect(screen.queryByTestId('workflow-file-actions')).not.toBeInTheDocument();
    });
});
