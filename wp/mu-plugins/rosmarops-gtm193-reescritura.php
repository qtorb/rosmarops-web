<?php
/**
 * Plugin Name: RosmarOps: the rewritten text of the 0.16.0 post (GTM-193, one-time, EN and ES)
 * Description: Once per site, on EN / and ES /es/ only, replaces the content, excerpt and The SEO Framework description of the 0.16.0 post (found by slug, published or draft) with the rewrite that Albert ordered on 20-11 («hay que implementar la revisión de texto»; qtorb/rosmarops-web wp/drafts/novedades-0-16-{en,es}.html and .json, the same files the CA draft is created from). The title, slug, status, date, category, image and translations do not change. It only writes when the post still starts with the first sentence of the previous text, so it never overwrites a later edit. Nothing is published or deleted. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_GTM193_DONE = 'rosmarops_gtm193_done';
const ROSMAROPS_GTM193_LOCK = 'rosmarops_gtm193_lock';
const ROSMAROPS_GTM193_LOG  = 'rosmarops_gtm193_log';

/** The plan for one site, by its home URL, or null for any other site (CA gets the new text as a new draft). */
function rosmarops_gtm193_plan($home_url) {
	$plans = [
		'https://rosmarops.com'    => ['lang' => 'en', 'slug' => 'from-a-long-list-of-findings-to-a-short-list-of-problems',
			'old' => 'RosmarOps 0.16.0 is out.'],
		'https://rosmarops.com/es' => ['lang' => 'es', 'slug' => 'de-una-lista-larga-de-avisos-a-una-lista-corta-de-problemas',
			'old' => 'Ya está la versión 0.16.0 de RosmarOps.'],
	];
	return $plans[rtrim((string) $home_url, '/')] ?? null;
}

/** Runs once on this site. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_gtm193_run() {
	$plan = rosmarops_gtm193_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_GTM193_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_GTM193_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_GTM193_LOCK) < 600) {
			return null; // another request is running it
		}
		update_option(ROSMAROPS_GTM193_LOCK, time(), false); // a run that died more than ten minutes ago: take over
	}
	global $wpdb;
	$log  = ['GTM-193 rewritten 0.16.0 post, site ' . $plan['lang'] . ', ' . gmdate('Y-m-d H:i:s') . ' UTC'];
	$dir  = WP_CONTENT_DIR . '/mu-plugins/rosmarops-drafts';
	$json = json_decode((string) @file_get_contents("{$dir}/novedades-0-16-{$plan['lang']}.json"), true);
	$html = (string) @file_get_contents("{$dir}/novedades-0-16-{$plan['lang']}.html");
	$found = get_posts(['name' => $plan['slug'], 'post_type' => 'post', 'post_status' => ['publish', 'draft', 'future', 'pending'], 'numberposts' => 1]);
	if (!is_array($json) || !is_string($json['excerpt'] ?? null) || !is_string($json['seo_description'] ?? null) || trim($html) === '') {
		$log[] = 'skipped: the new text is not on the server';
	} elseif (strpos(trim(html_entity_decode(wp_strip_all_tags($html), ENT_QUOTES)), $json['excerpt']) !== 0) {
		$log[] = 'skipped: the text on the server is not the rewrite';
	} elseif (!$found) {
		$log[] = "skipped: no post {$plan['slug']} here";
	} else {
		$p    = $found[0];
		$text = trim(wp_strip_all_tags((string) $p->post_content));
		if (strpos($text, $plan['old']) !== 0) {
			$log[] = "skipped: post {$p->ID} no longer starts with the previous text";
		} elseif ($wpdb->update($wpdb->posts, ['post_content' => rtrim($html, "\n"), 'post_excerpt' => $json['excerpt']], ['ID' => (int) $p->ID]) !== 1) {
			// Only content and excerpt: wp_update_post would also run the content filters and move the modified date.
			$log[] = "failed: post {$p->ID} could not be written";
		} else {
			update_post_meta((int) $p->ID, '_genesis_description', $json['seo_description']);
			clean_post_cache((int) $p->ID);
			$log[] = "post done: {$p->ID} ({$p->post_status})";
		}
	}
	update_option(ROSMAROPS_GTM193_LOG, $log, false);
	update_option(ROSMAROPS_GTM193_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_GTM193_LOCK);
	rosmarops_gtm193_write_log($plan['lang'], $log);
	return $log;
}

/** Writes the log to wp-content/rosmarops-private/ (closed to the web). */
function rosmarops_gtm193_write_log($lang, $log) {
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-gtm193: cannot create ' . $dir);
		return;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . "/gtm193-{$lang}.log", implode("\n", $log) . "\n");
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_gtm193_run();
});
