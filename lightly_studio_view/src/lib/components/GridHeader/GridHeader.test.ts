import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import GridHeaderTest from './GridHeaderTest.test.svelte';
import '@testing-library/jest-dom';

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        updateSampleSize: vi.fn(),
        sampleSize: writable({ width: 4 })
    })
}));

describe('GridHeader', () => {
    it('renders children snippet when provided', () => {
        const { container } = render(GridHeaderTest, {
            props: {
                testCase: 'children-only'
            }
        });

        expect(container.textContent).toContain('Test Title');
    });

    it('renders ImageSizeControl by default', () => {
        render(GridHeaderTest, {
            props: {
                testCase: 'children-only'
            }
        });

        const zoomOutButton = screen.getByLabelText('Zoom out');
        expect(zoomOutButton).toBeInTheDocument();
    });

    it('does not render ImageSizeControl when showImageSizeControl is false', () => {
        render(GridHeaderTest, {
            props: {
                testCase: 'no-image-size-control'
            }
        });

        const zoomOutButton = screen.queryByLabelText('Zoom out');
        expect(zoomOutButton).not.toBeInTheDocument();
    });

    it('renders auxControls snippet when provided', () => {
        const { container } = render(GridHeaderTest, {
            props: {
                testCase: 'with-aux-controls'
            }
        });

        expect(container.textContent).toContain('Aux Controls');
    });

    it('renders selectionControls snippet when provided', () => {
        const { container } = render(GridHeaderTest, {
            props: {
                testCase: 'with-selection-controls'
            }
        });

        expect(container.textContent).toContain('Selection Controls');
    });

    it('renders all elements together when provided', () => {
        const { container } = render(GridHeaderTest, {
            props: {
                testCase: 'all-elements'
            }
        });

        expect(container.textContent).toContain('Main Content');
        expect(container.textContent).toContain('Selection Controls');
        expect(container.textContent).toContain('Extra Controls');
        expect(screen.getByLabelText('Zoom out')).toBeInTheDocument();
    });

    it('lays out controls in a flex row that can wrap instead of overflowing', () => {
        const { container } = render(GridHeaderTest, {
            props: {
                testCase: 'children-only'
            }
        });

        const wrapper = container.querySelector('.flex.flex-wrap');
        expect(wrapper).toBeInTheDocument();
    });

    it('gives the children region flexible width', () => {
        const { container } = render(GridHeaderTest, {
            props: {
                testCase: 'children-only'
            }
        });

        const childrenContainer = container.querySelector('.flex-1');
        expect(childrenContainer).toBeInTheDocument();
    });
});
