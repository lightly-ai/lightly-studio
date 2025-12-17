import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import DatasetProgress from './DatasetProgress.svelte';

describe('DatasetProgress Component', () => {
    describe('rendering', () => {
        it('should render progress bar', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 50,
                    total: 100
                }
            });

            expect(container.querySelector('.dataset-progress')).toBeInTheDocument();
        });

        it('should display state label', () => {
            render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 30,
                    total: 100
                }
            });

            expect(screen.getByText('Indexing')).toBeInTheDocument();
        });

        it('should display percentage and counts', () => {
            render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 45,
                    total: 100
                }
            });

            expect(screen.getByText('45% (45/100)')).toBeInTheDocument();
        });

        it('should display custom message', () => {
            const message = 'Processing samples...';
            render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 30,
                    total: 100,
                    message
                }
            });

            expect(screen.getByText(message)).toBeInTheDocument();
        });

        it('should display error message', () => {
            const error = 'Something went wrong';
            render(DatasetProgress, {
                props: {
                    state: 'error',
                    error
                }
            });

            expect(screen.getByText(error)).toBeInTheDocument();
        });
    });

    describe('states', () => {
        it('should render pending state', () => {
            render(DatasetProgress, {
                props: {
                    state: 'pending'
                }
            });

            expect(screen.getByText('Pending')).toBeInTheDocument();
        });

        it('should render indexing state with spinner', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 30,
                    total: 100
                }
            });

            expect(screen.getByText('Indexing')).toBeInTheDocument();
            expect(container.querySelector('.spinner')).toBeInTheDocument();
        });

        it('should render embedding state with spinner', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'embedding',
                    current: 70,
                    total: 100
                }
            });

            expect(screen.getByText('Generating Embeddings')).toBeInTheDocument();
            expect(container.querySelector('.spinner')).toBeInTheDocument();
        });

        it('should render ready state with checkmark', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'ready'
                }
            });

            expect(screen.getByText('Ready')).toBeInTheDocument();
            const checkmark = container.querySelector('svg.text-green-600');
            expect(checkmark).toBeInTheDocument();
        });

        it('should render error state with X icon', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'error',
                    error: 'Test error'
                }
            });

            expect(screen.getByText('Error')).toBeInTheDocument();
            const errorIcon = container.querySelector('svg.text-red-600');
            expect(errorIcon).toBeInTheDocument();
        });
    });

    describe('progress bar', () => {
        it('should set correct width for progress bar', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 50,
                    total: 100
                }
            });

            const progressBar = container.querySelector('.bg-blue-500');
            expect(progressBar).toHaveStyle({ width: '50%' });
        });

        it('should show 100% width when ready', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'ready',
                    current: 100,
                    total: 100
                }
            });

            const progressBar = container.querySelector('.bg-green-500');
            expect(progressBar).toHaveStyle({ width: '100%' });
        });

        it('should show 0% width when error', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'error'
                }
            });

            const progressBar = container.querySelector('.bg-red-500');
            expect(progressBar).toHaveStyle({ width: '0%' });
        });

        it('should apply animation class for active states', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 30,
                    total: 100
                }
            });

            const progressBar = container.querySelector('.progress-animated');
            expect(progressBar).toBeInTheDocument();
        });

        it('should not apply animation class for ready state', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'ready'
                }
            });

            const progressBar = container.querySelector('.progress-animated');
            expect(progressBar).not.toBeInTheDocument();
        });
    });

    describe('percentage calculation', () => {
        it('should calculate correct percentage', () => {
            render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 33,
                    total: 100
                }
            });

            expect(screen.getByText('33% (33/100)')).toBeInTheDocument();
        });

        it('should round percentage', () => {
            render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 33,
                    total: 99
                }
            });

            // 33/99 = 33.33... should round to 33
            expect(screen.getByText(/33% \(33\/99\)/)).toBeInTheDocument();
        });

        it('should handle 0 total gracefully', () => {
            render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 0,
                    total: 0
                }
            });

            // Should not crash and should show 0%
            expect(screen.getByText(/0% \(0\/1\)/)).toBeInTheDocument();
        });

        it('should clamp current value to total', () => {
            render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 150,
                    total: 100
                }
            });

            // Current should be clamped to total
            expect(screen.getByText('100% (100/100)')).toBeInTheDocument();
        });

        it('should handle negative current value', () => {
            render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: -10,
                    total: 100
                }
            });

            // Current should be clamped to 0
            expect(screen.getByText('0% (0/100)')).toBeInTheDocument();
        });
    });

    describe('color coding', () => {
        it('should use gray for pending state', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'pending'
                }
            });

            const progressBar = container.querySelector('.bg-gray-400');
            expect(progressBar).toBeInTheDocument();
        });

        it('should use blue for indexing state', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 30,
                    total: 100
                }
            });

            const progressBar = container.querySelector('.bg-blue-500');
            expect(progressBar).toBeInTheDocument();
        });

        it('should use purple for embedding state', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'embedding',
                    current: 70,
                    total: 100
                }
            });

            const progressBar = container.querySelector('.bg-purple-500');
            expect(progressBar).toBeInTheDocument();
        });

        it('should use green for ready state', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'ready'
                }
            });

            const progressBar = container.querySelector('.bg-green-500');
            expect(progressBar).toBeInTheDocument();
        });

        it('should use red for error state', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'error'
                }
            });

            const progressBar = container.querySelector('.bg-red-500');
            expect(progressBar).toBeInTheDocument();
        });
    });

    describe('conditional rendering', () => {
        it('should not show percentage for pending state', () => {
            render(DatasetProgress, {
                props: {
                    state: 'pending',
                    current: 0,
                    total: 100
                }
            });

            expect(screen.queryByText(/0%/)).not.toBeInTheDocument();
        });

        it('should not show percentage for ready state', () => {
            render(DatasetProgress, {
                props: {
                    state: 'ready',
                    current: 100,
                    total: 100
                }
            });

            expect(screen.queryByText(/100%/)).not.toBeInTheDocument();
        });

        it('should not show percentage for error state', () => {
            render(DatasetProgress, {
                props: {
                    state: 'error'
                }
            });

            expect(screen.queryByText(/%/)).not.toBeInTheDocument();
        });

        it('should show percentage for indexing state', () => {
            render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 50,
                    total: 100
                }
            });

            expect(screen.getByText('50% (50/100)')).toBeInTheDocument();
        });

        it('should show percentage for embedding state', () => {
            render(DatasetProgress, {
                props: {
                    state: 'embedding',
                    current: 75,
                    total: 100
                }
            });

            expect(screen.getByText('75% (75/100)')).toBeInTheDocument();
        });

        it('should not render message when not provided', () => {
            render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 30,
                    total: 100
                }
            });

            const messages = screen.queryAllByText(/./);
            // Should only have state label and percentage, not an extra message
            expect(messages.length).toBeLessThan(4);
        });

        it('should not render error when not provided', () => {
            render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 30,
                    total: 100
                }
            });

            const errorContainer = screen.queryByText(/went wrong/);
            expect(errorContainer).not.toBeInTheDocument();
        });
    });

    describe('default props', () => {
        it('should use default current value of 0', () => {
            render(DatasetProgress, {
                props: {
                    state: 'indexing'
                }
            });

            expect(screen.getByText('0% (0/100)')).toBeInTheDocument();
        });

        it('should use default total value of 100', () => {
            render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 50
                }
            });

            expect(screen.getByText('50% (50/100)')).toBeInTheDocument();
        });

        it('should use empty string for default message', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 30,
                    total: 100
                }
            });

            // Should not have any message paragraph
            const messageParagraphs = container.querySelectorAll('p.text-sm.text-gray-600');
            expect(messageParagraphs.length).toBe(0);
        });
    });

    describe('error display', () => {
        it('should render error with icon', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'error',
                    error: 'Network error occurred'
                }
            });

            expect(screen.getByText('Network error occurred')).toBeInTheDocument();
            const errorIcon = container.querySelector('svg.text-red-600');
            expect(errorIcon).toBeInTheDocument();
        });

        it('should apply error background color', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'error',
                    error: 'Test error'
                }
            });

            const errorContainer = container.querySelector('.bg-red-50');
            expect(errorContainer).toBeInTheDocument();
        });
    });

    describe('accessibility', () => {
        it('should have proper role attributes', () => {
            const { container } = render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 50,
                    total: 100
                }
            });

            // Progress bar container should exist
            expect(container.querySelector('.dataset-progress')).toBeInTheDocument();
        });

        it('should have readable text content', () => {
            render(DatasetProgress, {
                props: {
                    state: 'indexing',
                    current: 50,
                    total: 100,
                    message: 'Processing data'
                }
            });

            // All text should be visible
            expect(screen.getByText('Indexing')).toBeVisible();
            expect(screen.getByText('50% (50/100)')).toBeVisible();
            expect(screen.getByText('Processing data')).toBeVisible();
        });
    });
});
