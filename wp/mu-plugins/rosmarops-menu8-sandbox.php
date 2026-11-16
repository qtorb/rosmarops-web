<?php
/**
 * Plugin Name: RosmarOps: «Sandbox» in the blog menu, after Observatory (one-time, per site)
 * Description: GTM-175 (asked by Albert, 16-11 17:18). Once per site (EN /, ES /es/, CA /ca/): adds a «Sandbox» custom link (/sandbox/, /es/sandbox/ or /ca/sandbox/) to the GeneratePress primary menu, at its top level, right after the item whose URL is the Observatory of that language, and moves the items after it one place down. menu7 skipped the three sites because the blog menu has no Methodology item; this one only needs the Observatory item. It is left alone and logged if an item already points to the section, or if the menu does not have exactly one top-level Observatory item. Touches nothing else. Idempotent: a per-site option marks it done, with a lock. The log (ids and positions only) goes to the option rosmarops_menu8_log and to wp-content/rosmarops-private/menu8-<lang>.log, which the deploy reads over SFTP; the deploy then removes this file from the server. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_MENU8_DONE = 'rosmarops_menu8_done';
const ROSMAROPS_MENU8_LOCK = 'rosmarops_menu8_lock';
const ROSMAROPS_MENU8_LOG  = 'rosmarops_menu8_log';

/** The plan for one site, by its home URL, or null for any other site. */
function rosmarops_menu8_plan($home_url) {
	$plans = [
		'https://rosmarops.com'    => ['lang' => 'en', 'observatory' => '/observatory', 'section' => '/sandbox/'],
		'https://rosmarops.com/es' => ['lang' => 'es', 'observatory' => '/es/observatorio', 'section' => '/es/sandbox/'],
		'https://rosmarops.com/ca' => ['lang' => 'ca', 'observatory' => '/ca/observatori', 'section' => '/ca/sandbox/'],
	];
	return $plans[rtrim((string) $home_url, '/')] ?? null;
}

/** Path of a menu item's URL, without the trailing slash, so «https://rosmarops.com/es/observatorio/» is «/es/observatorio». */
function rosmarops_menu8_path($url) {
	$path = parse_url((string) $url, PHP_URL_PATH);
	return is_string($path) ? rtrim($path, '/') : '';
}

/** Adds «Sandbox» after the Observatory item. Returns one log line. */
function rosmarops_menu8_menu($plan) {
	$locations = get_nav_menu_locations();
	$menu_id = (int) ($locations['primary'] ?? 0);
	if (!$menu_id) {
		return 'menu skipped: no menu in the primary location';
	}
	$items = wp_get_nav_menu_items($menu_id, ['post_status' => 'any']);
	if (!is_array($items) || !$items) {
		return "menu skipped: menu {$menu_id} has no items";
	}
	$obs = [];
	foreach ($items as $it) {
		$p = rosmarops_menu8_path($it->url);
		if ($p === rtrim($plan['section'], '/')) {
			return "menu skipped: item {$it->ID} already points to {$plan['section']}";
		}
		if ((int) $it->menu_item_parent === 0 && $p === $plan['observatory']) {
			$obs[] = $it;
		}
	}
	if (count($obs) !== 1) {
		return 'menu skipped: menu ' . $menu_id . ' has ' . count($obs) . " top-level items for {$plan['observatory']}/, 1 expected";
	}
	$after = (int) $obs[0]->menu_order;
	$pos = $after + 1;
	foreach ($items as $it) {
		if ((int) $it->menu_order > $after) {
			wp_update_post(['ID' => $it->ID, 'menu_order' => (int) $it->menu_order + 1]);
		}
	}
	$new = wp_update_nav_menu_item($menu_id, 0, [
		'menu-item-title'    => 'Sandbox',
		'menu-item-url'      => 'https://rosmarops.com' . $plan['section'],
		'menu-item-type'     => 'custom',
		'menu-item-status'   => 'publish',
		'menu-item-position' => $pos,
	]);
	if (is_wp_error($new) || !$new) {
		return "menu failed: could not add the item to menu {$menu_id}";
	}
	return "menu done: item {$new} «Sandbox» at position {$pos} of menu {$menu_id}, right after item {$obs[0]->ID}";
}

/** Runs once on this site. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_menu8_run() {
	$plan = rosmarops_menu8_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_MENU8_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_MENU8_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_MENU8_LOCK) < 600) {
			return null;
		}
		update_option(ROSMAROPS_MENU8_LOCK, time(), false);
	}
	$log = ['Sandbox in the blog menu after Observatory, site ' . $plan['lang'] . ', ' . gmdate('Y-m-d H:i:s') . ' UTC'];
	$log[] = rosmarops_menu8_menu($plan);
	update_option(ROSMAROPS_MENU8_LOG, $log, false);
	update_option(ROSMAROPS_MENU8_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_MENU8_LOCK);
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-menu8: cannot create ' . $dir);
		return $log;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . '/menu8-' . $plan['lang'] . '.log', implode("\n", $log) . "\n", FILE_APPEND);
	return $log;
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_menu8_run();
});
