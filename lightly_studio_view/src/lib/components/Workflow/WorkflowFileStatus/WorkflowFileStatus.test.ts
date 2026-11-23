import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import WorkflowFileStatus from './WorkflowFileStatus.svelte';
import { workflowFile } from '../workflowFile.fixture';

describe('WorkflowFileStatus', () => {
    it('shows the state badge, an unsubmitted round and the user’s turn', () => {
        render(WorkflowFileStatus, { props: { file: workflowFile } });

        expect(screen.getByTestId('workflow-state-badge')).toHaveTextContent('In progress');
        expect(screen.getByTestId('workflow-round')).toHaveTextContent('---');
        expect(screen.getByTestId('workflow-turn')).toHaveTextContent('Your turn');
        expect(screen.getByTestId('workflow-turn')).toHaveStyle({ color: '#3bd99f' });
    });

    it('shows the round and who the file is waiting for', () => {
        render(WorkflowFileStatus, {
            props: {
                file: {
                    ...workflowFile,
                    state: 'rework',
                    round: 2,
                    your_turn: false
                }
            }
        });

        expect(screen.getByTestId('workflow-state-badge')).toHaveTextContent('Rework');
        expect(screen.getByTestId('workflow-round')).toHaveTextContent('Round 2');
        expect(screen.getByTestId('workflow-turn')).toHaveTextContent(
            'Waiting for pedro@example.com'
        );
        expect(screen.getByTestId('workflow-turn')).toHaveStyle({ color: '#9f9fa6' });
    });
});
