import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import ExportAnnotationError from './ExportAnnotationError.svelte';

describe('ExportAnnotationError', () => {
    it('renders nothing when error is empty', () => {
        const { container } = render(ExportAnnotationError, { props: { error: '' } });

        expect(container.querySelector('[data-testid="alert-destructive"]')).toBeNull();
    });

    it('renders the error alert when error is provided', () => {
        const { container } = render(ExportAnnotationError, {
            props: { error: 'Export failed: something went wrong' }
        });

        expect(container.querySelector('[data-testid="alert-destructive"]')).toBeInTheDocument();
        expect(container.textContent).toContain('Export failed: something went wrong');
    });
});
