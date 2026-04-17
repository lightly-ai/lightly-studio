import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import CollectionLayoutAuxControls from './CollectionLayoutAuxControls.svelte';
import '@testing-library/jest-dom';

describe('CollectionLayoutAuxControls', () => {
    const mockRouteType = {
        isSamples: true,
        isGroups: false,
        isGroupDetails: false,
        isAnnotations: false,
        isSampleDetails: false,
        isAnnotationDetails: false,
        isCaptions: false,
        isVideos: false,
        isVideoFrames: false,
        isVideoDetails: false,
        showLeftSidebar: true
    };

    it('renders button when on samples route with embeddings', () => {
        render(CollectionLayoutAuxControls, {
            props: {
                routeType: mockRouteType,
                hasEmbeddings: true,
                showPlot: false,
                setShowPlot: vi.fn()
            }
        });

        expect(screen.getByTestId('toggle-plot-button')).toBeInTheDocument();
        expect(screen.getByText('Show Embeddings')).toBeInTheDocument();
    });

    it('renders button when on videos route with embeddings', () => {
        render(CollectionLayoutAuxControls, {
            props: {
                routeType: { ...mockRouteType, isSamples: false, isVideos: true },
                hasEmbeddings: true,
                showPlot: false,
                setShowPlot: vi.fn()
            }
        });

        expect(screen.getByTestId('toggle-plot-button')).toBeInTheDocument();
    });

    it('does not render button when no embeddings', () => {
        render(CollectionLayoutAuxControls, {
            props: {
                routeType: mockRouteType,
                hasEmbeddings: false,
                showPlot: false,
                setShowPlot: vi.fn()
            }
        });

        expect(screen.queryByTestId('toggle-plot-button')).not.toBeInTheDocument();
    });

    it('does not render button on annotations route', () => {
        render(CollectionLayoutAuxControls, {
            props: {
                routeType: { ...mockRouteType, isSamples: false, isAnnotations: true },
                hasEmbeddings: true,
                showPlot: false,
                setShowPlot: vi.fn()
            }
        });

        expect(screen.queryByTestId('toggle-plot-button')).not.toBeInTheDocument();
    });

    it('calls setShowPlot when button clicked', async () => {
        const setShowPlot = vi.fn();
        render(CollectionLayoutAuxControls, {
            props: {
                routeType: mockRouteType,
                hasEmbeddings: true,
                showPlot: false,
                setShowPlot
            }
        });

        const button = screen.getByTestId('toggle-plot-button');
        button.click();

        expect(setShowPlot).toHaveBeenCalledWith(true);
    });

    it('renders button with ghost variant when showPlot is false', () => {
        render(CollectionLayoutAuxControls, {
            props: {
                routeType: mockRouteType,
                hasEmbeddings: true,
                showPlot: false,
                setShowPlot: vi.fn()
            }
        });

        const button = screen.getByTestId('toggle-plot-button');
        // Button should have ghost variant classes
        expect(button.className).toMatch(/hover:bg-accent/);
    });

    it('renders button with default variant when showPlot is true', () => {
        render(CollectionLayoutAuxControls, {
            props: {
                routeType: mockRouteType,
                hasEmbeddings: true,
                showPlot: true,
                setShowPlot: vi.fn()
            }
        });

        const button = screen.getByTestId('toggle-plot-button');
        // When showPlot is true, variant should be 'default', not 'ghost'
        expect(button.className).not.toContain('ghost');
    });
});
