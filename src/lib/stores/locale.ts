import { writable, derived } from 'svelte/store';
import i18next from 'i18next';

export const locale = writable(localStorage.getItem('locale') || 'en-GB');

export const i18n = derived(
	locale,
	($locale, set) => {
		i18next.changeLanguage($locale).then(() => {
			localStorage.setItem('locale', $locale);
			set(i18next);
		});
	},
	i18next
);
