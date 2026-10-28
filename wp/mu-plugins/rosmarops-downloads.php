<?php
/**
 * Plugin Name: RosmarOps downloads
 * Description: Download counter (GTM-18). /download, /es/descargar and /ca/descarregar add one to an aggregate count (UTC day, source page, language) and redirect to the latest release on GitHub. Stores no IP address, cookie, user agent or referrer. Public read-only totals at /wp-json/rosmarops/v1/downloads. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_DL_TARGET = 'https://github.com/qtorb/rosmarops/releases/latest';
const ROSMAROPS_DL_ROUTES = ['/download' => 'en', '/es/descargar' => 'es', '/ca/descarregar' => 'ca'];
const ROSMAROPS_DL_FROM   = [
	'home', 'faq', 'about',
	'observatory-claude-code', 'observatory-cursor', 'observatory-hermes-agent', 'observatory-kanvas',
	'blog-v040', 'blog-v030', 'blog-launch', 'blog-18of100',
];
const ROSMAROPS_DL_DAYS   = 400;

function rosmarops_dl_table() {
	global $wpdb;
	return $wpdb->base_prefix . 'rosmarops_downloads';
}

/** Language of a download route for a request URI, or null if it is not one. */
function rosmarops_dl_route_lang($request_uri) {
	$path = parse_url((string) $request_uri, PHP_URL_PATH);
	if (!is_string($path)) {
		return null;
	}
	$path = rtrim($path, '/');
	return ROSMAROPS_DL_ROUTES[$path] ?? null;
}

/** Source page from ?from=, limited to the closed list; anything else is "other". */
function rosmarops_dl_source($raw) {
	return (is_string($raw) && in_array($raw, ROSMAROPS_DL_FROM, true)) ? $raw : 'other';
}

function rosmarops_dl_create_table() {
	global $wpdb;
	$t = rosmarops_dl_table();
	$wpdb->query(
		"CREATE TABLE IF NOT EXISTS `$t` (
			day DATE NOT NULL,
			src VARCHAR(40) NOT NULL,
			lang CHAR(2) NOT NULL,
			count INT UNSIGNED NOT NULL DEFAULT 0,
			PRIMARY KEY (day, src, lang)
		) " . $wpdb->get_charset_collate()
	);
}

/** Adds one to (UTC day, source, language). Only this table is written. */
function rosmarops_dl_count($src, $lang, $day = null) {
	global $wpdb;
	$t   = rosmarops_dl_table();
	$day = $day ?? gmdate('Y-m-d');
	$sql = $wpdb->prepare(
		"INSERT INTO `$t` (day, src, lang, count) VALUES (%s, %s, %s, 1) ON DUPLICATE KEY UPDATE count = count + 1",
		$day,
		$src,
		$lang
	);
	$suppress = $wpdb->suppress_errors(true);
	$ok       = $wpdb->query($sql);
	if ($ok === false) {
		rosmarops_dl_create_table();
		$ok = $wpdb->query($sql);
	}
	$wpdb->suppress_errors($suppress);
	return $ok !== false;
}

/** Aggregate rows of the last ROSMAROPS_DL_DAYS days (UTC), oldest first. */
function rosmarops_dl_rows($today = null) {
	global $wpdb;
	$t     = rosmarops_dl_table();
	$today = $today ?? gmdate('Y-m-d');
	$since = gmdate('Y-m-d', strtotime($today . ' UTC') - (ROSMAROPS_DL_DAYS - 1) * 86400);
	$suppress = $wpdb->suppress_errors(true);
	$res      = $wpdb->get_results(
		$wpdb->prepare("SELECT day, src, lang, count FROM `$t` WHERE day >= %s ORDER BY day, src, lang", $since),
		ARRAY_A
	);
	$wpdb->suppress_errors($suppress);
	$rows = [];
	foreach ((array) $res as $r) {
		$rows[] = ['day' => $r['day'], 'from' => $r['src'], 'lang' => $r['lang'], 'count' => (int) $r['count']];
	}
	return $rows;
}

// Redirect + count, before WordPress resolves the request (no page, no 404).
add_action('muplugins_loaded', function () {
	$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
	$lang   = rosmarops_dl_route_lang($_SERVER['REQUEST_URI'] ?? '');
	if ($lang === null || ($method !== 'GET' && $method !== 'HEAD')) {
		return;
	}
	if ($method === 'GET') {
		rosmarops_dl_count(rosmarops_dl_source($_GET['from'] ?? null), $lang);
	}
	header('Cache-Control: no-store');
	header('Location: ' . ROSMAROPS_DL_TARGET, true, 302);
	exit;
});

// Public, read-only totals. Only GET is registered, so any other method gets no route.
add_action('rest_api_init', function () {
	register_rest_route('rosmarops/v1', '/downloads', [
		'methods'             => 'GET',
		'permission_callback' => '__return_true',
		'callback'            => function () {
			$res = new WP_REST_Response([
				'generated_at' => gmdate('Y-m-d\TH:i:s\Z'),
				'rows'         => rosmarops_dl_rows(),
			]);
			$res->header('Cache-Control', 'public, max-age=3600');
			return $res;
		},
	]);
});
