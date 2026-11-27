import { render, screen } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { describe, it, expect } from 'vitest';
import AnnotationToolPopUp from './AnnotationToolPopUp.svelte';

const children = createRawSnippet(() => ({ render: () => '<div>Tool controls</div>' }));
const saveControls = createRawSnippet(() => ({ render: () => '<div>Save controls</div>' }));

describe('AnnotationToolPopUp', () => {
    it('shows the title, the tool controls and the save controls', () => {
        render(AnnotationToolPopUp, { props: { title: 'Smart select', children, saveControls } });

        expect(screen.getByRole('dialog', { name: 'Smart select' })).toBeInTheDocument();
        expect(screen.getByText('Tool controls')).toBeInTheDocument();
        expect(screen.getByText('Save controls')).toBeInTheDocument();
    });
});
