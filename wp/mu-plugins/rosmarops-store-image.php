<?php
/**
 * Plugin Name: RosmarOps: featured image for the Microsoft Store post (one-time, per site)
 * Description: Once per site (EN /, ES /es/, CA /ca/), finds the post «RosmarOps is now on the Microsoft Store» (GTM-139) by its slug and, if it has no featured image yet, sets one: a crop of RosmarOps's page on the Microsoft Store (rosmarops-img-18-microsoft-store.jpg, next to the blog drafts), with the alt text of that language. Asked by Albert on 13-11 («tendríamos que poner esta imagen de Microsoft store en el post»). Only the featured image is set: title, content, status, date, category, tags and SEO fields are left as they are. A post is left alone and logged if the slug matches no post or more than one, or if it already has a featured image. Never deletes. Idempotent: a per-site option marks it done, with a lock. The log (slugs, ids and statuses only) goes to the option rosmarops_storeimg_log and to wp-content/rosmarops-private/storeimg-<lang>.log, which the deploy reads over SFTP. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_STOREIMG_DONE = 'rosmarops_storeimg_done';
const ROSMAROPS_STOREIMG_LOCK = 'rosmarops_storeimg_lock';
const ROSMAROPS_STOREIMG_LOG  = 'rosmarops_storeimg_log';
const ROSMAROPS_STOREIMG_FILE = 'rosmarops-img-18-microsoft-store.jpg';
const ROSMAROPS_STOREIMG_SLUG = 'rosmarops-microsoft-store';

/** The plan for one site, by its home URL, or null for any other site. */
function rosmarops_storeimg_plan($home_url) {
	$plans = [
		'https://rosmarops.com'    => ['lang' => 'en', 'alt' => 'RosmarOps page on the Microsoft Store, with its download button and the PEGI 3 rating.'],
		'https://rosmarops.com/es' => ['lang' => 'es', 'alt' => 'Ficha de RosmarOps en la Microsoft Store, con su botón de descarga y la clasificación PEGI 3.'],
		'https://rosmarops.com/ca' => ['lang' => 'ca', 'alt' => 'Fitxa de RosmarOps a la Microsoft Store, amb el botó de descàrrega i la classificació PEGI 3.'],
	];
	return $plans[rtrim((string) $home_url, '/')] ?? null;
}

function rosmarops_storeimg_dir() {
	return defined('ROSMAROPS_DRAFTS_DIR') ? ROSMAROPS_DRAFTS_DIR : __DIR__ . '/rosmarops-drafts';
}

/** Runs once on this site. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_storeimg_run() {
	$plan = rosmarops_storeimg_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_STOREIMG_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_STOREIMG_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_STOREIMG_LOCK) < 600) {
			return null; // another request is running it
		}
		update_option(ROSMAROPS_STOREIMG_LOCK, time(), false);
	}
	$log = ['Store post featured image, site ' . $plan['lang'] . ', ' . gmdate('Y-m-d H:i:s') . ' UTC'];

	$found = get_posts(['name' => ROSMAROPS_STOREIMG_SLUG, 'post_type' => 'post', 'post_status' => ['publish', 'draft', 'pending', 'future', 'private'], 'numberposts' => 2]);
	if (count($found) !== 1) {
		$log[] = 'skipped: ' . count($found) . ' posts with slug ' . ROSMAROPS_STOREIMG_SLUG . ', 1 expected';
		return rosmarops_storeimg_finish($plan['lang'], $log);
	}
	$id = (int) $found[0]->ID;
	if (get_post_meta($id, '_thumbnail_id', true)) {
		$log[] = "skipped: post {$id} already has a featured image; left as it is";
		return rosmarops_storeimg_finish($plan['lang'], $log);
	}
	$file = rosmarops_storeimg_dir() . '/' . ROSMAROPS_STOREIMG_FILE;
	if (!is_file($file)) {
		$log[] = 'failed: ' . ROSMAROPS_STOREIMG_FILE . ' not found';
		return rosmarops_storeimg_finish($plan['lang'], $log);
	}
	$up = wp_upload_bits(ROSMAROPS_STOREIMG_FILE, null, (string) file_get_contents($file));
	if (!empty($up['error'])) {
		$log[] = 'failed: ' . ROSMAROPS_STOREIMG_FILE . ' not uploaded';
		return rosmarops_storeimg_finish($plan['lang'], $log);
	}
	$att = wp_insert_attachment(['post_mime_type' => 'image/jpeg', 'post_title' => 'Microsoft Store', 'post_status' => 'inherit'], $up['file'], $id, true);
	if (is_wp_error($att) || !$att) {
		$log[] = 'failed: attachment not created';
		return rosmarops_storeimg_finish($plan['lang'], $log);
	}
	foreach (['file.php', 'media.php', 'image.php'] as $inc) { // the admin helpers that build the image sizes
		if (is_file(ABSPATH . 'wp-admin/includes/' . $inc)) {
			require_once ABSPATH . 'wp-admin/includes/' . $inc;
		}
	}
	wp_update_attachment_metadata($att, wp_generate_attachment_metadata($att, $up['file']));
	update_post_meta($att, '_wp_attachment_image_alt', $plan['alt']);
	set_post_thumbnail($id, $att);
	$log[] = "done: attachment {$att} is the featured image of post {$id} (" . ROSMAROPS_STOREIMG_SLUG . ')';
	return rosmarops_storeimg_finish($plan['lang'], $log);
}

function rosmarops_storeimg_finish($lang, $log) {
	update_option(ROSMAROPS_STOREIMG_LOG, $log, false);
	update_option(ROSMAROPS_STOREIMG_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_STOREIMG_LOCK);
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-storeimg: cannot create ' . $dir);
		return $log;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . '/storeimg-' . $lang . '.log', implode("\n", $log) . "\n", FILE_APPEND);
	return $log;
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_storeimg_run();
});
