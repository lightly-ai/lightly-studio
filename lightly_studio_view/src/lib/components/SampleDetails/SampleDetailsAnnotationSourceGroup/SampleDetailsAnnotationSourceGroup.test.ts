import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { createRawSnippet } from 'svelte';
import { describe, expect, it } from 'vitest';
import SampleDetailsAnnotationSourceGroup from './SampleDetailsAnnotationSourceGroup.svelte';

const children = createRawSnippet(() => ({
    render: () => '<div data-testid="group-content">content</div>'
}));

const defaultProps = {
    name: 'Ground truth',
    count: 3,
    showColorMarker: true,
    children
};

describe('SampleDetailsAnnotationSourceGroup', () => {
    it('renders the source name, annotation count and children', () => {
        render(SampleDetailsAnnotationSourceGroup, { props: defaultProps });

        expect(screen.getByText('Ground truth')).toBeInTheDocument();
        expect(screen.getByText('3')).toBeInTheDocument();
        expect(screen.getByTestId('group-content')).toBeInTheDocument();
    });

    it('collapses and expands the children when clicking the header', async () => {
        const user = userEvent.setup();
        render(SampleDetailsAnnotationSourceGroup, { props: defaultProps });

        await user.click(screen.getByText('Ground truth'));
        expect(screen.queryByTestId('group-content')).not.toBeInTheDocument();

        await user.click(screen.getByText('Ground truth'));
        expect(screen.getByTestId('group-content')).toBeInTheDocument();
    });

    it('hides the color marker when showColorMarker is false', () => {
        render(SampleDetailsAnnotationSourceGroup, {
            props: { ...defaultProps, showColorMarker: false }
        });

        const header = screen.getByTestId('annotation-source-group-header');
        expect(header.querySelector('span[style*="background-color"]')).not.toBeInTheDocument();
    });
});
