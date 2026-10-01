import { locale } from './locale';

export const formatFloat = (num: number, maxDigits = 3, minDigits = 0): string => {
    return new Intl.NumberFormat(locale, {
        maximumFractionDigits: maxDigits,
        minimumFractionDigits: minDigits
    })
        .format(num)
        .toString();
};

export const formatFloat2 = (num: number): string => {
    return formatFloat(num, 2);
};
