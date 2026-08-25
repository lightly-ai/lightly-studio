import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import MetadataBalancingForm from './MetadataBalancingForm.svelte';

const defaultProps = {
    instanceId: 'test',
    params: {
        metadata_key: 'weather',
        target_distribution_mode: 'uniform' as const,
        target_distribution: [],
        strength: 1
    },
    metadataFieldNames: ['weather', 'city'],
    metadataValuesByKey: { weather: ['sunny', 'rainy'] },
    onUpdate: vi.fn()
};

describe('MetadataBalancingForm', () => {
    beforeEach(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('renders the metadata key select when field names are provided', () => {
        render(MetadataBalancingForm, { props: defaultProps });

        expect(screen.getByTestId('metadata-balancing-test-key')).toHaveTextContent('weather');
    });

    it('does not render the metadata key select when no field names are provided', () => {
        render(MetadataBalancingForm, {
            props: { ...defaultProps, metadataFieldNames: [] }
        });

        expect(screen.queryByTestId('metadata-balancing-test-key')).not.toBeInTheDocument();
    });

    it('calls onUpdate with the selected metadata key', async () => {
        const onUpdate = vi.fn();
        render(MetadataBalancingForm, { props: { ...defaultProps, onUpdate } });

        await fireEvent.keyDown(screen.getByTestId('metadata-balancing-test-key'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByText('city'));

        expect(onUpdate).toHaveBeenCalledWith({ metadata_key: 'city' });
    });

    it('hides the target distribution rows unless the mode is dictionary', () => {
        render(MetadataBalancingForm, { props: defaultProps });

        expect(screen.queryByTestId('metadata-balancing-test-add-row')).not.toBeInTheDocument();
    });

    it('shows the target distribution rows in dictionary mode', () => {
        render(MetadataBalancingForm, {
            props: {
                ...defaultProps,
                params: { ...defaultProps.params, target_distribution_mode: 'dictionary' as const }
            }
        });

        expect(screen.getByTestId('metadata-balancing-test-add-row')).toBeInTheDocument();
    });

    it('offers the values of the selected key as row options', async () => {
        render(MetadataBalancingForm, {
            props: {
                ...defaultProps,
                params: {
                    ...defaultProps.params,
                    target_distribution_mode: 'dictionary' as const,
                    target_distribution: [{ class_name: '', weight: 0 }]
                }
            }
        });

        await fireEvent.keyDown(screen.getByTestId('metadata-balancing-test-class-name-0'), {
            key: 'Enter'
        });

        expect(
            await screen.findByTestId('metadata-balancing-test-class-name-0-sunny')
        ).toBeInTheDocument();
        expect(
            screen.getByTestId('metadata-balancing-test-class-name-0-rainy')
        ).toBeInTheDocument();
    });

    it('offers no row options when the selected key has no known values', async () => {
        render(MetadataBalancingForm, {
            props: {
                ...defaultProps,
                params: {
                    ...defaultProps.params,
                    metadata_key: 'city',
                    target_distribution_mode: 'dictionary' as const,
                    target_distribution: [{ class_name: '', weight: 0 }]
                }
            }
        });

        await fireEvent.keyDown(screen.getByTestId('metadata-balancing-test-class-name-0'), {
            key: 'Enter'
        });

        expect(
            screen.queryByTestId('metadata-balancing-test-class-name-0-sunny')
        ).not.toBeInTheDocument();
    });

    it('renders the strength input with the current value', () => {
        render(MetadataBalancingForm, {
            props: { ...defaultProps, params: { ...defaultProps.params, strength: 2.5 } }
        });

        expect(screen.getByTestId('strategy-metadata-balancing-strength-input-test')).toHaveValue(
            2.5
        );
    });
});
