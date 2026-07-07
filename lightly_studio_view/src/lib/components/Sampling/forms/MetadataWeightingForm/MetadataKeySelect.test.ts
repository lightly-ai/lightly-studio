import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import MetadataKeySelect from './MetadataKeySelect.svelte';

describe('MetadataKeySelect', () => {
    it('renders the select trigger', () => {
        render(MetadataKeySelect, {
            props: {
                value: '',
                fieldNames: ['brightness', 'contrast'],
                onValueChange: vi.fn()
            }
        });

        expect(screen.getByTestId('strategy-metadata-key-input')).toBeInTheDocument();
    });

    it('shows the placeholder when no value is selected', () => {
        render(MetadataKeySelect, {
            props: {
                value: '',
                fieldNames: ['brightness', 'contrast'],
                onValueChange: vi.fn()
            }
        });

        expect(screen.getByTestId('strategy-metadata-key-input')).toHaveTextContent(
            'Select a metadata field'
        );
    });

    it('shows the selected value in the trigger', () => {
        render(MetadataKeySelect, {
            props: {
                value: 'brightness',
                fieldNames: ['brightness', 'contrast'],
                onValueChange: vi.fn()
            }
        });

        expect(screen.getByTestId('strategy-metadata-key-input')).toHaveTextContent('brightness');
    });
});
