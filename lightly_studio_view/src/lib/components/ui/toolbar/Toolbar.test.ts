import { render, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import Toolbar from './Toolbar.svelte';
import { MousePointer2, Hand, Box } from '@lucide/svelte';

const defaultProps = {
    items: [
        { id: 'select', label: 'Select', icon: MousePointer2, shortcut: 's', action: 'select' },
        {
            id: 'drag',
            label: 'Drag',
            icon: Hand,
            shortcut: 'd',
            action: 'pan',
            hint: 'Hold Space to pan temporarily'
        },
        { id: 'create', label: 'Create', icon: Box, shortcut: 'b', action: 'draw' }
    ],
    activeTool: 'select',
    onToolChange: vi.fn()
};

describe('Toolbar', () => {
    it('renders all visible items as buttons', () => {
        const { getByLabelText } = render(Toolbar, { props: defaultProps });

        expect(getByLabelText('Select')).toBeInTheDocument();
        expect(getByLabelText('Drag')).toBeInTheDocument();
        expect(getByLabelText('Create')).toBeInTheDocument();
    });

    it('calls onToolChange when a button is clicked', async () => {
        const onToolChange = vi.fn();
        const { getByLabelText } = render(Toolbar, {
            props: { ...defaultProps, onToolChange }
        });

        await fireEvent.click(getByLabelText('Drag'));

        expect(onToolChange).toHaveBeenCalledWith('drag', 'click');
    });

    it('hides items with visible set to false', () => {
        const { queryByLabelText } = render(Toolbar, {
            props: {
                ...defaultProps,
                items: [
                    { id: 'select', label: 'Select', icon: MousePointer2 },
                    { id: 'drag', label: 'Drag', icon: Hand, visible: false }
                ]
            }
        });

        expect(queryByLabelText('Select')).toBeInTheDocument();
        expect(queryByLabelText('Drag')).not.toBeInTheDocument();
    });

    it('disables items with a disabledReason', async () => {
        const onToolChange = vi.fn();
        const { getByLabelText } = render(Toolbar, {
            props: {
                ...defaultProps,
                onToolChange,
                items: [
                    {
                        id: 'drag',
                        label: 'Drag',
                        icon: Hand,
                        disabledReason: 'Coming soon'
                    }
                ]
            }
        });

        expect(getByLabelText('Drag')).toBeDisabled();
        await fireEvent.click(getByLabelText('Drag'));
        expect(onToolChange).not.toHaveBeenCalled();
    });

    it('activates tool on keyboard shortcut', async () => {
        const onToolChange = vi.fn();
        render(Toolbar, { props: { ...defaultProps, onToolChange } });

        await fireEvent.keyDown(window, { key: 'd' });

        expect(onToolChange).toHaveBeenCalledWith('drag', 'shortcut');
    });

    it('ignores shortcuts when focus is on a text input', async () => {
        const onToolChange = vi.fn();
        const { container } = render(Toolbar, {
            props: { ...defaultProps, onToolChange }
        });
        const input = container.appendChild(document.createElement('input'));

        await fireEvent.keyDown(input, { key: 'd' });

        expect(onToolChange).not.toHaveBeenCalled();
    });

    it('ignores shortcuts for disabled items', async () => {
        const onToolChange = vi.fn();
        render(Toolbar, {
            props: {
                ...defaultProps,
                onToolChange,
                items: [
                    {
                        id: 'drag',
                        label: 'Drag',
                        icon: Hand,
                        shortcut: 'd',
                        disabledReason: 'Coming soon'
                    }
                ]
            }
        });

        await fireEvent.keyDown(window, { key: 'd' });

        expect(onToolChange).not.toHaveBeenCalled();
    });

    it('ignores shortcuts for hidden items', async () => {
        const onToolChange = vi.fn();
        render(Toolbar, {
            props: {
                ...defaultProps,
                onToolChange,
                items: [
                    { id: 'drag', label: 'Drag', icon: Hand, shortcut: 'd', visible: false }
                ]
            }
        });

        await fireEvent.keyDown(window, { key: 'd' });

        expect(onToolChange).not.toHaveBeenCalled();
    });

    it('respects shouldHandleShortcut guard', async () => {
        const onToolChange = vi.fn();
        render(Toolbar, {
            props: {
                ...defaultProps,
                onToolChange,
                shouldHandleShortcut: () => false
            }
        });

        await fireEvent.keyDown(window, { key: 'd' });

        expect(onToolChange).not.toHaveBeenCalled();
    });

    it('matches shortcuts case-insensitively', async () => {
        const onToolChange = vi.fn();
        render(Toolbar, { props: { ...defaultProps, onToolChange } });

        await fireEvent.keyDown(window, { key: 'D' });

        expect(onToolChange).toHaveBeenCalledWith('drag', 'shortcut');
    });

    it('shows tooltip with label, shortcut, and action on hover', async () => {
        const { getByLabelText, getByRole } = render(Toolbar, { props: defaultProps });

        await fireEvent.pointerEnter(getByLabelText('Drag').parentElement!);

        const tooltip = getByRole('tooltip');
        expect(tooltip).toHaveTextContent('Drag');
        expect(tooltip).toHaveTextContent('Press D to pan');
        expect(tooltip).toHaveTextContent('Hold Space to pan temporarily');
    });

    it('shows disabledReason in tooltip instead of label for disabled items', async () => {
        const { getByLabelText, getByRole } = render(Toolbar, {
            props: {
                ...defaultProps,
                items: [
                    {
                        id: 'drag',
                        label: 'Drag',
                        icon: Hand,
                        shortcut: 'd',
                        action: 'pan',
                        disabledReason: 'Coming soon'
                    }
                ]
            }
        });

        await fireEvent.pointerEnter(getByLabelText('Drag').parentElement!);

        const tooltip = getByRole('tooltip');
        expect(tooltip).toHaveTextContent('Coming soon');
        expect(tooltip).not.toHaveTextContent('Press');
    });

    it('hides tooltip on pointerdown', async () => {
        const { getByLabelText, getByRole, queryByRole } = render(Toolbar, {
            props: defaultProps
        });
        const trigger = getByLabelText('Drag').parentElement!;

        await fireEvent.pointerEnter(trigger);
        expect(getByRole('tooltip')).toBeInTheDocument();

        await fireEvent.pointerDown(trigger);
        expect(queryByRole('tooltip')).not.toBeInTheDocument();
    });

    it('applies active styling to the active tool button', () => {
        const { getByLabelText } = render(Toolbar, { props: defaultProps });

        expect(getByLabelText('Select').className).toContain('bg-black/40');
        expect(getByLabelText('Drag').className).toContain('hover:bg-black/20');
    });
});
