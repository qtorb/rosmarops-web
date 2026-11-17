<?php
/**
 * Plugin Name: RosmarOps: the sandbox post in ES and CA back to its address without «-2» (one-time, per site)
 * Description: GTM-175 slug7 (signed by Albert 17-11 17:43). slug6 left the ES and CA sandbox posts at their «-2» address because the drafts 1238 (ES) and 90 (CA), the first text of #162, still hold the clean slug. Once per site (ES /es/, CA /ca/ only): checks that the draft is a draft at the clean slug and the published post is published at the «-2» slug; sends the draft to the bin with wp_trash_post() (never deletes); checks that no other post, page or attachment, in any status and the bin included, uses the clean slug; then changes only the post_name of the published post. WordPress keeps «-2» as _wp_old_slug and redirects it. Anything unexpected is logged as «skipped: <reason>» and nothing else is done. Idempotent: a per-site option marks it done, with a lock. The log (ids, slugs and statuses only) goes to the option rosmarops_slug7_log and to wp-content/rosmarops-private/slug7-<lang>.log, which the deploy reads over SFTP; the deploy then removes this file from the server. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_SLUG7_DONE = 'rosmarops_slug7_done';
const ROSMAROPS_SLUG7_LOCK = 'rosmarops_slug7_lock';
const ROSMAROPS_SLUG7_LOG  = 'rosmarops_slug7_log';
const ROSMAROPS_SLUG7_ALL  = ['publish', 'draft', 'pending', 'future', 'private', 'trash', 'inherit', 'auto-draft'];

/** The plan for one site, by its home URL, or null for any other site (EN included). */
function rosmarops_slug7_plan($home_url) {
	$plans = [
		'https://rosmarops.com/es' => ['lang' => 'es', 'slug' => 'sandbox-agentes-de-ia', 'draft' => 1238, 'post' => 1240],
		'https://rosmarops.com/ca' => ['lang' => 'ca', 'slug' => 'sandbox-agents-dia', 'draft' => 90, 'post' => 91],
	];
	return $plans[rtrim((string) $home_url, '/')] ?? null;
}

/** Runs once on this site. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_slug7_run() {
	$plan = rosmarops_slug7_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_SLUG7_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_SLUG7_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_SLUG7_LOCK) < 600) {
			return null;
		}
		update_option(ROSMAROPS_SLUG7_LOCK, time(), false);
	}
	$slug = $plan['slug'];
	$d = $plan['draft'];
	$p = $plan['post'];
	$log = ['Sandbox post back to ' . $slug . ', site ' . $plan['lang'] . ', ' . gmdate('Y-m-d H:i:s') . ' UTC'];

	// 1. What holds each address today.
	$draft = get_post($d);
	$post = get_post($p);
	$log[] = $draft ? "draft {$d}: {$draft->post_type} {$draft->post_status} at {$draft->post_name}" : "draft {$d}: not found";
	$log[] = $post ? "post {$p}: {$post->post_type} {$post->post_status} at {$post->post_name}" : "post {$p}: not found";
	if (!$draft || $draft->post_type !== 'post' || $draft->post_status !== 'draft' || $draft->post_name !== $slug) {
		$log[] = "skipped: post {$d} is not a draft at {$slug}";
		return rosmarops_slug7_finish($plan['lang'], $log);
	}
	if (!$post || $post->post_type !== 'post' || $post->post_status !== 'publish' || $post->post_name !== $slug . '-2') {
		$log[] = "skipped: post {$p} is not published at {$slug}-2";
		return rosmarops_slug7_finish($plan['lang'], $log);
	}

	// 2. The draft to the bin. Never wp_delete_post().
	$trashed = wp_trash_post($d);
	$log[] = "trash: post {$d} is " . get_post_field('post_status', $d) . ' at ' . get_post_field('post_name', $d);
	if (!$trashed || get_post_field('post_status', $d) !== 'trash') {
		$log[] = "failed: post {$d} did not go to the bin; post {$p} left at {$slug}-2";
		return rosmarops_slug7_finish($plan['lang'], $log);
	}

	// 3. Nothing else may use the clean slug, in any status, the bin included.
	$taken = get_posts(['name' => $slug, 'post_type' => ['post', 'page', 'attachment'], 'post_status' => ROSMAROPS_SLUG7_ALL, 'numberposts' => 2]);
	if (count($taken) > 0) {
		$log[] = "skipped: {$taken[0]->ID} usa el slug ({$taken[0]->post_type} {$taken[0]->post_status}); post {$p} left at {$slug}-2";
		return rosmarops_slug7_finish($plan['lang'], $log);
	}

	// 4. Only the slug of the published post. WordPress keeps «-2» as _wp_old_slug.
	$res = wp_update_post(['ID' => $p, 'post_name' => $slug], true);
	$now = get_post_field('post_name', $p);
	if (is_wp_error($res) || !$res || $now !== $slug) {
		$log[] = "failed: post {$p} is at {$now}, not {$slug}";
	} else {
		$log[] = "done: post {$p} now at {$slug} (was {$slug}-2)";
	}
	return rosmarops_slug7_finish($plan['lang'], $log);
}

function rosmarops_slug7_finish($lang, $log) {
	update_option(ROSMAROPS_SLUG7_LOG, $log, false);
	update_option(ROSMAROPS_SLUG7_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_SLUG7_LOCK);
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-slug7: cannot create ' . $dir);
		return $log;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . '/slug7-' . $lang . '.log', implode("\n", $log) . "\n", FILE_APPEND);
	return $log;
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_slug7_run();
});
