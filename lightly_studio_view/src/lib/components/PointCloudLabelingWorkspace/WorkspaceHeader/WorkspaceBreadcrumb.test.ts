import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import WorkspaceBreadcrumb from './WorkspaceBreadcrumb.svelte';

describe('WorkspaceBreadcrumb', () => {
    it('makes a crumb marked reload do a full page load and leaves the others client-side', () => {
        render(WorkspaceBreadcrumb, {
            props: {
                sequenceId: 'sequence-1',
                sourcePath: [
                    { label: 'Home', href: '/workspace/projects', reload: true },
                    { label: 'Collection 1', href: '/datasets/d/mcap/c' },
                    { label: 'drive.mcap' }
                ]
            }
        });

        expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('data-sveltekit-reload');
        expect(screen.getByRole('link', { name: 'Collection 1' })).not.toHaveAttribute(
            'data-sveltekit-reload'
        );
    });

    it('dims a crumb without a link and marks only the last crumb as the current page', () => {
        render(WorkspaceBreadcrumb, {
            props: {
                sequenceId: 'sequence-1',
                sourcePath: [{ label: 'Home' }, { label: 'Collection 1' }, { label: 'drive.mcap' }]
            }
        });

        expect(screen.queryAllByRole('link', { name: /Home|Collection 1/ })).toHaveLength(0);
        const home = screen.getByText('Home').parentElement!;
        expect(home).toHaveAttribute('aria-disabled', 'true');
        expect(home).not.toHaveAttribute('aria-current');
        expect(home).toHaveClass('cursor-default');
        expect(screen.getByText('drive.mcap').parentElement).toHaveAttribute(
            'aria-current',
            'page'
        );
    });
});
