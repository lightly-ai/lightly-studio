import { describe, it, expect } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import UserAvatar from './UserAvatar.svelte';

describe('UserAvatar', () => {
    const mockUser = {
        username: 'admin',
        email: 'admin@example.com',
        role: 'admin'
    };

    it('should render avatar button with user initial', () => {
        const { getByTitle } = render(UserAvatar, { props: { user: mockUser } });
        const avatarButton = getByTitle('admin');
        expect(avatarButton).toBeTruthy();
        expect(avatarButton.textContent).toContain('A');
    });

    it('should open popover when avatar is clicked', async () => {
        const { getByTitle, getByText } = render(UserAvatar, { props: { user: mockUser } });
        const avatarButton = getByTitle('admin');

        await fireEvent.click(avatarButton);

        expect(getByText('Signed in as')).toBeTruthy();
        expect(getByText('admin')).toBeTruthy();
    });

    it('should render sign out button in popover', async () => {
        const { getByTitle, getByRole } = render(UserAvatar, { props: { user: mockUser } });
        const avatarButton = getByTitle('admin');

        await fireEvent.click(avatarButton);

        const signOutButton = getByRole('button', { name: /sign out/i });
        expect(signOutButton).toBeTruthy();
    });
});
