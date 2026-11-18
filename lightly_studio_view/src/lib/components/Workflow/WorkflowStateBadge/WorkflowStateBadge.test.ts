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

    it('shows nothing for a value that is not a batch file state', () => {
        render(WorkflowStateBadge, { props: { state: 'not_in_workflow' } });

        expect(screen.queryByTestId('workflow-grid-state-badge')).not.toBeInTheDocument();
    });
});
