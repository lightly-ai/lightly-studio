import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import DefinitionList from './DefinitionList.svelte';

describe('DefinitionList', () => {
    it('renders empty list', () => {
        const { container } = render(DefinitionList, {
            props: {
                items: []
            }
        });

        expect(container.querySelector('div')).toBeInTheDocument();
    });

    it('renders items with labels and values', () => {
        render(DefinitionList, {
            props: {
                items: [
                    { label: 'Name:', value: 'John Doe' },
                    { label: 'Age:', value: 30 },
                    { label: 'Email:', value: 'john@example.com' }
                ]
            }
        });

        expect(screen.getByText('Name:')).toBeInTheDocument();
        expect(screen.getByText('John Doe')).toBeInTheDocument();
        expect(screen.getByText('Age:')).toBeInTheDocument();
        expect(screen.getByText('30')).toBeInTheDocument();
        expect(screen.getByText('Email:')).toBeInTheDocument();
        expect(screen.getByText('john@example.com')).toBeInTheDocument();
    });

    it('renders null values as dash', () => {
        render(DefinitionList, {
            props: {
                items: [{ label: 'Value:', value: null }]
            }
        });

        expect(screen.getByText('Value:')).toBeInTheDocument();
        expect(screen.getByText('-')).toBeInTheDocument();
    });

    it('renders undefined values as dash', () => {
        render(DefinitionList, {
            props: {
                items: [{ label: 'Value:', value: undefined }]
            }
        });

        expect(screen.getByText('Value:')).toBeInTheDocument();
        expect(screen.getByText('-')).toBeInTheDocument();
    });

    it('adds test id when provided', () => {
        render(DefinitionList, {
            props: {
                items: [{ label: 'Name:', value: 'Test', testId: 'name-field' }]
            }
        });

        const valueElement = screen.getByTestId('name-field');
        expect(valueElement).toBeInTheDocument();
        expect(valueElement).toHaveTextContent('Test');
    });

    it('renders multiple items with test ids', () => {
        render(DefinitionList, {
            props: {
                items: [
                    { label: 'Width:', value: '1920px', testId: 'video-width' },
                    { label: 'Height:', value: '1080px', testId: 'video-height' },
                    { label: 'FPS:', value: '30' }
                ]
            }
        });

        expect(screen.getByTestId('video-width')).toHaveTextContent('1920px');
        expect(screen.getByTestId('video-height')).toHaveTextContent('1080px');
        expect(screen.getByText('30')).toBeInTheDocument();
    });
});
