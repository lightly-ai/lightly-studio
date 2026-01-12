import { render, fireEvent, getByLabelText } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import BrushTool from './BrushToolPopUp.svelte';

vi.mock('$lib/contexts/SampleDetailsToolbar.svelte', async () => {
  return {
    useSampleDetailsToolbarContext: () => ({
      brush: {
        mode: 'brush',
        size: 10,
      },
    }),
  };
});

describe('BrushTool component', () => {
  it('switches to eraser mode when eraser button is clicked', async () => {
    const { container } = render(BrushTool);

    const eraserButton = getByLabelText(container, 'Eraser mode');

    await fireEvent.click(eraserButton);

    expect(eraserButton.className).toContain('bg-primary/20');
  });

  it('switches back to brush mode when brush button is clicked', async () => {
    const { container } = render(BrushTool);

    const brushButton = getByLabelText(container, 'Brush mode');

    await fireEvent.click(brushButton);

    expect(brushButton.className).toContain('bg-primary/20');
  });

  it('updates brush size when slider changes', async () => {
    const { getByRole } = render(BrushTool);

    const slider = getByRole('slider') as HTMLInputElement;

    await fireEvent.input(slider, { target: { value: '42' } });

    expect(slider.value).toBe('42');
  });
});
