<?php
/**
 * Plugin Name: RosmarOps: the sandbox post back to its address without «-2» (one-time, per site)
 * Description: Once per site (EN /, ES /es/, CA /ca/), finds the published sandbox post (GTM-168 v3) at its address with «-2» and gives it back its intended slug, so the hreflang links between languages point to pages that answer 200. Asked by Albert on 16-11 («hazlo tú»). Only the slug changes; WordPress keeps the «-2» address as an old slug, so it redirects to the new one. A post is left alone and logged if the «-2» slug matches no published post or more than one, or if any other post, page or attachment (in any status, the bin included) still uses the intended slug. Never deletes, never touches another post. Idempotent: a per-site option marks it done, with a lock. The log (slugs, ids and statuses only) goes to the option rosmarops_slug6_log and to wp-content/rosmarops-private/slug6-<lang>.log, which the deploy reads over SFTP. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_SLUG6_DONE = 'rosmarops_slug6_done';
const ROSMAROPS_SLUG6_LOCK = 'rosmarops_slug6_lock';
const ROSMAROPS_SLUG6_LOG  = 'rosmarops_slug6_log';

/** The plan for one site, by its home URL, or null for any other site. */
function rosmarops_slug6_plan($home_url) {
	$plans = [
		'https://rosmarops.com'    => ['lang' => 'en', 'slug' => 'sandbox-ai-agents'],
		'https://rosmarops.com/es' => ['lang' => 'es', 'slug' => 'sandbox-agentes-de-ia'],
		'https://rosmarops.com/ca' => ['lang' => 'ca', 'slug' => 'sandbox-agents-dia'],
	];
	return $plans[rtrim((string) $home_url, '/')] ?? null;
}

function rosmarops_slug6_find($slug, $statuses, $types = ['post']) {
	return get_posts(['name' => $slug, 'post_type' => $types, 'post_status' => $statuses, 'numberposts' => 2]);
}

/** Runs once on this site. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_slug6_run() {
	$plan = rosmarops_slug6_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_SLUG6_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_SLUG6_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_SLUG6_LOCK) < 600) {
			return null;
		}
		update_option(ROSMAROPS_SLUG6_LOCK, time(), false);
	}
	$slug = $plan['slug'];
	$log = ['Sandbox post back to ' . $slug . ', site ' . $plan['lang'] . ', ' . gmdate('Y-m-d H:i:s') . ' UTC'];
	$found = rosmarops_slug6_find($slug . '-2', ['publish']);
	if (count($found) !== 1) {
		$log[] = 'skipped: ' . count($found) . " published posts with slug {$slug}-2, 1 expected";
		return rosmarops_slug6_finish($plan['lang'], $log);
	}
	$taken = rosmarops_slug6_find($slug, ['publish', 'draft', 'pending', 'future', 'private', 'trash', 'inherit'], ['post', 'page', 'attachment']);
	if (count($taken) > 0) {
		$log[] = "skipped: post {$taken[0]->ID} ({$taken[0]->post_status}) {$taken[0]->post_type} still uses {$slug}; post {$found[0]->ID} left at {$slug}-2";
		return rosmarops_slug6_finish($plan['lang'], $log);
	}
	$res = wp_update_post(['ID' => $found[0]->ID, 'post_name' => $slug], true);
	$now = get_post_field('post_name', $found[0]->ID);
	if (is_wp_error($res) || !$res || $now !== $slug) {
		$log[] = "failed: post {$found[0]->ID} is at " . $now . ", not {$slug}";
	} else {
		$log[] = "done: post {$found[0]->ID} now at {$slug} (was {$slug}-2)";
	}
	return rosmarops_slug6_finish($plan['lang'], $log);
}

function rosmarops_slug6_finish($lang, $log) {
	update_option(ROSMAROPS_SLUG6_LOG, $log, false);
	update_option(ROSMAROPS_SLUG6_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_SLUG6_LOCK);
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-slug6: cannot create ' . $dir);
		return $log;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . '/slug6-' . $lang . '.log', implode("\n", $log) . "\n", FILE_APPEND);
	return $log;
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_slug6_run();
});
