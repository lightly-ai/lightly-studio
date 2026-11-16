import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import WorkflowBreadcrumb from './WorkflowBreadcrumb.svelte';
import { workflowFile } from '../workflowFile.fixture';

describe('WorkflowBreadcrumb', () => {
    it('links home, the project and the batch, and shows the sample position', () => {
        render(WorkflowBreadcrumb, { props: { file: workflowFile } });

        expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute(
            'href',
            '/workspace/projects'
        );
        expect(screen.getByRole('link', { name: 'Roads' })).toHaveAttribute(
            'href',
            '/workspace/projects/project-1'
        );
        expect(screen.getByRole('link', { name: 'Batch 1' })).toHaveAttribute(
            'href',
            '/workspace/projects/project-1/batches/batch-1'
        );
        expect(screen.getByText('Sample 3 of 150')).toBeInTheDocument();
    });
});
