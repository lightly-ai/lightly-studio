import { fireEvent, render, screen } from '@testing-library/svelte';
import type { ComponentProps } from 'svelte';
import { describe, expect, it, vi } from 'vitest';
import InstancePromptInput from './InstancePromptInput.svelte';

type Instances = ComponentProps<typeof InstancePromptInput>['instances'];

const makeInstances = (canGenerate: boolean) => ({
    canGenerate,
    isGenerating: false,
    generate: vi.fn()
});

const defaultProps = {
    prompt: 'cars',
    onPromptChange: vi.fn(),
    isDrawingBox: false,
    onDrawBoxChange: vi.fn()
};

const renderInput = (instances: ReturnType<typeof makeInstances>) =>
    render(InstancePromptInput, {
        props: {
            ...defaultProps,
            instances: instances as unknown as Instances
        }
    });

describe('InstancePromptInput', () => {
    it('finds instances on Enter but not while an input method composes', async () => {
        const instances = makeInstances(true);
        renderInput(instances);
        const input = screen.getByLabelText('Instance prompt');

        await fireEvent.keyDown(input, { key: 'Enter', isComposing: true });
        await fireEvent.keyDown(input, { key: 'Enter', keyCode: 229 });
        expect(instances.generate).not.toHaveBeenCalled();

        await fireEvent.keyDown(input, { key: 'Enter' });
        expect(instances.generate).toHaveBeenCalledOnce();
    });

    it('blocks finding instances when the hook cannot generate', async () => {
        const instances = makeInstances(false);
        renderInput(instances);

        await fireEvent.keyDown(screen.getByLabelText('Instance prompt'), { key: 'Enter' });
        expect(instances.generate).not.toHaveBeenCalled();
        expect(screen.getByRole('button', { name: 'Find instances' })).toBeDisabled();
    });
});
