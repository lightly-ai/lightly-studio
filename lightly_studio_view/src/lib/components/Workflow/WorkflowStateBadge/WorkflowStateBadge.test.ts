import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import WorkflowStateBadge from './WorkflowStateBadge.svelte';
import { WORKFLOW_STATES } from '../workflowFileTexts';

describe('WorkflowStateBadge', () => {
    it.each(Object.entries(WORKFLOW_STATES))(
        'shows the %s label and colour',
        (state, { label, color }) => {
            render(WorkflowStateBadge, { props: { state } });

            const badge = screen.getByTestId('workflow-grid-state-badge');
            expect(badge).toHaveTextContent(label);
            expect(badge).toHaveAttribute('data-state', state);
            expect(screen.getByTestId('workflow-grid-state-dot')).toHaveStyle({
                backgroundColor: color
            });
        }
    );

    it('stays on one line and leaves room for the selection box on narrow cards', () => {
        render(WorkflowStateBadge, { props: { state: 'not_started' } });

        const badge = screen.getByTestId('workflow-grid-state-badge');
        expect(badge).toHaveClass('whitespace-nowrap');
        expect(badge).toHaveClass('max-w-[calc(100%-2.5rem)]');
        expect(badge).toHaveAttribute('title', WORKFLOW_STATES.not_started.label);
        expect(screen.getByTestId('workflow-grid-state-label')).toHaveClass('truncate');
    });

    it('shows only the dot when compact, keeping the label as tooltip and accessible name', () => {
        render(WorkflowStateBadge, { props: { state: 'in_review', compact: true } });

        const badge = screen.getByTestId('workflow-grid-state-badge');
        expect(screen.queryByTestId('workflow-grid-state-label')).not.toBeInTheDocument();
        expect(screen.getByTestId('workflow-grid-state-dot')).toBeInTheDocument();
        expect(badge).toHaveAttribute('title', WORKFLOW_STATES.in_review.label);
        expect(badge).toHaveAttribute('aria-label', WORKFLOW_STATES.in_review.label);
    });

    it('shows nothing for a value that is not a batch file state', () => {
        render(WorkflowStateBadge, { props: { state: 'not_in_workflow' } });

        expect(screen.queryByTestId('workflow-grid-state-badge')).not.toBeInTheDocument();
    });
});
