<?php
/**
 * Plugin Name: RosmarOps consent
 * Description: Loads the same cookie banner as the static home pages (/assets/consent/). Google Analytics loads only after consent. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_CONSENT_VER = '1';

add_action('wp_enqueue_scripts', function () {
	wp_enqueue_style('rosmarops-cc', '/assets/consent/cookieconsent.css', [], '3.1.0');
	wp_enqueue_script('rosmarops-cc', '/assets/consent/cookieconsent.umd.js', [], '3.1.0', true);
	wp_enqueue_script('rosmarops-consent', '/assets/consent/consent.js', ['rosmarops-cc'], ROSMAROPS_CONSENT_VER, true);
});

add_action('wp_footer', function () {
	$es = strpos(get_locale(), 'es') === 0;
	echo '<p class="rosmarops-cc-link" style="text-align:center;font-size:14px;margin:16px 0">'
		. '<a href="#" data-cc="show-preferencesModal">'
		. esc_html($es ? 'Configurar cookies' : 'Cookie settings')
		. '</a></p>';
}, 100);
