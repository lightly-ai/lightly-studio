import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import PlotToolPill from './PlotToolPill.svelte';

const RECT_TITLE = 'Toggle rectangle selection mode. In normal mode, use shift + drag.';
const LASSO_TITLE = 'Toggle lasso selection mode. In normal mode, use shift + meta + drag.';

// Stands in for the toolbar embedding-atlas renders and PlotPanel paints out.
function buildPlotContainer() {
    const container = document.createElement('div');
    const view = document.createElement('div');
    view.className = 'embedding-view';
    const marquee = document.createElement('button');
    marquee.setAttribute('title', RECT_TITLE);
    const lasso = document.createElement('button');
    lasso.setAttribute('title', LASSO_TITLE);
    view.append(marquee, lasso);
    container.append(view);
    document.body.append(container);
    return { container, marquee, lasso };
}

afterEach(() => {
    document.body.innerHTML = '';
});

describe('PlotToolPill.svelte', () => {
    it('starts on pan and marks only the active tool as pressed', () => {
        const { container } = buildPlotContainer();
        render(PlotToolPill, { props: { plotContainer: container, activeTool: 'pan' } });

        expect(screen.getByTestId('plot-tool-pan')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('plot-tool-rectangle')).toHaveAttribute('aria-pressed', 'false');
        expect(screen.getByTestId('plot-tool-lasso')).toHaveAttribute('aria-pressed', 'false');
    });

    it('arms the library button behind the chosen tool', async () => {
        const user = userEvent.setup();
        const { container, lasso } = buildPlotContainer();
        const lassoClick = vi.spyOn(lasso, 'click');
        render(PlotToolPill, { props: { plotContainer: container, activeTool: 'pan' } });

        await user.click(screen.getByTestId('plot-tool-lasso'));

        expect(screen.getByTestId('plot-tool-lasso')).toHaveAttribute('aria-pressed', 'true');
        expect(lassoClick).toHaveBeenCalledTimes(1);
    });

    // Changing a filter (picking a tag, committing a region) restarts the embeddings query and
    // unmounts the plot while it loads. The parent holds `activeTool` so the remounted pill
    // comes back on the user's tool instead of pan.
    it('restores the tool it is mounted with and re-arms the library', () => {
        const { container, lasso } = buildPlotContainer();
        const lassoClick = vi.spyOn(lasso, 'click');
        render(PlotToolPill, { props: { plotContainer: container, activeTool: 'lasso' } });

        expect(screen.getByTestId('plot-tool-lasso')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('plot-tool-pan')).toHaveAttribute('aria-pressed', 'false');
        expect(lassoClick).toHaveBeenCalledTimes(1);
    });

    it('renders nothing interactive against a missing plot container', () => {
        render(PlotToolPill, { props: { plotContainer: null, activeTool: 'pan' } });

        // The pill still shows: the container arrives one tick after the plot mounts.
        expect(screen.getByTestId('plot-tool-pill')).toBeInTheDocument();
    });

    it('shows the drag shortcut when hovering a selection tool', async () => {
        const user = userEvent.setup();
        const { container } = buildPlotContainer();
        render(PlotToolPill, { props: { plotContainer: container, activeTool: 'pan' } });

        await user.hover(screen.getByTestId('plot-tool-lasso'));

        expect(screen.getByText('Lasso select')).toBeInTheDocument();
        expect(screen.getByText(/^Shift \+ (⌘|Win)$/)).toBeInTheDocument();
        expect(screen.getByText(/to drag a lasso/)).toBeInTheDocument();
    });

    it('shows the shortcut on keyboard focus and describes the focused tool with it', async () => {
        const user = userEvent.setup();
        const { container } = buildPlotContainer();
        render(PlotToolPill, { props: { plotContainer: container, activeTool: 'pan' } });

        await user.tab();
        await user.tab();

        const rectangle = screen.getByTestId('plot-tool-rectangle');
        expect(rectangle).toHaveFocus();
        const tooltip = screen.getByRole('tooltip');
        expect(tooltip).toHaveTextContent('Hold Shift to drag a rectangle');
        expect(rectangle).toHaveAttribute('aria-describedby', tooltip.id);
    });

    it('shows no shortcut for pan', async () => {
        const user = userEvent.setup();
        const { container } = buildPlotContainer();
        render(PlotToolPill, { props: { plotContainer: container, activeTool: 'pan' } });

        await user.hover(screen.getByTestId('plot-tool-pan'));

        expect(screen.getByText('Pan')).toBeInTheDocument();
        expect(screen.queryByText(/Hold/)).not.toBeInTheDocument();
    });
});
