<?php
/**
 * Plugin Name: RosmarOps: «Academy» in the blog menu, after Sandbox (one-time, per site, only once Academy is open)
 * Description: GTM-230 (signed by Albert with block 214, 27-11). Does nothing while ROSMAROPS_MENU10_OPEN is false: that line is written by observatory/academy.py from the RosmarOps Academy switch ("open" in observatory/data/academy.json), so the blog menu changes in the same deploy that opens Academy. Then, once per site (EN /, ES /es/, CA /ca/): adds an «Academy» custom link (/academy/, /es/academy/ or /ca/academy/) to the GeneratePress primary menu, at its top level, right after the Sandbox item, and moves the items after it one place down. It acts only on the menu as it is today (27-11): exactly seven top-level items, the fourth of them Sandbox right after the Observatory, and no item pointing to Academy. Otherwise it is left alone and logged. Touches nothing else. Idempotent: a per-site option marks it done, with a lock. The log (ids and positions only) goes to the option rosmarops_menu10_log and to wp-content/rosmarops-private/menu10-<lang>.log, which the deploy reads over SFTP; the deploy then removes this file from the server. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

// Written by observatory/academy.py from observatory/data/academy.json; do not change it by hand.
const ROSMAROPS_MENU10_OPEN = true;
const ROSMAROPS_MENU10_DONE = 'rosmarops_menu10_done';
const ROSMAROPS_MENU10_LOCK = 'rosmarops_menu10_lock';
const ROSMAROPS_MENU10_LOG  = 'rosmarops_menu10_log';

/** The plan for one site, by its home URL, or null for any other site. */
function rosmarops_menu10_plan($home_url) {
	$plans = [
		'https://rosmarops.com'    => ['lang' => 'en', 'observatory' => '/observatory', 'sandbox' => '/sandbox', 'academy' => '/academy/'],
		'https://rosmarops.com/es' => ['lang' => 'es', 'observatory' => '/es/observatorio', 'sandbox' => '/es/sandbox', 'academy' => '/es/academy/'],
		'https://rosmarops.com/ca' => ['lang' => 'ca', 'observatory' => '/ca/observatori', 'sandbox' => '/ca/sandbox', 'academy' => '/ca/academy/'],
	];
	return $plans[rtrim((string) $home_url, '/')] ?? null;
}

/** Path of a menu item's URL, without the trailing slash. */
function rosmarops_menu10_path($url) {
	$path = parse_url((string) $url, PHP_URL_PATH);
	return is_string($path) ? rtrim($path, '/') : '';
}

/** Adds «Academy» after the Sandbox item. Returns one log line. */
function rosmarops_menu10_menu($plan) {
	$locations = get_nav_menu_locations();
	$menu_id = (int) ($locations['primary'] ?? 0);
	if (!$menu_id) {
		return 'menu skipped: no menu in the primary location';
	}
	$items = wp_get_nav_menu_items($menu_id, ['post_status' => 'any']);
	if (!is_array($items) || !$items) {
		return "menu skipped: menu {$menu_id} has no items";
	}
	$top = [];
	foreach ($items as $it) {
		if (rosmarops_menu10_path($it->url) === rtrim($plan['academy'], '/')) {
			return "menu skipped: item {$it->ID} already points to {$plan['academy']}";
		}
		if ((int) $it->menu_item_parent === 0) {
			$top[] = $it;
		}
	}
	// The menu of today: Blog, About, Observatory, Sandbox, the product, two languages.
	if (count($top) !== 7 || rosmarops_menu10_path($top[2]->url) !== $plan['observatory'] || rosmarops_menu10_path($top[3]->url) !== $plan['sandbox']) {
		$paths = array_map(function ($it) { return rosmarops_menu10_path($it->url); }, $top);
		return "menu skipped: menu {$menu_id} is not the menu of 27-11 (top level: " . implode(', ', $paths) . ')';
	}
	$sandbox = $top[3];
	$new = wp_update_nav_menu_item($menu_id, 0, [
		'menu-item-title'  => 'Academy',
		'menu-item-url'    => 'https://rosmarops.com' . $plan['academy'],
		'menu-item-type'   => 'custom',
		'menu-item-status' => 'publish',
	]);
	if (is_wp_error($new) || !$new) {
		return "menu failed: could not add the item to menu {$menu_id}";
	}
	// As menu8: the new order is written for every item, from the display order.
	$seq = [];
	foreach ($items as $it) {
		$seq[] = (int) $it->ID;
		if ((int) $it->ID === (int) $sandbox->ID) {
			$seq[] = (int) $new;
		}
	}
	foreach ($seq as $i => $id) {
		wp_update_post(['ID' => $id, 'menu_order' => $i + 1]);
	}
	$pos = array_search((int) $new, $seq, true) + 1;
	return "menu done: item {$new} «Academy» at position {$pos} of menu {$menu_id}, right after item {$sandbox->ID}";
}

/** Runs once on this site, once Academy is open. Returns the log lines (also stored), or null when there is nothing to run. */
function rosmarops_menu10_run() {
	if (!ROSMAROPS_MENU10_OPEN) {
		return null;
	}
	$plan = rosmarops_menu10_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_MENU10_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_MENU10_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_MENU10_LOCK) < 600) {
			return null;
		}
		update_option(ROSMAROPS_MENU10_LOCK, time(), false);
	}
	$log = ['Academy in the blog menu after Sandbox, site ' . $plan['lang'] . ', ' . gmdate('Y-m-d H:i:s') . ' UTC'];
	$log[] = rosmarops_menu10_menu($plan);
	update_option(ROSMAROPS_MENU10_LOG, $log, false);
	update_option(ROSMAROPS_MENU10_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_MENU10_LOCK);
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-menu10: cannot create ' . $dir);
		return $log;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . '/menu10-' . $plan['lang'] . '.log', implode("\n", $log) . "\n", FILE_APPEND);
	return $log;
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_menu10_run();
});
