/**
 * Turbo colormap — polynomial approximation by Anton Mikhailov (Google).
 * Maps a scalar in [0, 1] to RGB in [0, 1], written directly into `out` at `offset`.
 *
 * Writes three consecutive floats (R, G, B) starting at `out[offset]`.
 */
export function turboInto(value: number, out: Float32Array, offset: number): void {
    const x = Math.max(0, Math.min(1, value));
    out[offset] = Math.max(
        0,
        Math.min(
            1,
            0.13572138 +
                x *
                    (4.6153926 +
                        x *
                            (-42.66032258 +
                                x * (132.13108234 + x * (-152.94239396 + x * 59.28637943))))
        )
    );
    out[offset + 1] = Math.max(
        0,
        Math.min(
            1,
            0.09140261 +
                x *
                    (2.19418839 +
                        x * (4.84296658 + x * (-14.18503333 + x * (4.27729857 + x * 2.82956604))))
        )
    );
    out[offset + 2] = Math.max(
        0,
        Math.min(
            1,
            0.1066733 +
                x *
                    (12.64194608 +
                        x *
                            (-60.58204836 +
                                x * (110.36276771 + x * (-89.90310912 + x * 27.34824973))))
        )
    );
}
