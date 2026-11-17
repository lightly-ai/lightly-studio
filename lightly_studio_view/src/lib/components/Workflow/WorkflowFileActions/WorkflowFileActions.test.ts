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
        props: { file: workflowFile, transitioning: false, onTransition, ...props }
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

    it('lets the labeler resubmit a file in rework', async () => {
        const { onTransition } = renderActions({ file: { ...workflowFile, state: 'rework' } });

        await fireEvent.click(screen.getByRole('button', { name: 'Submit for review' }));

        expect(onTransition).toHaveBeenCalledWith('in_review');
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
    });

    it('lets the reviewer send a file back to rework in one click', async () => {
        const { onTransition } = renderActions({ file: reviewerFile });

        const sendBack = screen.getByRole('button', { name: 'Send back to Rework' });
        expect(sendBack).toBeEnabled();
        await fireEvent.click(sendBack);

        expect(onTransition).toHaveBeenCalledWith('rework');
    });

    it('shows a loading state on send-back while waiting for the service', async () => {
        const onTransition = vi.fn(() => new Promise<void>(() => {}));
        const { rerender } = render(WorkflowFileActions, {
            props: { file: reviewerFile, transitioning: false, onTransition }
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Send back to Rework' }));
        await rerender({ file: reviewerFile, transitioning: true, onTransition });

        expect(screen.getByRole('button', { name: 'Sending back…' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Accept' })).toBeDisabled();
    });

    it('offers nothing once the file is accepted', () => {
        renderActions({ file: { ...reviewerFile, state: 'accepted', can_edit: false } });

        expect(screen.queryByTestId('workflow-file-actions')).not.toBeInTheDocument();
    });
});
