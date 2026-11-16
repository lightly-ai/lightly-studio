import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import WorkflowInstructions from './WorkflowInstructions.svelte';
import { workflowFile } from '../workflowFile.fixture';

describe('WorkflowInstructions', () => {
    it('shows the batch instructions and who edited them last, and collapses', async () => {
        render(WorkflowInstructions, { props: { file: workflowFile } });

        expect(screen.getByText('Box every car.')).toBeInTheDocument();
        expect(screen.getByText(/Last edited by marta@example.com/)).toBeInTheDocument();

        await fireEvent.click(screen.getByRole('button', { name: /Instructions/ }));

        expect(screen.queryByText('Box every car.')).not.toBeInTheDocument();
    });

    it('says when the batch has no instructions', () => {
        render(WorkflowInstructions, {
            props: {
                file: {
                    ...workflowFile,
                    instructions: '',
                    instructions_updated_by: null,
                    instructions_updated_at: null
                }
            }
        });

        expect(screen.getByText('No instructions for this batch.')).toBeInTheDocument();
        expect(screen.queryByText(/Last edited/)).not.toBeInTheDocument();
    });
});
