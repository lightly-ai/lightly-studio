import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { createRawSnippet } from 'svelte';
import { describe, expect, it, vi } from 'vitest';
import SampleDetailsAnnotationSourceGroup from './SampleDetailsAnnotationSourceGroup.svelte';

const children = createRawSnippet(() => ({
    render: () => '<div data-testid="group-content">content</div>'
}));

const defaultProps = {
    name: 'Ground truth',
    count: 3,
    sampleId: 'sample-1',
    showColorMarker: true,
    allHidden: false,
    onToggleVisibility: vi.fn(),
    children
};

// Classifications reuse the group without a visibility toggle: omitting
// onToggleVisibility hides the eye entirely.
const propsWithoutEye = {
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

    it('shows an open eye when not all annotations are hidden', () => {
        render(SampleDetailsAnnotationSourceGroup, { props: defaultProps });

        expect(screen.getByTestId('source-group-eye')).toBeInTheDocument();
        expect(screen.queryByTestId('source-group-eye-off')).not.toBeInTheDocument();
    });

    it('shows a closed eye when all annotations are hidden', () => {
        render(SampleDetailsAnnotationSourceGroup, {
            props: { ...defaultProps, allHidden: true }
        });

        expect(screen.getByTestId('source-group-eye-off')).toBeInTheDocument();
        expect(screen.queryByTestId('source-group-eye')).not.toBeInTheDocument();
    });

    it('calls onToggleVisibility when clicking the eye without collapsing the group', async () => {
        const user = userEvent.setup();
        const onToggleVisibility = vi.fn();
        render(SampleDetailsAnnotationSourceGroup, {
            props: { ...defaultProps, onToggleVisibility }
        });

        await user.click(screen.getByTestId('source-group-eye'));

        expect(onToggleVisibility).toHaveBeenCalledOnce();
        expect(screen.getByTestId('group-content')).toBeInTheDocument();
    });

    it('hides the visibility eye when onToggleVisibility is omitted', () => {
        render(SampleDetailsAnnotationSourceGroup, { props: propsWithoutEye });

        expect(screen.queryByTestId('source-group-eye')).not.toBeInTheDocument();
        expect(screen.queryByTestId('source-group-eye-off')).not.toBeInTheDocument();
    });

    it('still renders the name, count and children without the eye', () => {
        render(SampleDetailsAnnotationSourceGroup, { props: propsWithoutEye });

        expect(screen.getByText('Ground truth')).toBeInTheDocument();
        expect(screen.getByText('3')).toBeInTheDocument();
        expect(screen.getByTestId('group-content')).toBeInTheDocument();
    });

    it('starts expanded by default', () => {
        render(SampleDetailsAnnotationSourceGroup, { props: defaultProps });

        expect(screen.getByTestId('group-content')).toBeInTheDocument();
    });

    it('starts collapsed when initiallyOpen is false', () => {
        render(SampleDetailsAnnotationSourceGroup, {
            props: { ...defaultProps, initiallyOpen: false }
        });

        expect(screen.queryByTestId('group-content')).not.toBeInTheDocument();
    });

    it('toggles visibility via the eye without expanding a collapsed group', async () => {
        const user = userEvent.setup();
        const onToggleVisibility = vi.fn();
        render(SampleDetailsAnnotationSourceGroup, {
            props: { ...defaultProps, initiallyOpen: false, allHidden: true, onToggleVisibility }
        });

        await user.click(screen.getByTestId('source-group-eye-off'));

        expect(onToggleVisibility).toHaveBeenCalledOnce();
        expect(screen.queryByTestId('group-content')).not.toBeInTheDocument();
    });

    it('re-applies the initial collapse when the sample changes', async () => {
        const user = userEvent.setup();
        const { rerender } = render(SampleDetailsAnnotationSourceGroup, {
            props: { ...defaultProps, initiallyOpen: false, sampleId: 'sample-1' }
        });

        // Manually expand the collapsed group.
        await user.click(screen.getByText('Ground truth'));
        expect(screen.getByTestId('group-content')).toBeInTheDocument();

        // Navigating to another sample re-applies the seeded collapse.
        await rerender({ ...defaultProps, initiallyOpen: false, sampleId: 'sample-2' });
        expect(screen.queryByTestId('group-content')).not.toBeInTheDocument();
    });

    it('keeps the manual open state when re-rendered for the same sample', async () => {
        const user = userEvent.setup();
        const { rerender } = render(SampleDetailsAnnotationSourceGroup, {
            props: { ...defaultProps, initiallyOpen: false, sampleId: 'sample-1' }
        });

        await user.click(screen.getByText('Ground truth'));
        expect(screen.getByTestId('group-content')).toBeInTheDocument();

        // A re-render for the same sample must not clobber the manual toggle.
        await rerender({ ...defaultProps, initiallyOpen: false, sampleId: 'sample-1' });
        expect(screen.getByTestId('group-content')).toBeInTheDocument();
    });
});
