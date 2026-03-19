export const TYPOGRAPHY_VARIANTS = [
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'body1',
    'body2',
    'caption',
    'overline',
    'subtitle1',
    'subtitle2'
] as const;

export type TypographyVariant = (typeof TYPOGRAPHY_VARIANTS)[number];

export const COMPONENT_TYPES = [
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'p',
    'span',
    'div',
    'dt',
    'dd'
] as const;

export type ComponentType = (typeof COMPONENT_TYPES)[number];
