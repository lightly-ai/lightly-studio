import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import Input from './input.svelte';

const progressSelector = '[data-testid="input-progress"]';
const inputSelector = 'input';

describe('Input', () => {
    it('renders an input element', () => {
        const { container } = render(Input);

        expect(container.querySelector(inputSelector)).toBeInTheDocument();
    });

    it('does not render the progress bar by default', () => {
        const { container } = render(Input);

        expect(container.querySelector(progressSelector)).toBeNull();
    });

    it('input is not disabled by default', () => {
        const { container } = render(Input);

        expect(container.querySelector(inputSelector)).not.toBeDisabled();
    });

    it('forwards value to the input element', () => {
        const { container } = render(Input, { props: { value: 'hello' } });

        expect(container.querySelector(inputSelector)).toHaveValue('hello');
    });

    it('forwards placeholder to the input element', () => {
        const { container } = render(Input, { props: { placeholder: 'Type a tag…' } });

        expect(container.querySelector(inputSelector)).toHaveAttribute(
            'placeholder',
            'Type a tag…'
        );
    });

    it('forwards class to the input element', () => {
        const { container } = render(Input, { props: { class: 'custom-class' } });

        const input = container.querySelector(inputSelector);
        expect(input?.className).toContain('custom-class');
        expect(input?.className).toContain('rounded-md');
    });

    describe('disabled', () => {
        it('disables the input when disabled is true', () => {
            const { container } = render(Input, { props: { disabled: true } });

            expect(container.querySelector(inputSelector)).toBeDisabled();
        });

        it('does not render a progress bar when only disabled is true', () => {
            const { container } = render(Input, { props: { disabled: true } });

            expect(container.querySelector(progressSelector)).toBeNull();
        });
    });

    describe('isPending', () => {
        it('renders a progress bar when isPending is true', () => {
            const { container } = render(Input, { props: { isPending: true } });

            const progress = container.querySelector(progressSelector);
            expect(progress).toBeInTheDocument();
            expect(progress).toHaveAttribute('role', 'progressbar');
            expect(progress?.querySelector('.input-progress-indicator')).toBeInTheDocument();
        });

        it('disables the input when isPending is true', () => {
            const { container } = render(Input, { props: { isPending: true } });

            expect(container.querySelector(inputSelector)).toBeDisabled();
        });

        it('keeps the input disabled even when disabled={false} is also passed', () => {
            const { container } = render(Input, {
                props: { isPending: true, disabled: false }
            });

            expect(container.querySelector(inputSelector)).toBeDisabled();
        });

        it('keeps the existing value visible while pending', () => {
            const { container } = render(Input, {
                props: { isPending: true, value: 'my-tag' }
            });

            expect(container.querySelector(inputSelector)).toHaveValue('my-tag');
        });

        it('keeps the placeholder visible while pending', () => {
            const { container } = render(Input, {
                props: { isPending: true, placeholder: 'Assigning…' }
            });

            expect(container.querySelector(inputSelector)).toHaveAttribute(
                'placeholder',
                'Assigning…'
            );
        });

        it('keeps the class applied to the input while pending', () => {
            const { container } = render(Input, {
                props: { isPending: true, class: 'custom-class' }
            });

            expect(container.querySelector(inputSelector)?.className).toContain('custom-class');
        });

        it('progress bar has an accessible label', () => {
            const { container } = render(Input, { props: { isPending: true } });

            const progress = container.querySelector(progressSelector);
            expect(progress).toHaveAttribute('aria-label', 'Loading');
        });

        it('does not render a progress bar when isPending is false', () => {
            const { container } = render(Input, { props: { isPending: false } });

            expect(container.querySelector(progressSelector)).toBeNull();
        });
    });
});
