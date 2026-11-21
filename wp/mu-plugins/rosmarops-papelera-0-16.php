<?php
/**
 * Plugin Name: RosmarOps: the three 0.16 drafts to the bin (one-time, per site)
 * Description: Plan for the week of 23-29 November, point 7 (signed by Albert 21-11 10:48). Once the news post for 0.16 + 0.17 is published, the three drafts of the earlier 0.16 post are no longer needed: EN 1255, ES 1245 and CA 99 (created by rosmarops-blog-drafts.php, deploy of 20-11 22:31 UTC). Once per site (EN /, ES /es/, CA /ca/): checks that the post with that id is a post, a draft and at its slug; then sends it to the bin with wp_trash_post() (never deletes: it can be restored from the bin for 30 days). Anything unexpected is logged as «skipped: <reason>» and nothing is done. Idempotent: a per-site option marks it done, with a lock. The log (ids, slugs and statuses only) goes to the option rosmarops_bin016_log and to wp-content/rosmarops-private/bin016-<lang>.log, which the deploy reads over SFTP; the deploy then removes this file from the server. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_BIN016_DONE = 'rosmarops_bin016_done';
const ROSMAROPS_BIN016_LOCK = 'rosmarops_bin016_lock';
const ROSMAROPS_BIN016_LOG  = 'rosmarops_bin016_log';

/** The plan for one site, by its home URL, or null for any other site. */
function rosmarops_bin016_plan($home_url) {
	$plans = [
		'https://rosmarops.com'    => ['lang' => 'en', 'id' => 1255, 'slug' => 'from-a-long-list-of-findings-to-a-short-list-of-problems'],
		'https://rosmarops.com/es' => ['lang' => 'es', 'id' => 1245, 'slug' => 'de-una-lista-larga-de-avisos-a-una-lista-corta-de-problemas'],
		'https://rosmarops.com/ca' => ['lang' => 'ca', 'id' => 99, 'slug' => 'duna-llista-llarga-davisos-a-una-llista-curta-de-problemes'],
	];
	return $plans[rtrim((string) $home_url, '/')] ?? null;
}

/** Runs once on this site. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_bin016_run() {
	$plan = rosmarops_bin016_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_BIN016_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_BIN016_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_BIN016_LOCK) < 600) {
			return null; // another request is running it
		}
		update_option(ROSMAROPS_BIN016_LOCK, time(), false); // a run that died more than ten minutes ago: take over
	}
	$id = $plan['id'];
	$slug = $plan['slug'];
	$log = ['0.16 draft to the bin, site ' . $plan['lang'] . ', ' . gmdate('Y-m-d H:i:s') . ' UTC'];

	$p = get_post($id);
	$log[] = $p ? "post {$id}: {$p->post_type} {$p->post_status} at {$p->post_name}" : "post {$id}: not found";
	if (!$p || $p->post_type !== 'post' || $p->post_status !== 'draft' || $p->post_name !== $slug) {
		$log[] = "skipped: post {$id} is not a draft at {$slug}";
		return rosmarops_bin016_finish($plan['lang'], $log);
	}

	// To the bin. Never wp_delete_post().
	$trashed = wp_trash_post($id);
	$status = get_post_field('post_status', $id);
	if (!$trashed || $status !== 'trash') {
		$log[] = "failed: post {$id} is {$status}, not in the bin";
	} else {
		$log[] = "done: post {$id} in the bin (was a draft at {$slug})";
	}
	return rosmarops_bin016_finish($plan['lang'], $log);
}

function rosmarops_bin016_finish($lang, $log) {
	update_option(ROSMAROPS_BIN016_LOG, $log, false);
	update_option(ROSMAROPS_BIN016_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_BIN016_LOCK);
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-bin016: cannot create ' . $dir);
		return $log;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . '/bin016-' . $lang . '.log', implode("\n", $log) . "\n", FILE_APPEND);
	return $log;
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_bin016_run();
});
