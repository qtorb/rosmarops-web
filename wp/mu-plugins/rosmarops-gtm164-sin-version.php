<?php
/**
 * Plugin Name: RosmarOps news post without a version in its title or address (GTM-164, one-time, per site)
 * Description: Once per site (EN /, ES /es/, CA /ca/), in the published news post of 14-11 (slug rosmarops-0-11), replaces the title, The SEO Framework title and the slug with versions without a program version, and points the hreflang addresses of the three posts to their new slugs. Asked by Albert on 14-11: no post title names a specific version of the program. The old address keeps working with a 301: the old slug is stored as _wp_old_slug, which WordPress redirects. Only post_title and post_name are written (by ID, without wp_update_post, so the dates and the content stay as they are), plus those three meta fields. A post is left alone and logged if it is not published, if the slug matches no post or more than one, or if the new slug is already taken. Idempotent: a per-site option marks it done, with a lock. The log (slugs and ids only) goes to the option rosmarops_gtm164_log and to wp-content/rosmarops-private/gtm164-<lang>.log, which the deploy reads over SFTP. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_GTM164_DONE = 'rosmarops_gtm164_done';
const ROSMAROPS_GTM164_LOCK = 'rosmarops_gtm164_lock';
const ROSMAROPS_GTM164_LOG  = 'rosmarops_gtm164_log';
const ROSMAROPS_GTM164_OLD  = 'rosmarops-0-11';
const ROSMAROPS_GTM164_URLS = [
	'en' => 'https://rosmarops.com/blog/whats-new-in-rosmarops-november-2026/',
	'es' => 'https://rosmarops.com/es/blog/novedades-de-rosmarops-noviembre-2026/',
	'ca' => 'https://rosmarops.com/ca/blog/novetats-de-rosmarops-novembre-2026/',
];

/** The plan for one site, by its home URL, or null for any other site. */
function rosmarops_gtm164_plan($home_url) {
	$plans = [
		'https://rosmarops.com' => ['lang' => 'en', 'slug' => 'whats-new-in-rosmarops-november-2026',
			'title' => "What's new in RosmarOps: nine agents with a score, your projects across your whole folder and fewer interruptions",
			'seo' => "What's new in RosmarOps for people using AI agents"],
		'https://rosmarops.com/es' => ['lang' => 'es', 'slug' => 'novedades-de-rosmarops-noviembre-2026',
			'title' => 'Lo nuevo en RosmarOps: nueve agentes con nota, tus proyectos en toda tu carpeta y menos interrupciones',
			'seo' => 'Lo nuevo en RosmarOps para quien usa agentes de IA'],
		'https://rosmarops.com/ca' => ['lang' => 'ca', 'slug' => 'novetats-de-rosmarops-novembre-2026',
			'title' => 'El nou de RosmarOps: nou agents amb nota, els teus projectes a tota la teva carpeta i menys interrupcions',
			'seo' => "El nou de RosmarOps per a qui fa servir agents d'IA"],
	];
	return $plans[rtrim((string) $home_url, '/')] ?? null;
}

/** Runs once on this site. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_gtm164_run() {
	$plan = rosmarops_gtm164_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_GTM164_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_GTM164_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_GTM164_LOCK) < 600) {
			return null; // another request is running it
		}
		update_option(ROSMAROPS_GTM164_LOCK, time(), false); // a run that died more than ten minutes ago: take over
	}
	global $wpdb;
	$log = ['GTM-164 news post without a version, site ' . $plan['lang'] . ', ' . gmdate('Y-m-d H:i:s') . ' UTC'];
	$any = ['publish', 'draft', 'pending', 'future', 'private'];
	$found = get_posts(['name' => ROSMAROPS_GTM164_OLD, 'post_type' => 'post', 'post_status' => $any, 'numberposts' => 2]);
	$taken = get_posts(['name' => $plan['slug'], 'post_type' => ['post', 'page'], 'post_status' => $any, 'numberposts' => 1]);
	if (count($found) !== 1) {
		$log[] = 'skipped: ' . count($found) . ' posts with slug ' . ROSMAROPS_GTM164_OLD . ', 1 expected';
	} elseif ($found[0]->post_status !== 'publish') {
		$log[] = "skipped: post {$found[0]->ID} is {$found[0]->post_status}, not publish; left as it is";
	} elseif ($taken) {
		$log[] = "skipped: slug {$plan['slug']} already used by {$taken[0]->post_type} {$taken[0]->ID}";
	} else {
		$id = (int) $found[0]->ID;
		// Only these two columns: wp_update_post would move the modified date and run the content filters.
		if ($wpdb->update($wpdb->posts, ['post_title' => $plan['title'], 'post_name' => $plan['slug']], ['ID' => $id]) !== 1) {
			$log[] = "failed: post {$id} could not be written";
		} else {
			add_post_meta($id, '_wp_old_slug', ROSMAROPS_GTM164_OLD); // WordPress answers the old address with a 301
			update_post_meta($id, '_genesis_title', $plan['seo']);
			foreach (ROSMAROPS_GTM164_URLS as $l => $url) {
				if ($l !== $plan['lang']) {
					update_post_meta($id, 'rosmarops_url_' . $l, $url);
				}
			}
			clean_post_cache($id);
			$log[] = "done: post {$id} is now {$plan['slug']}, old slug kept for the redirect";
		}
	}
	update_option(ROSMAROPS_GTM164_LOG, $log, false);
	update_option(ROSMAROPS_GTM164_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_GTM164_LOCK);
	rosmarops_gtm164_write_log($plan['lang'], $log);
	return $log;
}

/** Writes the log to wp-content/rosmarops-private/ (closed to the web). */
function rosmarops_gtm164_write_log($lang, $log) {
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-gtm164: cannot create ' . $dir);
		return;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . "/gtm164-{$lang}.log", implode("\n", $log) . "\n");
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_gtm164_run();
});
