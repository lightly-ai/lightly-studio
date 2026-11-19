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
});
