import type { Component } from 'svelte';

export type NavigationMenuItem = {
    title: string;
    href: string;
    isSelected: boolean;
    icon?: Component;
    id: string;
    children?: NavigationMenuItem[];
};

export type BreadcrumbLevel = {
    selected: NavigationMenuItem;
    siblings: NavigationMenuItem[];
};
