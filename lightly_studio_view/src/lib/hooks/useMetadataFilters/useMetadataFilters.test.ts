import { describe, it, expect, vi } from 'vitest';
import { createMetadataFilters } from './useMetadataFilters';
import type { MetadataValues } from '$lib/services/loadMetadataInfo';

// Mock the session storage
vi.mock('$lib/hooks/useSessionStorage/useSessionStorage', () => ({
    useSessionStorage: vi.fn(() => ({
        subscribe: vi.fn(),
        set: vi.fn(),
        update: vi.fn()
    }))
}));

// Mock the svelte store
vi.mock('svelte/store', () => ({
    get: vi.fn((store) => {
        // Mock the metadataBounds store
        if (store && typeof store === 'object' && 'subscribe' in store) {
            return {
                temperature: { min: 0, max: 100 },
                humidity: { min: 0, max: 100 },
                pressure: { min: 900, max: 1100 }
            };
        }
        return {};
    }),
    writable: vi.fn(() => ({
        subscribe: vi.fn(),
        set: vi.fn(),
        update: vi.fn()
    }))
}));

describe('createMetadataFilters', () => {
    it('should create filters for metadata values that are not at full range', () => {
        const metadataValues: MetadataValues = {
            temperature: { min: 20, max: 80 }, // Not at full range
            humidity: { min: 0, max: 100 }, // At full range
            pressure: { min: 950, max: 1050 } // Not at full range
        };

        const filters = createMetadataFilters(metadataValues);

        expect(filters).toHaveLength(4); // 2 min filters + 2 max filters

        // Check temperature filters
        const tempMinFilter = filters.find((f) => f.key === 'temperature' && f.op === '>=');
        const tempMaxFilter = filters.find((f) => f.key === 'temperature' && f.op === '<=');
        expect(tempMinFilter).toEqual({ key: 'temperature', value: 20 as unknown, op: '>=' });
        expect(tempMaxFilter).toEqual({ key: 'temperature', value: 80 as unknown, op: '<=' });

        // Check pressure filters
        const pressureMinFilter = filters.find((f) => f.key === 'pressure' && f.op === '>=');
        const pressureMaxFilter = filters.find((f) => f.key === 'pressure' && f.op === '<=');
        expect(pressureMinFilter).toEqual({ key: 'pressure', value: 950 as unknown, op: '>=' });
        expect(pressureMaxFilter).toEqual({ key: 'pressure', value: 1050 as unknown, op: '<=' });

        // Humidity should not have filters since it's at full range
        const humidityFilters = filters.filter((f) => f.key === 'humidity');
        expect(humidityFilters).toHaveLength(0);
    });

    it('should not create filters when metadata values are at full range', () => {
        const metadataValues: MetadataValues = {
            temperature: { min: 0, max: 100 }, // At full range
            humidity: { min: 0, max: 100 } // At full range
        };

        const filters = createMetadataFilters(metadataValues);

        expect(filters).toHaveLength(0);
    });

    it('should handle empty metadata values', () => {
        const metadataValues: MetadataValues = {};

        const filters = createMetadataFilters(metadataValues);

        expect(filters).toHaveLength(0);
    });

    it('should only create min filter when min is not at bound', () => {
        const metadataValues: MetadataValues = {
            temperature: { min: 20, max: 100 } // Only min is not at bound
        };

        const filters = createMetadataFilters(metadataValues);

        expect(filters).toHaveLength(1);
        expect(filters[0]).toEqual({ key: 'temperature', value: 20 as unknown, op: '>=' });
    });

    it('should only create max filter when max is not at bound', () => {
        const metadataValues: MetadataValues = {
            temperature: { min: 0, max: 80 } // Only max is not at bound
        };

        const filters = createMetadataFilters(metadataValues);

        expect(filters).toHaveLength(1);
        expect(filters[0]).toEqual({ key: 'temperature', value: 80 as unknown, op: '<=' });
    });
});
