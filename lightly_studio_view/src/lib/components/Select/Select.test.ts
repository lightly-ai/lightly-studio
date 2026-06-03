import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { Crosshair, Target } from '@lucide/svelte';
import '@testing-library/jest-dom';
import Select, { type SelectItem } from './Select.svelte';

// bits-ui Select uses pointer-capture and scrollIntoView APIs that jsdom doesn't implement.
const originalHasPointerCapture = Element.prototype.hasPointerCapture;
const originalSetPointerCapture = Element.prototype.setPointerCapture;
const originalReleasePointerCapture = Element.prototype.releasePointerCapture;
const originalScrollIntoView = Element.prototype.scrollIntoView;

beforeAll(() => {
    Element.prototype.hasPointerCapture = vi.fn(() => false);
    Element.prototype.setPointerCapture = vi.fn();
    Element.prototype.releasePointerCapture = vi.fn();
    Element.prototype.scrollIntoView = vi.fn();
});

afterAll(() => {
    Element.prototype.hasPointerCapture = originalHasPointerCapture;
    Element.prototype.setPointerCapture = originalSetPointerCapture;
    Element.prototype.releasePointerCapture = originalReleasePointerCapture;
    Element.prototype.scrollIntoView = originalScrollIntoView;
});

const ITEMS: SelectItem[] = [
    { value: 'accuracy', label: 'Accuracy' },
    { value: 'precision', label: 'Precision' },
    { value: 'recall', label: 'Recall' }
];

const ITEMS_WITH_ICONS: SelectItem[] = [
    { value: 'accuracy', label: 'Accuracy', icon: Target },
    { value: 'precision', label: 'Precision', icon: Crosshair },
    { value: 'recall', label: 'Recall' }
];

const triggerSelector = 'button[data-select-trigger]';

describe('Select', () => {
    it('renders the placeholder when no value is selected', () => {
        const { container } = render(Select, {
            props: { items: ITEMS, placeholder: 'Pick a metric' }
        });

        const trigger = container.querySelector(triggerSelector);
        expect(trigger).toBeInTheDocument();
        expect(trigger).toHaveTextContent('Pick a metric');
    });

    it('renders the matching item label when a value is selected', () => {
        const { container } = render(Select, {
            props: { items: ITEMS, value: 'precision' }
        });

        expect(container.querySelector(triggerSelector)).toHaveTextContent('Precision');
    });

    it('falls back to the raw value when no matching item exists', () => {
        const { container } = render(Select, {
            props: { items: ITEMS, value: 'unknown' }
        });

        expect(container.querySelector(triggerSelector)).toHaveTextContent('unknown');
    });

    it('forwards the testId to the trigger element', () => {
        const { container } = render(Select, {
            props: { items: ITEMS, testId: 'metric-select' }
        });

        expect(container.querySelector(triggerSelector)).toHaveAttribute(
            'data-testid',
            'metric-select'
        );
    });

    it('disables the trigger when disabled is true', () => {
        const { container } = render(Select, {
            props: { items: ITEMS, disabled: true }
        });

        expect(container.querySelector(triggerSelector)).toBeDisabled();
    });

    it('merges custom class names with the default classes', () => {
        const { container } = render(Select, {
            props: { items: ITEMS, class: 'custom-class' }
        });

        const trigger = container.querySelector(triggerSelector);
        expect(trigger?.className).toContain('custom-class');
    });

    describe('icon', () => {
        it('renders the selected item icon in the trigger', () => {
            const { container } = render(Select, {
                props: { items: ITEMS_WITH_ICONS, value: 'accuracy' }
            });

            const icon = container.querySelector(`${triggerSelector} > svg`);
            expect(icon).toBeInTheDocument();
            expect(icon).toHaveClass('size-4');
        });

        it('renders an icon matching the selected value when multiple items have icons', () => {
            const { container } = render(Select, {
                props: { items: ITEMS_WITH_ICONS, value: 'precision' }
            });

            const icon = container.querySelector(`${triggerSelector} > svg`);
            expect(icon).toBeInTheDocument();
            // Lucide adds a `lucide-<name>` class so we can assert which icon mounted
            expect(icon?.getAttribute('class')).toContain('lucide-crosshair');
        });

        it.each([
            ['sm', 'size-3.5'],
            ['md', 'size-4'],
            ['lg', 'size-5']
        ] as const)('scales the trigger icon to %s', (size, sizeClass) => {
            const { container } = render(Select, {
                props: { items: ITEMS_WITH_ICONS, value: 'accuracy', size }
            });

            const icon = container.querySelector(`${triggerSelector} > svg`);
            expect(icon).toBeInTheDocument();
            expect(icon?.getAttribute('class')).toContain(sizeClass);
        });

        it.each([
            ['sm', 'size-3.5'],
            ['md', 'size-4'],
            ['lg', 'size-5']
        ] as const)('scales dropdown item icons to %s', (size, sizeClass) => {
            const { baseElement } = render(Select, {
                props: { items: ITEMS_WITH_ICONS, size, open: true }
            });

            const itemIcons = baseElement.querySelectorAll('[data-select-item] > svg');
            expect(itemIcons.length).toBeGreaterThan(0);
            itemIcons.forEach((icon) => {
                expect(icon.getAttribute('class')).toContain(sizeClass);
            });
        });
    });

    describe('size', () => {
        it('defaults to md (h-10)', () => {
            const { container } = render(Select, { props: { items: ITEMS } });

            const trigger = container.querySelector(triggerSelector);
            expect(trigger?.className).toContain('h-10');
            expect(trigger?.className).toContain('text-sm');
        });

        it.each([
            ['sm', 'h-9', 'text-xs'],
            ['md', 'h-10', 'text-sm'],
            ['lg', 'h-11', 'text-base']
        ] as const)(
            'applies the %s size classes to the trigger',
            (size, heightClass, textClass) => {
                const { container } = render(Select, {
                    props: { items: ITEMS, size }
                });

                const trigger = container.querySelector(triggerSelector);
                expect(trigger?.className).toContain(heightClass);
                expect(trigger?.className).toContain(textClass);
            }
        );

        it.each([
            ['sm', 'py-1', 'text-xs'],
            ['md', 'py-1.5', 'text-sm'],
            ['lg', 'py-2', 'text-base']
        ] as const)(
            'applies the %s size classes to dropdown items',
            (size, paddingClass, textClass) => {
                const { baseElement } = render(Select, {
                    props: { items: ITEMS, size, open: true }
                });

                const items = baseElement.querySelectorAll('[data-select-item]');
                expect(items.length).toBe(ITEMS.length);
                items.forEach((item) => {
                    expect(item.className).toContain(paddingClass);
                    expect(item.className).toContain(textClass);
                });
            }
        );
    });
});
