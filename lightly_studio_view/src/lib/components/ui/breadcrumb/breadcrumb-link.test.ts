import { render, screen } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { describe, expect, it } from 'vitest';
import BreadcrumbLink from './breadcrumb-link.svelte';

const label = createRawSnippet(() => ({ render: () => '<span>Home</span>' }));

describe('BreadcrumbLink', () => {
    it('renders a hoverable link when it has an href', () => {
        render(BreadcrumbLink, { props: { href: '/datasets/d', children: label } });

        const link = screen.getByRole('link', { name: 'Home' });
        expect(link).toHaveAttribute('href', '/datasets/d');
        expect(link).toHaveClass('hover:text-foreground');
    });

    it('renders dimmed, non-interactive text when it has no href', () => {
        render(BreadcrumbLink, { props: { children: label } });

        expect(screen.queryByRole('link')).toBeNull();
        const crumb = screen.getByText('Home').parentElement!;
        expect(crumb).not.toHaveAttribute('href');
        expect(crumb).toHaveAttribute('aria-disabled', 'true');
        expect(crumb).not.toHaveAttribute('aria-current');
        expect(crumb).toHaveClass('cursor-default');
        expect(crumb).not.toHaveClass('hover:text-foreground');
    });
});
