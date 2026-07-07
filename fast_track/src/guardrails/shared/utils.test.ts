import { describe, expect, it } from 'vitest';
import { extractStdoutOrThrow } from './utils';

describe('extractStdoutOrThrow', () => {
    it('returns stdout when error has code 1 and string stdout', () => {
        const err = Object.assign(new Error(), { code: 1, stdout: 'output text' });
        expect(extractStdoutOrThrow(err)).toBe('output text');
    });

    it('re-throws when exit code is not 1', () => {
        const err = Object.assign(new Error('bad'), { code: 2, stdout: 'output' });
        expect(() => extractStdoutOrThrow(err)).toThrow(err);
    });

    it('re-throws when stdout is not a string', () => {
        const err = Object.assign(new Error(), { code: 1, stdout: 42 });
        expect(() => extractStdoutOrThrow(err)).toThrow(err);
    });

    it('re-throws when stdout is missing', () => {
        const err = Object.assign(new Error(), { code: 1 });
        expect(() => extractStdoutOrThrow(err)).toThrow(err);
    });

    it('re-throws a plain string error', () => {
        expect(() => extractStdoutOrThrow('oops')).toThrow('oops');
    });

    it('re-throws null', () => {
        expect(() => extractStdoutOrThrow(null)).toThrow();
    });
});
