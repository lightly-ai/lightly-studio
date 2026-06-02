import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import MetadataWeightingForm from './MetadataWeightingForm.svelte';

describe('MetadataWeightingForm', () => {
    it('renders the form', () => {
        render(MetadataWeightingForm, {
            props: {
                params: { metadata_key: '', strength: 1 },
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('metadata-weighting-form')).toBeInTheDocument();
    });

    it('does not render the metadata key select when no metadata field names are provided', () => {
        render(MetadataWeightingForm, {
            props: {
                params: { metadata_key: '', strength: 1 },
                onUpdate: vi.fn()
            }
        });

        expect(screen.queryByTestId('strategy-metadata-key-input')).not.toBeInTheDocument();
    });

    it('renders a select trigger when metadata field names are provided', () => {
        render(MetadataWeightingForm, {
            props: {
                params: { metadata_key: '', strength: 1 },
                metadataFieldNames: ['brightness', 'contrast'],
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('strategy-metadata-key-input')).toBeInTheDocument();
    });

    it('renders the strength input with the current value', () => {
        render(MetadataWeightingForm, {
            props: {
                params: { metadata_key: '', strength: 2.5 },
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('strategy-metadata-weighting-strength-input')).toHaveValue(2.5);
    });
});
