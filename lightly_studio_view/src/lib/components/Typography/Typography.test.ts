import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import TypographyTestWrapper from './TypographyTestWrapper.test.svelte';

describe('Typography', () => {
    it('should render default body1 variant', () => {
        const { container } = render(TypographyTestWrapper, { props: {} });
        const element = container.querySelector('p');
        expect(element).toBeTruthy();
        expect(element?.className).toContain('text-base');
        expect(element?.className).toContain('leading-normal');
    });

    it('should render h1 variant with h1 element', () => {
        const { container } = render(TypographyTestWrapper, { props: { variant: 'h1' } });
        const element = container.querySelector('h1');
        expect(element).toBeTruthy();
        expect(element?.className).toContain('text-4xl');
        expect(element?.className).toContain('font-bold');
    });

    it('should render h2 variant with h2 element', () => {
        const { container } = render(TypographyTestWrapper, { props: { variant: 'h2' } });
        const element = container.querySelector('h2');
        expect(element).toBeTruthy();
        expect(element?.className).toContain('text-3xl');
        expect(element?.className).toContain('font-semibold');
    });

    it('should render h3 variant with h3 element', () => {
        const { container } = render(TypographyTestWrapper, { props: { variant: 'h3' } });
        const element = container.querySelector('h3');
        expect(element).toBeTruthy();
        expect(element?.className).toContain('text-2xl');
    });

    it('should render caption variant with span element', () => {
        const { container } = render(TypographyTestWrapper, { props: { variant: 'caption' } });
        const element = container.querySelector('span');
        expect(element).toBeTruthy();
        expect(element?.className).toContain('text-xs');
    });

    it('should render overline variant with span element', () => {
        const { container } = render(TypographyTestWrapper, { props: { variant: 'overline' } });
        const element = container.querySelector('span');
        expect(element).toBeTruthy();
        expect(element?.className).toContain('text-xs');
        expect(element?.className).toContain('uppercase');
    });

    it('should override default component type', () => {
        const { container } = render(TypographyTestWrapper, {
            props: { variant: 'h1', component: 'div' }
        });
        const element = container.querySelector('div');
        expect(element).toBeTruthy();
        expect(element?.className).toContain('text-4xl');
    });

    it('should apply custom className', () => {
        const { container } = render(TypographyTestWrapper, {
            props: { className: 'custom-class' }
        });
        const element = container.querySelector('p');
        expect(element?.className).toContain('custom-class');
    });

    it('should render body2 variant', () => {
        const { container } = render(TypographyTestWrapper, { props: { variant: 'body2' } });
        const element = container.querySelector('p');
        expect(element).toBeTruthy();
        expect(element?.className).toContain('text-sm');
    });

    it('should render subtitle1 variant', () => {
        const { container } = render(TypographyTestWrapper, { props: { variant: 'subtitle1' } });
        const element = container.querySelector('p');
        expect(element).toBeTruthy();
        expect(element?.className).toContain('text-base');
        expect(element?.className).toContain('font-medium');
    });

    it('should render subtitle2 variant', () => {
        const { container } = render(TypographyTestWrapper, { props: { variant: 'subtitle2' } });
        const element = container.querySelector('p');
        expect(element).toBeTruthy();
        expect(element?.className).toContain('text-sm');
        expect(element?.className).toContain('font-medium');
    });

    it('should pass through additional props', () => {
        const { container } = render(TypographyTestWrapper, {
            props: { props: { 'data-testid': 'custom-typography' } }
        });
        const element = container.querySelector('[data-testid="custom-typography"]');
        expect(element).toBeTruthy();
    });
});
