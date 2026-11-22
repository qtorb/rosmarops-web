<?php
/**
 * Plugin Name: RosmarOps: worktree post drafts in Albert's voice (GTM-195, one-time, per site)
 * Description: Once per site (EN /, ES /es/, CA /ca/), replaces the title, content, excerpt and The SEO Framework description of the draft «A git worktree is not a sandbox» (EN 1262, ES 1252, CA 105) with the text in wp-content/mu-plugins/rosmarops-drafts/worktree-<lang>.json and .html. Those files hold the version in Albert's voice, cleared by the advisor on 22-11 (qtorb/rosmarops-vigil docs/research/2026-11-22-gtm-195-post-worktree-voz-albert.md). The blog drafts plugin never updates an existing post, hence this one. The post is checked by ID, type, slug and status (draft only) before it is written, and is left alone and logged if anything differs: a post Albert already published is never touched. Nothing is published. The write goes by ID with $wpdb (no wp_update_post), so no revision or date changes. Idempotent: a per-site option marks it done, with a lock. The log (ids, slugs and statuses only) goes to the option rosmarops_gtm195_log and to wp-content/rosmarops-private/gtm195-<lang>.log, which the deploy reads over SFTP; the deploy then removes this file from the server. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_GTM195_DONE = 'rosmarops_gtm195_done';
const ROSMAROPS_GTM195_LOCK = 'rosmarops_gtm195_lock';
const ROSMAROPS_GTM195_LOG  = 'rosmarops_gtm195_log';

/** The plan for one site, by its home URL, or null for any other site. */
function rosmarops_gtm195_plan($home_url) {
	$plans = [
		'https://rosmarops.com'    => ['lang' => 'en', 'id' => 1262, 'slug' => 'a-git-worktree-is-not-a-sandbox'],
		'https://rosmarops.com/es' => ['lang' => 'es', 'id' => 1252, 'slug' => 'una-worktree-de-git-no-es-un-sandbox'],
		'https://rosmarops.com/ca' => ['lang' => 'ca', 'id' => 105, 'slug' => 'una-worktree-de-git-no-es-un-sandbox'],
	];
	return $plans[rtrim((string) $home_url, '/')] ?? null;
}

/** The new text for a language, or a string saying what is wrong. */
function rosmarops_gtm195_text($lang) {
	$dir = defined('ROSMAROPS_GTM195_DRAFTS') ? ROSMAROPS_GTM195_DRAFTS : __DIR__ . '/rosmarops-drafts'; // tests point it at wp/drafts
	$json = @file_get_contents("{$dir}/worktree-{$lang}.json");
	$d = $json === false ? null : json_decode($json, true);
	if (!is_array($d) || ($d['lang'] ?? '') !== $lang || ($d['content'] ?? '') !== "worktree-{$lang}.html") {
		return "worktree-{$lang}.json missing or not well formed";
	}
	foreach (['title', 'excerpt', 'seo_description'] as $k) {
		if (!is_string($d[$k] ?? null) || $d[$k] === '') {
			return "worktree-{$lang}.json lacks {$k}";
		}
	}
	$html = @file_get_contents("{$dir}/worktree-{$lang}.html");
	if ($html === false || trim($html) === '') {
		return "worktree-{$lang}.html missing or empty";
	}
	return ['title' => $d['title'], 'excerpt' => $d['excerpt'], 'seo_description' => $d['seo_description'], 'content' => $html];
}

/** Runs once on this site. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_gtm195_run() {
	$plan = rosmarops_gtm195_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_GTM195_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_GTM195_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_GTM195_LOCK) < 600) {
			return null; // another request is running it
		}
		update_option(ROSMAROPS_GTM195_LOCK, time(), false); // a run that died more than ten minutes ago: take over
	}
	global $wpdb;
	$id   = $plan['id'];
	$slug = $plan['slug'];
	$log  = ['GTM-195 worktree draft in Albert\'s voice, site ' . $plan['lang'] . ', ' . gmdate('Y-m-d H:i:s') . ' UTC'];

	$p = get_post($id);
	$t = rosmarops_gtm195_text($plan['lang']);
	$log[] = $p ? "post {$id}: {$p->post_type} {$p->post_status} at {$p->post_name}" : "post {$id}: not found";
	if (!$p || $p->post_type !== 'post' || $p->post_status !== 'draft' || $p->post_name !== $slug) {
		$log[] = "skipped: post {$id} is not the draft at {$slug}";
	} elseif (!is_array($t)) {
		$log[] = "skipped: {$t}";
	} else {
		$data = ['post_title' => $t['title'], 'post_content' => $t['content'], 'post_excerpt' => $t['excerpt']];
		if ($wpdb->update($wpdb->posts, $data, ['ID' => $id]) === false) {
			$log[] = "failed: post {$id} could not be written";
		} else {
			update_post_meta($id, '_genesis_description', $t['seo_description']);
			clean_post_cache($id);
			$log[] = "done: draft {$id} {$slug} has the new title, content, excerpt and description; still a draft";
		}
	}

	update_option(ROSMAROPS_GTM195_LOG, $log, false);
	update_option(ROSMAROPS_GTM195_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_GTM195_LOCK);
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-gtm195: cannot create ' . $dir);
		return $log;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . '/gtm195-' . $plan['lang'] . '.log', implode("\n", $log) . "\n", FILE_APPEND);
	return $log;
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_gtm195_run();
});
