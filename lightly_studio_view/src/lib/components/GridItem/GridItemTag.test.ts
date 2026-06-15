import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import GridItemTag from './GridItemTag.svelte';
import * as useAuthModule from '$lib/hooks/useAuth/useAuth';

vi.mock('$lib/hooks/useAuth/useAuth');

const defaultProps = { isSelected: false };

describe('GridItemTag', () => {
    it('shows checkbox for unselected item when user has labeler role', () => {
        vi.mocked(useAuthModule.default).mockReturnValue({
            user: { role: 'labeler', email: 'labeler@example.com', username: 'labeler' },
            token: 'mock-token',
            isAuthenticated: true
        });

        render(GridItemTag, { props: defaultProps });

        expect(screen.getByTestId('grid-item-tag')).toBeInTheDocument();
        expect(screen.getByRole('checkbox')).not.toBeChecked();
    });

    it('shows checked checkbox for selected item when user has labeler role', () => {
        vi.mocked(useAuthModule.default).mockReturnValue({
            user: { role: 'labeler', email: 'labeler@example.com', username: 'labeler' },
            token: 'mock-token',
            isAuthenticated: true
        });

        render(GridItemTag, { props: { ...defaultProps, isSelected: true } });

        expect(screen.getByTestId('grid-item-tag')).toBeInTheDocument();
        expect(screen.getByRole('checkbox')).toBeChecked();
    });

    it('does not show checkbox for viewer role', () => {
        vi.mocked(useAuthModule.default).mockReturnValue({
            user: { role: 'viewer', email: 'viewer@example.com', username: 'viewer' },
            token: 'mock-token',
            isAuthenticated: true
        });

        render(GridItemTag, { props: defaultProps });

        expect(screen.queryByTestId('grid-item-tag')).not.toBeInTheDocument();
    });

    it('shows checkbox in OSS mode (no role)', () => {
        vi.mocked(useAuthModule.default).mockReturnValue({
            user: undefined,
            token: undefined,
            isAuthenticated: false
        });

        render(GridItemTag, { props: defaultProps });

        expect(screen.getByTestId('grid-item-tag')).toBeInTheDocument();
    });
});
