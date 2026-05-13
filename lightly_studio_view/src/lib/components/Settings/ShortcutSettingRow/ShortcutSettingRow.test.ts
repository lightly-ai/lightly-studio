import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ShortcutSettingRow from './ShortcutSettingRow.svelte';

describe('ShortcutSettingRow', () => {
    it('should render label and current value', () => {
        render(ShortcutSettingRow, {
            props: { id: 'test-key', label: 'Test Shortcut', value: 'v', isRecording: false }
        });

        expect(screen.getByText('Test Shortcut')).toBeInTheDocument();
        expect(screen.getByText('v')).toBeInTheDocument();
    });

    it('should show "Press a key..." when recording', () => {
        render(ShortcutSettingRow, {
            props: { id: 'test-key', label: 'Test Shortcut', value: 'v', isRecording: true }
        });

        expect(screen.getByText('Press a key...')).toBeInTheDocument();
        expect(screen.queryByText('v')).not.toBeInTheDocument();
    });

    it('should call onStartRecording when clicked', async () => {
        const onStartRecording = vi.fn();
        render(ShortcutSettingRow, {
            props: {
                id: 'test-key',
                label: 'Test Shortcut',
                value: 'v',
                isRecording: false,
                onStartRecording
            }
        });

        await fireEvent.click(screen.getByRole('button'));
        expect(onStartRecording).toHaveBeenCalledOnce();
    });

    it('should render as disabled when disabled prop is set', () => {
        render(ShortcutSettingRow, {
            props: {
                id: 'test-key',
                label: 'Test Shortcut',
                value: 'Alt + scroll',
                isRecording: false,
                disabled: true
            }
        });

        expect(screen.getByRole('button')).toBeDisabled();
    });

    it('should associate label with button via id', () => {
        render(ShortcutSettingRow, {
            props: { id: 'my-shortcut', label: 'My Shortcut', value: 'x', isRecording: false }
        });

        const button = document.getElementById('my-shortcut');
        expect(button).not.toBeNull();
        expect(button?.tagName.toLowerCase()).toBe('button');
    });
});
