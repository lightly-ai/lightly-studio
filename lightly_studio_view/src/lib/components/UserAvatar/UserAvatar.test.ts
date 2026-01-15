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

    it('should render users menu item for admin user', async () => {
        const { getByTitle, getByRole } = render(UserAvatar, { props: { user: mockUser } });
        const avatarButton = getByTitle('admin');

        await fireEvent.click(avatarButton);

        const usersButton = getByRole('link', { name: /users/i });
        expect(usersButton).toBeTruthy();
        expect(usersButton.getAttribute('href')).toBe('/workspace/users');
    });

    it('should not render users menu item for non-admin user', async () => {
        const nonAdminUser = {
            username: 'user',
            email: 'user@example.com',
            role: 'user'
        };
        const { getByTitle, queryByRole } = render(UserAvatar, { props: { user: nonAdminUser } });
        const avatarButton = getByTitle('user');

        await fireEvent.click(avatarButton);

        const usersButton = queryByRole('link', { name: /users/i });
        expect(usersButton).toBeNull();
    });
});
