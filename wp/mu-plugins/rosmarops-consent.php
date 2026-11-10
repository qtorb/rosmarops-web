<?php
/**
 * Plugin Name: RosmarOps consent
 * Description: Loads the same cookie banner as the static home pages (/assets/consent/). Google Analytics loads only after consent. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_CONSENT_VER = '5';
// Absolute URLs: on the Spanish site WordPress would otherwise prefix /es/.
const ROSMAROPS_CONSENT_BASE = 'https://rosmarops.com/assets/consent/';

add_action('wp_enqueue_scripts', function () {
	wp_enqueue_style('rosmarops-cc', ROSMAROPS_CONSENT_BASE . 'cookieconsent.css', [], '3.1.0');
	wp_enqueue_script('rosmarops-cc', ROSMAROPS_CONSENT_BASE . 'cookieconsent.umd.js', [], '3.1.0', true);
	wp_enqueue_script('rosmarops-consent', ROSMAROPS_CONSENT_BASE . 'consent.js', ['rosmarops-cc'], ROSMAROPS_CONSENT_VER, true);
});

/**
 * The footer paragraph of the blogs: privacy, legal notice and terms of the blog's language, then the cookie settings
 * link (GTM-130b, signed by Albert 10-11), separated by « · ». The theme's own footer is not touched.
 */
function rosmarops_consent_footer_html($locale) {
	$links = [
		'es' => [['/es/privacidad/', 'Privacidad'], ['/es/aviso-legal/', 'Aviso legal'], ['/es/terminos/', 'Términos'], 'Configurar cookies'],
		'ca' => [['/ca/privadesa/', 'Privadesa'], ['/ca/avis-legal/', 'Avís legal'], ['/ca/termes/', 'Termes'], 'Configura les galetes'],
		'en' => [['/privacy/', 'Privacy'], ['/legal-notice/', 'Legal notice'], ['/terms/', 'Terms'], 'Cookie settings'],
	];
	$set   = $links[substr((string) $locale, 0, 2)] ?? $links['en'];
	$parts = [];
	foreach (array_slice($set, 0, 3) as [$href, $text]) {
		$parts[] = '<a href="' . esc_attr($href) . '">' . esc_html($text) . '</a>';
	}
	$parts[] = '<a href="#" data-cc="show-preferencesModal">' . esc_html($set[3]) . '</a>';
	return '<p class="rosmarops-cc-link" style="text-align:center;font-size:14px;margin:16px 0">' . implode(' · ', $parts) . '</p>';
}

add_action('wp_footer', function () {
	echo rosmarops_consent_footer_html(get_locale());
}, 100);
