import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import ObjectDetectionConfigFields from './ObjectDetectionConfigFieldsTestWrapper.svelte';

describe('ObjectDetectionConfigFields', () => {
    it('renders the IoU threshold value formatted to two decimals', () => {
        render(ObjectDetectionConfigFields, { props: { iouThreshold: 0.5 } });

        expect(screen.getByTestId('iou-threshold-value')).toHaveTextContent('0.50');
    });

    it('exposes the IoU slider bounds and step', () => {
        render(ObjectDetectionConfigFields, { props: { iouThreshold: 0.45 } });

        const thumb = screen.getByRole('slider');
        expect(thumb).toHaveAttribute('aria-valuemin', '0');
        expect(thumb).toHaveAttribute('aria-valuemax', '1');
        expect(thumb).toHaveAttribute('aria-valuenow', '0.45');
    });

    it('steps the IoU threshold by 0.05 with the arrow keys', async () => {
        const user = userEvent.setup();
        render(ObjectDetectionConfigFields, { props: { iouThreshold: 0.5 } });

        const thumb = screen.getByRole('slider');
        thumb.focus();
        await user.keyboard('{ArrowRight}');

        expect(screen.getByTestId('iou-threshold-value')).toHaveTextContent('0.55');
        expect(screen.getByTestId('iou-threshold-state')).toHaveTextContent('0.55');

        await user.keyboard('{ArrowLeft}{ArrowLeft}');

        expect(screen.getByTestId('iou-threshold-value')).toHaveTextContent('0.45');
        expect(screen.getByTestId('iou-threshold-state')).toHaveTextContent('0.45');
    });

    it('renders the class-wise switch reflecting the checked state', () => {
        render(ObjectDetectionConfigFields, { props: { classwise: true } });

        expect(screen.getByTestId('classwise-switch')).toBeChecked();
    });

    it('toggles class-wise matching when the switch is clicked', async () => {
        const user = userEvent.setup();
        render(ObjectDetectionConfigFields, { props: { classwise: true } });

        await user.click(screen.getByTestId('classwise-switch'));

        expect(screen.getByTestId('classwise-switch')).not.toBeChecked();
        expect(screen.getByTestId('classwise-state')).toHaveTextContent('false');
    });
});
