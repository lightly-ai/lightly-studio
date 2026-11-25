import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import SceneUpdateFileFields from './SceneUpdateFileFields.svelte';

const defaultProps = {
    topic: '/perception/detections_3d',
    suffix: '_labeled',
    onTopicChange: vi.fn(),
    onSuffixChange: vi.fn()
};

describe('SceneUpdateFileFields', () => {
    it('shows the topic, the suffix, and the resulting file name ending', () => {
        render(SceneUpdateFileFields, { props: defaultProps });
        expect(screen.getByTestId('scene-update-topic-input')).toHaveValue(
            '/perception/detections_3d'
        );
        expect(screen.getByTestId('scene-update-suffix-input')).toHaveValue('_labeled');
        expect(
            screen.getByText(
                'Each file is named after its recording with _labeled.mcap at the end.'
            )
        ).toBeInTheDocument();
    });

    it('explains an empty topic and an invalid suffix', () => {
        render(SceneUpdateFileFields, { props: { ...defaultProps, topic: '', suffix: '_x/y' } });
        expect(screen.getByText('Enter a topic.')).toBeInTheDocument();
        expect(
            screen.getByText("The suffix can only contain letters, digits, '_', '.' and '-'.")
        ).toBeInTheDocument();
    });
});
