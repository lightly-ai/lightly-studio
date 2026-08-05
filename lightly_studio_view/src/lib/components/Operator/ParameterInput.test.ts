import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ParameterInput from './ParameterInput.svelte';

const defaultProps = {
    name: 'prompt',
    value: '',
    required: true,
    isMissing: false,
    onUpdate: vi.fn()
};

describe('ParameterInput', () => {
    it('leaves a submittable field unflagged', () => {
        render(ParameterInput, { props: { ...defaultProps, value: 'person', onUpdate: vi.fn() } });

        expect(screen.getByLabelText(/prompt/)).toBeValid();
        expect(screen.queryByText(/required|valid value/)).not.toBeInTheDocument();
    });

    it('asks for a value when a required field is missing one', () => {
        render(ParameterInput, { props: { ...defaultProps, isMissing: true, onUpdate: vi.fn() } });

        expect(screen.getByLabelText(/prompt/)).toBeInvalid();
        expect(screen.getByText('This field is required.')).toBeInTheDocument();
    });

    it('surfaces an unusable value in an optional field without asking for one', () => {
        // Whitespace blocks Execute even though the field is optional, so the reason has to be visible
        // — but the field may be left empty, so the hint must not call it required.
        render(ParameterInput, {
            props: {
                ...defaultProps,
                required: false,
                value: '   ',
                isMissing: true,
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByLabelText(/prompt/)).toBeInvalid();
        expect(screen.getByText('Enter a valid value or clear this field.')).toBeInTheDocument();
    });
});
