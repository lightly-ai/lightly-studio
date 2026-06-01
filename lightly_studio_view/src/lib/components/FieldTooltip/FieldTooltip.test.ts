import { describe, it, expect } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import FieldTooltip from './FieldTooltip.svelte';

const defaultProps = { content: 'Some info' };

describe('FieldTooltip', () => {
    it('renders the help icon', () => {
        render(FieldTooltip, { props: defaultProps });

        expect(screen.getByRole('button', { name: 'More information' })).toBeInTheDocument();
    });

    it('does not show tooltip initially', () => {
        render(FieldTooltip, { props: defaultProps });

        expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    });

    it('shows tooltip on mouse enter', async () => {
        render(FieldTooltip, { props: defaultProps });

        await fireEvent.mouseEnter(screen.getByRole('button', { name: 'More information' }));

        expect(screen.getByRole('tooltip')).toBeInTheDocument();
        expect(screen.getByRole('tooltip')).toHaveTextContent('Some info');
    });

    it('hides tooltip on mouse leave', async () => {
        render(FieldTooltip, { props: defaultProps });

        const wrapper = screen.getByRole('button', { name: 'More information' });
        await fireEvent.mouseEnter(wrapper);
        await fireEvent.mouseLeave(wrapper);

        expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    });

    it('shows tooltip on focus', async () => {
        render(FieldTooltip, { props: { content: 'Keyboard accessible info' } });

        await fireEvent.focusIn(screen.getByRole('button', { name: 'More information' }));

        expect(screen.getByRole('tooltip')).toBeInTheDocument();
        expect(screen.getByRole('tooltip')).toHaveTextContent('Keyboard accessible info');
    });

    it('hides tooltip on blur', async () => {
        render(FieldTooltip, { props: { content: 'Keyboard accessible info' } });

        const wrapper = screen.getByRole('button', { name: 'More information' });
        await fireEvent.focusIn(wrapper);
        await fireEvent.focusOut(wrapper);

        expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    });

    it('renders the content prop in the tooltip', async () => {
        render(FieldTooltip, { props: { content: 'This field controls the threshold value' } });

        await fireEvent.mouseEnter(screen.getByRole('button', { name: 'More information' }));

        expect(screen.getByRole('tooltip')).toHaveTextContent(
            'This field controls the threshold value'
        );
    });
});
