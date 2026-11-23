<?php
/**
 * Plugin Name: RosmarOps: Google title and description of two posts (GTM-121, one-time, per site)
 * Description: Once per site, sets The SEO Framework title (_genesis_title) and description (_genesis_description) of one published post: on EN, «Can one AI agent change another agent's configuration?»; on ES, the auto mode post. Signed by Albert on 23-11 with the advisor's recommendation (qtorb/rosmarops-vigil docs/research/2026-11-23-gtm-120-titulos-search-console.md, §2 and §6). Only those two meta fields change: the post title (H1), its content, its slug and its dates stay as they are. The post is found by slug and must be the only published post with it; anything else is left alone and logged. CA has no plan and logs nothing. Idempotent: a per-site option marks it done, with a lock. The log (id, slug, and the title and description before and after) goes to the option rosmarops_gtm121_log and to wp-content/rosmarops-private/gtm121-<lang>.log, which the deploy reads over SFTP; the deploy then removes this file from the server. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_GTM121_DONE = 'rosmarops_gtm121_done';
const ROSMAROPS_GTM121_LOCK = 'rosmarops_gtm121_lock';
const ROSMAROPS_GTM121_LOG  = 'rosmarops_gtm121_log';

/** The plan for one site, by its home URL, or null for any other site. Texts literal from GTM-120 §2.1 and §2.2. */
function rosmarops_gtm121_plan($home_url) {
	$plans = [
		'https://rosmarops.com'    => ['lang' => 'en', 'slug' => 'can-one-ai-agent-change-another-agents-configuration',
			'title' => "Can one AI agent rewrite another agent's settings?",
			'description' => 'Yes, if it can write where the other keeps its settings or instructions. Where Claude Code, Cursor and Hermes Agent keep theirs on Windows, and who asks first.'],
		'https://rosmarops.com/es' => ['lang' => 'es', 'slug' => 'modo-auto-claude-code-que-puede-leer',
			'title' => 'Modo auto de Claude Code: qué aprueba sin ti y cómo acotarlo',
			'description' => 'Las versiones recientes de Claude Code arrancan en modo auto: otro modelo de IA aprueba lo que antes te preguntaba. Qué sigue preguntando y cómo acotarlo.'],
	];
	return $plans[rtrim((string) $home_url, '/')] ?? null;
}

/** Runs once on this site. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_gtm121_run() {
	$plan = rosmarops_gtm121_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_GTM121_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_GTM121_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_GTM121_LOCK) < 600) {
			return null; // another request is running it
		}
		update_option(ROSMAROPS_GTM121_LOCK, time(), false); // a run that died more than ten minutes ago: take over
	}
	$log   = ['GTM-121 Google title and description, site ' . $plan['lang'] . ', ' . gmdate('Y-m-d H:i:s') . ' UTC'];
	$any   = ['publish', 'draft', 'pending', 'future', 'private'];
	$found = get_posts(['name' => $plan['slug'], 'post_type' => 'post', 'post_status' => $any, 'numberposts' => 2]);
	if (count($found) !== 1) {
		$log[] = 'skipped: ' . count($found) . " posts with slug {$plan['slug']}, 1 expected";
	} elseif ($found[0]->post_status !== 'publish') {
		$log[] = "skipped: post {$found[0]->ID} is {$found[0]->post_status}, not publish; left as it is";
	} else {
		$id    = (int) $found[0]->ID;
		$log[] = "post {$id} {$plan['slug']}";
		$log[] = 'title before: ' . (string) get_post_meta($id, '_genesis_title', true);
		$log[] = 'description before: ' . (string) get_post_meta($id, '_genesis_description', true);
		update_post_meta($id, '_genesis_title', $plan['title']);
		update_post_meta($id, '_genesis_description', $plan['description']);
		clean_post_cache($id);
		$log[] = 'title now: ' . $plan['title'];
		$log[] = 'description now: ' . $plan['description'];
		$log[] = "done: post {$id} has the new Google title and description; its H1, content and dates are unchanged";
	}
	update_option(ROSMAROPS_GTM121_LOG, $log, false);
	update_option(ROSMAROPS_GTM121_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_GTM121_LOCK);
	rosmarops_gtm121_write_log($plan['lang'], $log);
	return $log;
}

/** Writes the log to wp-content/rosmarops-private/ (closed to the web). */
function rosmarops_gtm121_write_log($lang, $log) {
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-gtm121: cannot create ' . $dir);
		return;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . "/gtm121-{$lang}.log", implode("\n", $log) . "\n");
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_gtm121_run();
});
