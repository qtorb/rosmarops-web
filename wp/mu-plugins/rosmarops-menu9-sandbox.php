<?php
/**
 * Plugin Name: RosmarOps: the ES blog menu back in order, with «Sandbox» after Observatorio (one-time, /es/ only)
 * Description: GTM-175 (signed by Albert, 16-11). menu8 left the ES menu 317 as Blog, Sandbox, RosmarOps el producto, EN, CA, Acerca de, Observatorio: it shifted the display positions that WordPress returns (1..n) while the stored menu_order of Blog, Acerca de and Observatorio were other numbers. Once, on /es/ only: logs the stored menu_order of each top-level item, then sets menu_order 1-7 in this order: 1120 Blog, 1126 Acerca de, 1178 Observatorio, 1243 Sandbox, 1127 RosmarOps el producto, 1136 EN, 1169 CA. Changes no title, URL or parent; never touches EN or CA. It is left alone and logged if the primary menu is not 317 or its top level is not exactly those seven items. Idempotent: a per-site option marks it done, with a lock. The log (ids and orders only) goes to the option rosmarops_menu9_log and to wp-content/rosmarops-private/menu9-es.log, which the deploy reads over SFTP; the deploy then removes this file from the server. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_MENU9_DONE  = 'rosmarops_menu9_done';
const ROSMAROPS_MENU9_LOCK  = 'rosmarops_menu9_lock';
const ROSMAROPS_MENU9_LOG   = 'rosmarops_menu9_log';
const ROSMAROPS_MENU9_HOME  = 'https://rosmarops.com/es';
const ROSMAROPS_MENU9_MENU  = 317;
const ROSMAROPS_MENU9_ORDER = [1120, 1126, 1178, 1243, 1127, 1136, 1169];

/** Puts the ES menu in order. Returns the log lines after the header. */
function rosmarops_menu9_menu() {
	$locations = get_nav_menu_locations();
	$menu_id = (int) ($locations['primary'] ?? 0);
	if ($menu_id !== ROSMAROPS_MENU9_MENU) {
		return ["menu skipped: the primary menu is {$menu_id}, not " . ROSMAROPS_MENU9_MENU];
	}
	$items = wp_get_nav_menu_items($menu_id, ['post_status' => 'any']);
	$top = [];
	foreach (is_array($items) ? $items : [] as $it) {
		if ((int) $it->menu_item_parent === 0) {
			$top[] = (int) $it->ID;
		}
	}
	// The stored values, not the 1..n positions wp_get_nav_menu_items() hands back.
	$before = [];
	foreach ($top as $id) {
		$before[] = $id . '=' . (int) get_post_field('menu_order', $id);
	}
	$log = ['before (id=stored menu_order, in display order): ' . implode(', ', $before)];
	$want = ROSMAROPS_MENU9_ORDER;
	$a = $top;
	sort($a);
	sort($want);
	if ($a !== $want) {
		$log[] = 'menu skipped: the top level of menu ' . $menu_id . ' is not exactly ' . implode(', ', ROSMAROPS_MENU9_ORDER);
		return $log;
	}
	foreach (ROSMAROPS_MENU9_ORDER as $i => $id) {
		wp_update_post(['ID' => $id, 'menu_order' => $i + 1]);
	}
	$after = [];
	$ok = true;
	foreach (ROSMAROPS_MENU9_ORDER as $i => $id) {
		$o = (int) get_post_field('menu_order', $id);
		$after[] = $id . '=' . $o;
		$ok = $ok && $o === $i + 1;
	}
	$log[] = ($ok ? 'menu done: ' : 'menu failed: ') . 'after (id=menu_order): ' . implode(', ', $after);
	return $log;
}

/** Runs once on /es/. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_menu9_run() {
	if (rtrim((string) home_url(), '/') !== ROSMAROPS_MENU9_HOME || get_option(ROSMAROPS_MENU9_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_MENU9_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_MENU9_LOCK) < 600) {
			return null;
		}
		update_option(ROSMAROPS_MENU9_LOCK, time(), false);
	}
	$log = array_merge(['ES blog menu in order, site es, ' . gmdate('Y-m-d H:i:s') . ' UTC'], rosmarops_menu9_menu());
	update_option(ROSMAROPS_MENU9_LOG, $log, false);
	update_option(ROSMAROPS_MENU9_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_MENU9_LOCK);
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-menu9: cannot create ' . $dir);
		return $log;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . '/menu9-es.log', implode("\n", $log) . "\n", FILE_APPEND);
	return $log;
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_menu9_run();
});
