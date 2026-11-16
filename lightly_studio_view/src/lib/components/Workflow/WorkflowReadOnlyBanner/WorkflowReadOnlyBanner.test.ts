import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import WorkflowReadOnlyBanner from './WorkflowReadOnlyBanner.svelte';
import { workflowFile } from '../workflowFile.fixture';

describe('WorkflowReadOnlyBanner', () => {
    it('explains why the file is read-only', () => {
        render(WorkflowReadOnlyBanner, {
            props: { file: { ...workflowFile, state: 'in_review', can_edit: false } }
        });

        expect(screen.getByRole('status')).toHaveTextContent(
            'You submitted this file. It’s read-only while marta@example.com reviews it.'
        );
    });

    it('is hidden when it is the user’s turn', () => {
        render(WorkflowReadOnlyBanner, { props: { file: workflowFile } });

        expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });
});
