import { describe, it, expect } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import UserAvatar from './UserAvatar.svelte';

describe('UserAvatar', () => {
    const mockUser = {
        username: 'admin',
        email: 'admin@example.com',
        role: 'admin' as const
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

    it('should keep menu icons as direct children so gap-2 applies', async () => {
        const { getByTitle, getByRole } = render(UserAvatar, { props: { user: mockUser } });

        await fireEvent.click(getByTitle('admin'));

        // The button's `gap-2` only spaces the icon from the label while both are
        // its flex children; a wrapper around them collapses the spacing.
        expect(
            getByRole('button', { name: /sign out/i }).querySelector(':scope > svg')
        ).toBeInTheDocument();
        expect(
            getByRole('link', { name: /users/i }).querySelector(':scope > svg')
        ).toBeInTheDocument();
    });

    it('should render admin menu items for admin user', async () => {
        const { getByTitle, getByRole } = render(UserAvatar, { props: { user: mockUser } });
        const avatarButton = getByTitle('admin');

        await fireEvent.click(avatarButton);

        const usersButton = getByRole('link', { name: /users/i });
        expect(usersButton).toBeTruthy();
        expect(usersButton.getAttribute('href')).toBe('/workspace/users');

        const apiKeysButton = getByRole('link', { name: /api keys/i });
        expect(apiKeysButton.getAttribute('href')).toBe('/workspace/api-keys');
    });

    it('should not render users menu item for editor user', async () => {
        const editorUser = {
            username: 'editor',
            email: 'editor@example.com',
            role: 'editor' as const
        };
        const { getByTitle, queryByRole } = render(UserAvatar, { props: { user: editorUser } });
        const avatarButton = getByTitle('editor');

        await fireEvent.click(avatarButton);

        const usersButton = queryByRole('link', { name: /users/i });
        expect(usersButton).toBeNull();
    });

    it('should not render users menu item for labeler user', async () => {
        const labelerUser = {
            username: 'labeler',
            email: 'labeler@example.com',
            role: 'labeler' as const
        };
        const { getByTitle, queryByRole } = render(UserAvatar, { props: { user: labelerUser } });
        const avatarButton = getByTitle('labeler');

        await fireEvent.click(avatarButton);

        const usersButton = queryByRole('link', { name: /users/i });
        expect(usersButton).toBeNull();
    });

    it('should not render admin menu items for viewer user', async () => {
        const viewerUser = {
            username: 'viewer',
            email: 'viewer@example.com',
            role: 'viewer' as const
        };
        const { getByTitle, queryByRole } = render(UserAvatar, { props: { user: viewerUser } });
        const avatarButton = getByTitle('viewer');

        await fireEvent.click(avatarButton);

        const usersButton = queryByRole('link', { name: /users/i });
        expect(usersButton).toBeNull();
        expect(queryByRole('link', { name: /api keys/i })).toBeNull();
    });
});
