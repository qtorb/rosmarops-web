/*
 * rosmarops.com cookie consent.
 * Library: CookieConsent 3.1.0 by Orest Bida (MIT), served from this domain.
 * Google Analytics 4 loads only after the visitor accepts analytics cookies
 * (basic consent mode). Before that, this page contacts no third party.
 * Same file for the static home pages and both WordPress blogs.
 */
(function () {
  'use strict';
  if (!window.CookieConsent) return;

  var GA_ID = 'G-6RVHZ8ERGW';
  var lang = (document.documentElement.lang || 'en').slice(0, 2).toLowerCase() === 'es' ? 'es' : 'en';
  var privacy = lang === 'es'
    ? 'https://rosmarops.com/es/privacidad/'
    : 'https://rosmarops.com/privacy/';

  function loadGA() {
    if (window.__rosmaropsGA) return;
    window.__rosmaropsGA = true;
    window.dataLayer = window.dataLayer || [];
    function gtag() { window.dataLayer.push(arguments); }
    window.gtag = gtag;
    gtag('consent', 'default', {
      analytics_storage: 'granted',
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied'
    });
    gtag('js', new Date());
    gtag('config', GA_ID, {
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
      cookie_expires: 33696000 // 13 months
    });
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    document.head.appendChild(s);
  }

  function apply() {
    if (CookieConsent.acceptedCategory('analytics')) loadGA();
  }

  CookieConsent.run({
    cookie: { name: 'cc_cookie', path: '/', expiresAfterDays: 182, sameSite: 'Lax' },
    guiOptions: {
      consentModal: { layout: 'box', position: 'bottom right', equalWeightButtons: true, flipButtons: false },
      preferencesModal: { layout: 'box', equalWeightButtons: true, flipButtons: false }
    },
    categories: {
      necessary: { enabled: true, readOnly: true },
      analytics: {
        autoClear: { cookies: [{ name: /^_ga/ }], reloadPage: true }
      }
    },
    onConsent: apply,
    onChange: apply,
    language: {
      default: lang,
      translations: {
        en: {
          consentModal: {
            title: 'Analytics cookies',
            description: 'This website can use Google Analytics to count visits and see which pages are read. It only does so if you accept. You can change your mind at any time from "Cookie settings" at the bottom of the page. <a href="' + privacy + '">Privacy and cookies</a>',
            acceptAllBtn: 'Accept',
            acceptNecessaryBtn: 'Reject',
            showPreferencesBtn: 'Settings'
          },
          preferencesModal: {
            title: 'Cookie settings',
            acceptAllBtn: 'Accept all',
            acceptNecessaryBtn: 'Reject all',
            savePreferencesBtn: 'Save settings',
            closeIconLabel: 'Close',
            sections: [
              {
                title: 'Necessary',
                description: 'One cookie, cc_cookie, remembers your choice for six months. It is always on.',
                linkedCategory: 'necessary'
              },
              {
                title: 'Analytics',
                description: 'Google Analytics 4, from Google, counts visits and how pages are used. It sets the _ga cookies. Google signals and ad personalisation are off.',
                linkedCategory: 'analytics'
              },
              {
                title: 'More information',
                description: '<a href="' + privacy + '">Privacy and cookies</a>'
              }
            ]
          }
        },
        es: {
          consentModal: {
            title: 'Cookies de analítica',
            description: 'Esta web puede usar Google Analytics para contar visitas y ver qué páginas se leen. Solo lo hace si aceptas. Puedes cambiar de opinión cuando quieras desde «Configurar cookies», al final de la página. <a href="' + privacy + '">Privacidad y cookies</a>',
            acceptAllBtn: 'Aceptar',
            acceptNecessaryBtn: 'Rechazar',
            showPreferencesBtn: 'Configurar'
          },
          preferencesModal: {
            title: 'Configurar cookies',
            acceptAllBtn: 'Aceptar todas',
            acceptNecessaryBtn: 'Rechazar todas',
            savePreferencesBtn: 'Guardar',
            closeIconLabel: 'Cerrar',
            sections: [
              {
                title: 'Necesarias',
                description: 'Una cookie, cc_cookie, recuerda tu elección durante seis meses. Siempre está activa.',
                linkedCategory: 'necessary'
              },
              {
                title: 'Analítica',
                description: 'Google Analytics 4, de Google, cuenta las visitas y cómo se usan las páginas. Pone las cookies _ga. Las señales de Google y la personalización de anuncios están desactivadas.',
                linkedCategory: 'analytics'
              },
              {
                title: 'Más información',
                description: '<a href="' + privacy + '">Privacidad y cookies</a>'
              }
            ]
          }
        }
      }
    }
  });
})();
