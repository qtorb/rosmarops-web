<?php
/**
 * Plugin Name: RosmarOps: «Sandbox» in the blog menu and «All about sandboxes» in the sandbox post (one-time, per site)
 * Description: GTM-175 (signed by Albert, 16-11). Once per site (EN /, ES /es/, CA /ca/), after the «Sandbox» section is published: (1) adds a «Sandbox» item to the GeneratePress primary menu, between Observatory and Methodology, pointing to the section of the site's language; (2) adds «All about sandboxes» («Todo sobre el sandbox», «Tot sobre el sandbox») as a last paragraph of the sandbox post (GTM-168 v3). Each part is left alone and logged if it is already there, if the menu has no Observatory item followed by a Methodology item at its top level, or if the post is not found once among the published posts. Never deletes, never touches other menu items than shifting the ones from Methodology on by one place, never touches another post. Idempotent: a per-site option marks it done, with a lock. The log (ids, slugs and positions only) goes to the option rosmarops_menu7_log and to wp-content/rosmarops-private/menu7-<lang>.log, which the deploy reads over SFTP; the deploy then removes this file from the server. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_MENU7_DONE = 'rosmarops_menu7_done';
const ROSMAROPS_MENU7_LOCK = 'rosmarops_menu7_lock';
const ROSMAROPS_MENU7_LOG  = 'rosmarops_menu7_log';

/** The plan for one site, by its home URL, or null for any other site. */
function rosmarops_menu7_plan($home_url) {
	$plans = [
		'https://rosmarops.com'    => ['lang' => 'en', 'observatory' => '/observatory', 'methodology' => '/methodology',
			'section' => '/sandbox/', 'post' => 'sandbox-ai-agents', 'link' => 'All about sandboxes'],
		'https://rosmarops.com/es' => ['lang' => 'es', 'observatory' => '/es/observatorio', 'methodology' => '/es/metodologia',
			'section' => '/es/sandbox/', 'post' => 'sandbox-agentes-de-ia', 'link' => 'Todo sobre el sandbox'],
		'https://rosmarops.com/ca' => ['lang' => 'ca', 'observatory' => '/ca/observatori', 'methodology' => '/ca/metodologia',
			'section' => '/ca/sandbox/', 'post' => 'sandbox-agents-dia', 'link' => 'Tot sobre el sandbox'],
	];
	return $plans[rtrim((string) $home_url, '/')] ?? null;
}

/** Path of a menu item's URL, without the trailing slash, so «https://rosmarops.com/es/observatorio/» is «/es/observatorio». */
function rosmarops_menu7_path($url) {
	$path = parse_url((string) $url, PHP_URL_PATH);
	return is_string($path) ? rtrim($path, '/') : '';
}

/** Adds «Sandbox» to the primary menu. Returns one log line. */
function rosmarops_menu7_menu($plan) {
	$locations = get_nav_menu_locations();
	$menu_id = (int) ($locations['primary'] ?? 0);
	if (!$menu_id) {
		return 'menu skipped: no menu in the primary location';
	}
	$items = wp_get_nav_menu_items($menu_id, ['post_status' => 'any']);
	if (!is_array($items)) {
		return "menu skipped: menu {$menu_id} has no items";
	}
	$obs = $meth = null;
	foreach ($items as $it) {
		$p = rosmarops_menu7_path($it->url);
		if ($p === rtrim($plan['section'], '/')) {
			return "menu skipped: item {$it->ID} already points to {$plan['section']}";
		}
		if ((int) $it->menu_item_parent !== 0) {
			continue;
		}
		if ($p === $plan['observatory'] && $obs === null) {
			$obs = $it;
		} elseif ($p === $plan['methodology'] && $meth === null) {
			$meth = $it;
		}
	}
	if ($obs === null || $meth === null || (int) $obs->menu_order >= (int) $meth->menu_order) {
		return "menu skipped: menu {$menu_id} has no top-level Observatory item followed by a Methodology item";
	}
	$pos = (int) $meth->menu_order;
	foreach ($items as $it) {
		if ((int) $it->menu_order >= $pos) {
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
	return "menu done: item {$new} «Sandbox» at position {$pos} of menu {$menu_id}, after item {$obs->ID} and before item {$meth->ID}";
}

/** Adds the link as the last paragraph of the sandbox post. Returns one log line. */
function rosmarops_menu7_post($plan) {
	$found = get_posts(['name' => $plan['post'], 'post_type' => ['post'], 'post_status' => ['publish'], 'numberposts' => 2]);
	if (count($found) !== 1) {
		return 'post skipped: ' . count($found) . " published posts with slug {$plan['post']}, 1 expected";
	}
	$post = $found[0];
	$href = $plan['section'];
	if (strpos((string) $post->post_content, 'href="' . $href . '"') !== false) {
		return "post skipped: post {$post->ID} already links to {$href}";
	}
	$block = "\n\n<!-- wp:paragraph -->\n<p><a href=\"{$href}\">" . esc_html($plan['link']) . "</a></p>\n<!-- /wp:paragraph -->";
	$content = rtrim((string) $post->post_content) . $block;
	$res = wp_update_post(['ID' => $post->ID, 'post_content' => wp_slash($content)], true);
	$now = (string) get_post_field('post_content', $post->ID);
	if (is_wp_error($res) || !$res || strpos($now, 'href="' . $href . '"') === false) {
		return "post failed: post {$post->ID} does not link to {$href}";
	}
	return "post done: post {$post->ID} ({$plan['post']}) now ends with the link to {$href}";
}

/** Runs once on this site. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_menu7_run() {
	$plan = rosmarops_menu7_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_MENU7_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_MENU7_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_MENU7_LOCK) < 600) {
			return null;
		}
		update_option(ROSMAROPS_MENU7_LOCK, time(), false);
	}
	$log = ['Sandbox in the menu and the post, site ' . $plan['lang'] . ', ' . gmdate('Y-m-d H:i:s') . ' UTC'];
	$log[] = rosmarops_menu7_menu($plan);
	$log[] = rosmarops_menu7_post($plan);
	update_option(ROSMAROPS_MENU7_LOG, $log, false);
	update_option(ROSMAROPS_MENU7_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_MENU7_LOCK);
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-menu7: cannot create ' . $dir);
		return $log;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . '/menu7-' . $plan['lang'] . '.log', implode("\n", $log) . "\n", FILE_APPEND);
	return $log;
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_menu7_run();
});
