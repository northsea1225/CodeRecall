import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';
import zhCN from './resources/zh-CN';
import enUS from './resources/en-US';

const LANGUAGE_STORAGE_KEY = 'cr-language';
const savedLanguage =
  typeof localStorage !== 'undefined'
    ? (localStorage.getItem(LANGUAGE_STORAGE_KEY) ?? 'zh-CN')
    : 'zh-CN';

void i18next.use(initReactI18next).init({
  lng: savedLanguage,
  fallbackLng: 'zh-CN',
  resources: {
    'zh-CN': { translation: zhCN },
    'en-US': { translation: enUS },
  },
  interpolation: { escapeValue: false },
});

export default i18next;
