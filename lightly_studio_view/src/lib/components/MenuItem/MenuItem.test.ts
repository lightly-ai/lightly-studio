import { describe, it, expect, beforeAll, afterAll, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { Image, Video } from '@lucide/svelte';
import '@testing-library/jest-dom';
import MenuItem from './MenuItem.svelte';
import type { NavigationMenuItem } from '../NavigationMenu/types';

const goto = vi.fn();
vi.mock('$app/navigation', () => ({
    goto: (...args: unknown[]) => goto(...args)
}));

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

beforeEach(() => {
    goto.mockClear();
});

const imagesItem: NavigationMenuItem = {
    title: 'Images',
    id: 'image-1',
    href: '/images',
    isSelected: true,
    icon: Image
};

const videosItem: NavigationMenuItem = {
    title: 'Videos',
    id: 'video-1',
    href: '/videos',
    isSelected: false,
    icon: Video
};

describe('MenuItem', () => {
    describe('without siblings', () => {
        it('renders the item as a link button with the item href', () => {
            const { container } = render(MenuItem, { props: { item: imagesItem } });

            const link = container.querySelector('a');
            expect(link).toBeInTheDocument();
            expect(link).toHaveAttribute('href', '/images');
            expect(link).toHaveAttribute('data-testid', 'navigation-menu-images');
            expect(link).toHaveTextContent('Images');
        });
    });

    describe('with siblings', () => {
        const siblings: NavigationMenuItem[] = [imagesItem, videosItem];

        it('renders a Select trigger instead of a link', () => {
            render(MenuItem, { props: { item: imagesItem, siblings } });

            expect(screen.queryByRole('link')).toBeNull();

            const trigger = screen.getByTestId('navigation-menu-images');
            expect(trigger).toBeInTheDocument();
            expect(trigger).toHaveTextContent('Images');
        });

        it('keeps the trigger label fixed to the current item title', () => {
            render(MenuItem, { props: { item: videosItem, siblings } });

            const trigger = screen.getByTestId('navigation-menu-videos');
            expect(trigger).toHaveTextContent('Videos');
        });

        it('renders dropdown items with the sibling testIds when opened', async () => {
            const user = userEvent.setup();
            render(MenuItem, { props: { item: imagesItem, siblings } });

            await user.click(screen.getByTestId('navigation-menu-images'));

            const imagesOption = screen.getByTestId('navigation-dropdown-images');
            const videosOption = screen.getByTestId('navigation-dropdown-videos');
            expect(imagesOption).toHaveTextContent('Images');
            expect(videosOption).toHaveTextContent('Videos');
        });

        it('navigates to the sibling href when a dropdown item is selected', async () => {
            const user = userEvent.setup();
            render(MenuItem, { props: { item: imagesItem, siblings } });

            await user.click(screen.getByTestId('navigation-menu-images'));
            await user.click(screen.getByTestId('navigation-dropdown-videos'));

            expect(goto).toHaveBeenCalledExactlyOnceWith('/videos');
        });

        it('navigates to the current item href when the active item is reselected', async () => {
            const user = userEvent.setup();
            render(MenuItem, { props: { item: imagesItem, siblings } });

            await user.click(screen.getByTestId('navigation-menu-images'));
            await user.click(screen.getByTestId('navigation-dropdown-images'));

            expect(goto).toHaveBeenCalledExactlyOnceWith('/images');
        });
    });
});
