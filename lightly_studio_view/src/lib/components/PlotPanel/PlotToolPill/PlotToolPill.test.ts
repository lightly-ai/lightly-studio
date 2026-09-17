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
        render(PlotToolPill, { props: { plotContainer: container } });

        expect(screen.getByTestId('plot-tool-pan')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('plot-tool-rectangle')).toHaveAttribute('aria-pressed', 'false');
        expect(screen.getByTestId('plot-tool-lasso')).toHaveAttribute('aria-pressed', 'false');
    });

    it('arms the library button behind the chosen tool', async () => {
        const user = userEvent.setup();
        const { container, lasso } = buildPlotContainer();
        const lassoClick = vi.spyOn(lasso, 'click');
        render(PlotToolPill, { props: { plotContainer: container } });

        await user.click(screen.getByTestId('plot-tool-lasso'));

        expect(screen.getByTestId('plot-tool-lasso')).toHaveAttribute('aria-pressed', 'true');
        expect(lassoClick).toHaveBeenCalledTimes(1);
    });

    it('renders nothing interactive against a missing plot container', () => {
        render(PlotToolPill, { props: { plotContainer: null } });

        // The pill still shows: the container arrives one tick after the plot mounts.
        expect(screen.getByTestId('plot-tool-pill')).toBeInTheDocument();
    });
});
