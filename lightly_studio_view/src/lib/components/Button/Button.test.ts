import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { ChevronDown, Pencil } from '@lucide/svelte';
import '@testing-library/jest-dom';
import ButtonTestWrapper from './ButtonTestWrapper.test.svelte';

const labelSelector = 'button > span:not([data-testid="button-progress"])';
const iconSelector = 'button > svg';
const progressSelector = '[data-testid="button-progress"]';

describe('Button', () => {
    it('renders label children inside a span', () => {
        const { container } = render(ButtonTestWrapper, { props: { label: 'Click me' } });

        const button = container.querySelector('button');
        expect(button).toBeInTheDocument();
        expect(button).toHaveTextContent('Click me');
        expect(container.querySelector(labelSelector)).toHaveTextContent('Click me');
    });

    it('renders the icon when provided', () => {
        const { container } = render(ButtonTestWrapper, {
            props: { label: 'Edit', icon: Pencil }
        });

        const svg = container.querySelector(iconSelector);
        expect(svg).toBeInTheDocument();
        expect(svg).toHaveClass('size-4');
    });

    it('renders without a label span when no children are provided', () => {
        const { container } = render(ButtonTestWrapper, { props: { icon: Pencil } });

        expect(container.querySelector('button')).toBeInTheDocument();
        expect(container.querySelector(labelSelector)).toBeNull();
    });

    it('renders the trailing icon after the label when iconAfter is provided', () => {
        const { container } = render(ButtonTestWrapper, {
            props: { label: 'Open', iconAfter: ChevronDown }
        });

        const children = Array.from(container.querySelector('button')?.children ?? []);
        const labelIndex = children.findIndex((el) => el.tagName === 'SPAN');
        const svgIndex = children.findIndex((el) => el.tagName === 'svg' || el.tagName === 'SVG');
        expect(labelIndex).toBeGreaterThan(-1);
        expect(svgIndex).toBeGreaterThan(labelIndex);
        expect(children[svgIndex]).toHaveClass('size-4');
    });

    it('renders both leading and trailing icons when both are provided', () => {
        const { container } = render(ButtonTestWrapper, {
            props: { label: 'Open', icon: Pencil, iconAfter: ChevronDown }
        });

        const svgs = container.querySelectorAll(iconSelector);
        expect(svgs.length).toBe(2);
    });

    it('merges iconAfterClass with the default size class on the trailing icon', () => {
        const { container } = render(ButtonTestWrapper, {
            props: { label: 'Open', iconAfter: ChevronDown, iconAfterClass: 'rotate-180' }
        });

        const svg = container.querySelector('button > svg:last-of-type');
        expect(svg?.getAttribute('class')).toContain('size-4');
        expect(svg?.getAttribute('class')).toContain('rotate-180');
    });

    it('applies the variant passed through to the underlying button', () => {
        const { container } = render(ButtonTestWrapper, {
            props: { label: 'Delete', variant: 'destructive' }
        });

        const button = container.querySelector('button');
        expect(button?.className).toContain('bg-destructive');
    });

    it('forwards buttonProps such as disabled and title to the button element', () => {
        const { container } = render(ButtonTestWrapper, {
            props: {
                label: 'Undo',
                buttonProps: { disabled: true, title: 'Cannot undo' }
            }
        });

        const button = container.querySelector('button');
        expect(button).toBeDisabled();
        expect(button).toHaveAttribute('title', 'Cannot undo');
    });

    it('merges the buttonProps class with the default classes', () => {
        const { container } = render(ButtonTestWrapper, {
            props: { label: 'Save', buttonProps: { class: 'custom-class' } }
        });

        const button = container.querySelector('button');
        expect(button?.className).toContain('custom-class');
        expect(button?.className).toContain('relative');
        expect(button?.className).toContain('items-center');
        expect(button?.className).toContain('gap-2');
    });

    it('invokes the onclick handler from buttonProps when clicked', async () => {
        const onclick = vi.fn();
        render(ButtonTestWrapper, {
            props: { label: 'Click me', buttonProps: { onclick } }
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Click me' }));
        expect(onclick).toHaveBeenCalledOnce();
    });

    it('does not apply a collapse class when collapseAt is "never"', () => {
        const { container } = render(ButtonTestWrapper, {
            props: { label: 'Edit', collapseAt: 'never' }
        });

        const span = container.querySelector(labelSelector);
        expect(span).toBeInTheDocument();
        expect(span?.className).not.toMatch(/max-\w+:(?:sr-only|hidden)/);
    });

    it.each([
        ['sm', 'max-sm:sr-only'],
        ['md', 'max-md:sr-only'],
        ['lg', 'max-lg:sr-only'],
        ['xl', 'max-xl:sr-only'],
        ['2xl', 'max-2xl:sr-only']
    ] as const)(
        'visually hides the label with sr-only at the %s breakpoint',
        (collapseAt, expected) => {
            const { container } = render(ButtonTestWrapper, {
                props: { label: 'Edit', collapseAt }
            });

            const span = container.querySelector(labelSelector);
            expect(span?.className).toContain(expected);
            expect(span?.className).not.toContain('max-' + collapseAt + ':hidden');
        }
    );

    describe('accessible name', () => {
        it('uses the visible children as the accessible name by default', () => {
            render(ButtonTestWrapper, { props: { label: 'Save changes', icon: Pencil } });

            expect(screen.getByRole('button', { name: 'Save changes' })).toBeInTheDocument();
        });

        it('forwards ariaLabel to the underlying button', () => {
            const { container } = render(ButtonTestWrapper, {
                props: { label: 'Save', ariaLabel: 'Save the document' }
            });

            expect(container.querySelector('button')).toHaveAttribute(
                'aria-label',
                'Save the document'
            );
        });

        it('requires ariaLabel on icon-only buttons to provide an accessible name', () => {
            render(ButtonTestWrapper, { props: { icon: Pencil, ariaLabel: 'Edit annotations' } });

            expect(screen.getByRole('button', { name: 'Edit annotations' })).toBeInTheDocument();
        });

        it('keeps the label in the accessibility tree even when visually collapsed', () => {
            render(ButtonTestWrapper, {
                props: { label: 'Edit annotations', icon: Pencil, collapseAt: 'md' }
            });

            expect(screen.getByRole('button', { name: 'Edit annotations' })).toBeInTheDocument();
        });
    });

    describe('isPending', () => {
        it('does not render the progress bar by default', () => {
            const { container } = render(ButtonTestWrapper, { props: { label: 'Save' } });

            expect(container.querySelector(progressSelector)).toBeNull();
        });

        it('renders a progress bar when isPending is true', () => {
            const { container } = render(ButtonTestWrapper, {
                props: { label: 'Save', isPending: true }
            });

            const progress = container.querySelector(progressSelector);
            expect(progress).toBeInTheDocument();
            expect(progress).toHaveAttribute('role', 'progressbar');
            expect(progress?.querySelector('.button-progress-indicator')).toBeInTheDocument();
        });

        it('disables the button when isPending is true', () => {
            const { container } = render(ButtonTestWrapper, {
                props: { label: 'Save', isPending: true }
            });

            expect(container.querySelector('button')).toBeDisabled();
        });

        it('keeps the icon and label visible while pending', () => {
            const { container } = render(ButtonTestWrapper, {
                props: { label: 'Save', icon: Pencil, isPending: true }
            });

            expect(container.querySelector(iconSelector)).toBeInTheDocument();
            const label = container.querySelector(labelSelector);
            expect(label).toHaveTextContent('Save');
            expect(label?.className).not.toContain('invisible');
            expect(label?.className).not.toContain('hidden');
        });

        it('keeps the button disabled even when buttonProps.disabled is false', () => {
            const { container } = render(ButtonTestWrapper, {
                props: { label: 'Save', isPending: true, buttonProps: { disabled: false } }
            });

            expect(container.querySelector('button')).toBeDisabled();
        });
    });
});
