import { describe, it, expect } from 'vitest';
import { getConstrainedCoordinates } from './getConstrainedCoordinates';
import type { BoundingBox } from '$lib/types';

describe('getConstrainedCoordinates', () => {
    const constraintBox: BoundingBox = {
        x: 0,
        y: 0,
        width: 100,
        height: 100
    };

    it('returns unchanged bbox when it fits within constraint box', () => {
        const newBbox: BoundingBox = {
            x: 10,
            y: 10,
            width: 20,
            height: 20
        };

        const result = getConstrainedCoordinates(newBbox, constraintBox);

        expect(result).toEqual(newBbox);
    });

    it('constrains x position when bbox is moved too far left', () => {
        const newBbox: BoundingBox = {
            x: -10,
            y: 10,
            width: 20,
            height: 20
        };

        const result = getConstrainedCoordinates(newBbox, constraintBox, true);

        expect(result).toEqual({
            x: 0,
            y: 10,
            width: 20,
            height: 20
        });
    });

    it('constrains y position when bbox is moved too far up', () => {
        const newBbox: BoundingBox = {
            x: 10,
            y: -5,
            width: 20,
            height: 20
        };

        const result = getConstrainedCoordinates(newBbox, constraintBox, true);

        expect(result).toEqual({
            x: 10,
            y: 0,
            width: 20,
            height: 20
        });
    });

    it('constrains x position when bbox extends too far right', () => {
        const newBbox: BoundingBox = {
            x: 90,
            y: 10,
            width: 20,
            height: 20
        };

        const result = getConstrainedCoordinates(newBbox, constraintBox, true);

        expect(result).toEqual({
            x: 80,
            y: 10,
            width: 20,
            height: 20
        });
    });

    it('constrains y position when bbox extends too far down', () => {
        const newBbox: BoundingBox = {
            x: 10,
            y: 90,
            width: 20,
            height: 20
        };

        const result = getConstrainedCoordinates(newBbox, constraintBox, true);

        expect(result).toEqual({
            x: 10,
            y: 80,
            width: 20,
            height: 20
        });
    });

    it('constrains width when bbox is too wide (resize mode)', () => {
        const newBbox: BoundingBox = {
            x: 10,
            y: 10,
            width: 150,
            height: 20
        };

        const result = getConstrainedCoordinates(newBbox, constraintBox, false);

        expect(result).toEqual({
            x: 10,
            y: 10,
            width: 90,
            height: 20
        });
    });

    it('constrains height when bbox is too tall (resize mode)', () => {
        const newBbox: BoundingBox = {
            x: 10,
            y: 10,
            width: 20,
            height: 150
        };

        const result = getConstrainedCoordinates(newBbox, constraintBox, false);

        expect(result).toEqual({
            x: 10,
            y: 10,
            width: 20,
            height: 90
        });
    });

    it('handles bbox that is both out of bounds and too large', () => {
        const newBbox: BoundingBox = {
            x: -10,
            y: -5,
            width: 150,
            height: 120
        };

        const result = getConstrainedCoordinates(newBbox, constraintBox);

        expect(result).toEqual({
            x: 0,
            y: 0,
            width: 100,
            height: 100
        });
    });

    it('handles constraint box with non-zero origin', () => {
        const offsetConstraintBox: BoundingBox = {
            x: 50,
            y: 25,
            width: 100,
            height: 75
        };

        const newBbox: BoundingBox = {
            x: 30,
            y: 10,
            width: 20,
            height: 20
        };

        const result = getConstrainedCoordinates(newBbox, offsetConstraintBox, true);

        expect(result).toEqual({
            x: 50,
            y: 25,
            width: 20,
            height: 20
        });
    });

    it('handles bbox extending beyond constraint box with offset', () => {
        const offsetConstraintBox: BoundingBox = {
            x: 50,
            y: 25,
            width: 100,
            height: 75
        };

        const newBbox: BoundingBox = {
            x: 140,
            y: 90,
            width: 20,
            height: 20
        };

        const result = getConstrainedCoordinates(newBbox, offsetConstraintBox, true);

        expect(result).toEqual({
            x: 130,
            y: 80,
            width: 20,
            height: 20
        });
    });
});
