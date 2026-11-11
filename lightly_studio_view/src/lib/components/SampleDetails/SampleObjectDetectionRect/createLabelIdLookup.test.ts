import { describe, expect, it, vi } from 'vitest';
import { createLabelIdLookup } from './createLabelIdLookup';

const setup = (createLabel: (className: string) => Promise<string>) =>
    createLabelIdLookup({
        getLabels: async () => [{ annotation_label_name: 'cat', annotation_label_id: 'cat-id' }],
        createLabel
    });

describe('createLabelIdLookup', () => {
    it('finds an existing class without creating it', async () => {
        const createLabel = vi.fn();

        await expect(setup(createLabel)('cat')).resolves.toBe('cat-id');
        expect(createLabel).not.toHaveBeenCalled();
    });

    it('creates a new class once for two boxes drawn during the creation', async () => {
        let finish: (id: string) => void = () => {};
        const createLabel = vi.fn(() => new Promise<string>((resolve) => (finish = resolve)));
        const getLabelId = setup(createLabel);

        const first = getLabelId('dog');
        const second = getLabelId('dog');
        await vi.waitFor(() => expect(createLabel).toHaveBeenCalled());
        finish('dog-id');

        await expect(first).resolves.toBe('dog-id');
        await expect(second).resolves.toBe('dog-id');
        expect(createLabel).toHaveBeenCalledOnce();
    });

    it('tries again after a failed creation', async () => {
        const createLabel = vi
            .fn()
            .mockRejectedValueOnce(new Error('offline'))
            .mockResolvedValueOnce('dog-id');
        const getLabelId = setup(createLabel);

        await expect(getLabelId('dog')).rejects.toThrow('offline');

        await expect(getLabelId('dog')).resolves.toBe('dog-id');
    });
});
