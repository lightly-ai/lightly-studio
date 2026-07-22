import { locale } from './locale';

export const formatInteger = (num: number): string => {
    return new Intl.NumberFormat(locale, {}).format(num).toString();
};
