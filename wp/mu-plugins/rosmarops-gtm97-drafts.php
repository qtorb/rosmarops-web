<?php
/**
 * Plugin Name: RosmarOps retired posts to draft (GTM-97, one-time migration)
 * Description: Once, on the Spanish site (/es/) only, turns to draft every published post or page whose slug is in the retired list of rosmarops-retired.php (group 3 of the legacy blog cut, asked by Albert 2026-11-03 19:48, signed 2026-11-06), then clears The SEO Framework sitemap cache so /es/sitemap.xml is rebuilt. Deletes nothing; never touches a slug outside the list or one of the product's posts; a slug already in draft or missing is left alone and logged. Idempotent (option rosmarops_gtm97_done, with a lock). The log (slugs and statuses only) goes to the option rosmarops_gtm97_log and to wp-content/rosmarops-private/gtm97-es.log, which the deploy reads over SFTP. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_GTM97_DONE = 'rosmarops_gtm97_done';
const ROSMAROPS_GTM97_LOCK = 'rosmarops_gtm97_lock';
const ROSMAROPS_GTM97_LOG  = 'rosmarops_gtm97_log';

// The product's posts and pages on /es/: never changed, even if a slug somehow appeared in the retired list.
const ROSMAROPS_GTM97_PRODUCT = [
	'que-es-rosmarops', 'que-claves-puede-leer-tu-agente-de-ia', 'puede-un-agente-de-ia-cambiar-la-configuracion-de-otro',
	'herramientas-que-revisan-a-que-llegan-tus-agentes-de-ia', 'mi-maquina-saco-un-18-de-100', 'rosmarops-ya-se-puede-descargar',
	'rosmarops-0-3-0', 'rosmarops-0-4-0', 'como-funciona-la-nota-de-exposicion', 'antes-de-decirle-a-tu-agente-que-lo-instale',
	'lo-que-no-se-leyo-no-cuenta-como-limpio', 'modo-auto-claude-code-que-puede-leer',
	'servidores-mcp-de-markdown-que-buscaban-credenciales-en-la-nube',
];

/** Runs once on /es/. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_gtm97_run() {
	if (rtrim((string) home_url(), '/') !== 'https://rosmarops.com/es' || get_option(ROSMAROPS_GTM97_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_GTM97_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_GTM97_LOCK) < 600) {
			return null; // another request is running it
		}
		update_option(ROSMAROPS_GTM97_LOCK, time(), false); // a run that died more than ten minutes ago: take over
	}
	$log = ['GTM-97 retired posts to draft, site es, ' . gmdate('Y-m-d H:i:s') . ' UTC'];
	if (!defined('ROSMAROPS_RETIRED')) {
		$log[] = 'stopped: the retired list (rosmarops-retired.php) is not loaded; nothing changed';
		delete_option(ROSMAROPS_GTM97_LOCK);
		rosmarops_gtm97_write_log($log);
		return $log; // not marked done: it runs again once the list is there
	}
	$changed = 0;
	foreach (ROSMAROPS_RETIRED as $slug) {
		if (in_array($slug, ROSMAROPS_GTM97_PRODUCT, true)) {
			$log[] = "skipped: {$slug} is a product post; not touched";
			continue;
		}
		$found = get_posts(['name' => $slug, 'post_type' => ['post', 'page'], 'post_status' => 'any', 'numberposts' => 2]);
		if (!$found) {
			$log[] = "skipped: {$slug} not found";
			continue;
		}
		if (count($found) > 1) {
			$log[] = "skipped: {$slug} matches more than one post; not touched";
			continue;
		}
		$p = $found[0];
		if ($p->post_status !== 'publish') {
			$log[] = "skipped: {$slug} ({$p->post_type}) is {$p->post_status}; left as it is";
			continue;
		}
		$res = wp_update_post(['ID' => $p->ID, 'post_status' => 'draft'], true);
		if (is_wp_error($res) || !$res) {
			$log[] = "failed: {$slug} ({$p->post_type}) still publish";
			continue;
		}
		$changed++;
		$log[] = "done: {$slug} ({$p->post_type}) publish -> draft";
	}
	$log[] = "total: {$changed} turned to draft, " . count(ROSMAROPS_RETIRED) . ' in the list';
	$log[] = rosmarops_gtm97_clear_sitemap();
	update_option(ROSMAROPS_GTM97_LOG, $log, false);
	update_option(ROSMAROPS_GTM97_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_GTM97_LOCK);
	rosmarops_gtm97_write_log($log);
	return $log;
}

/** Clears The SEO Framework sitemap cache on this site, with the API of the installed version; returns a log line. */
function rosmarops_gtm97_clear_sitemap() {
	if (class_exists('\The_SEO_Framework\Sitemap\Cache') && method_exists('\The_SEO_Framework\Sitemap\Cache', 'clear_sitemap_caches')) {
		\The_SEO_Framework\Sitemap\Cache::clear_sitemap_caches();
		return 'sitemap: cache cleared (The SEO Framework 5, Sitemap\Cache::clear_sitemap_caches)';
	}
	if (function_exists('tsf') && method_exists(tsf(), 'delete_cache')) {
		tsf()->delete_cache('sitemap');
		return "sitemap: cache cleared (The SEO Framework 4, delete_cache('sitemap'))";
	}
	global $wpdb;
	if (isset($wpdb) && is_object($wpdb) && method_exists($wpdb, 'query')) {
		$n = (int) $wpdb->query("DELETE FROM {$wpdb->options} WHERE option_name LIKE '\\_transient\\_tsf\\_sitemap\\_%' OR option_name LIKE '\\_transient\\_timeout\\_tsf\\_sitemap\\_%'");
		return "sitemap: The SEO Framework API not found; {$n} sitemap transients deleted";
	}
	return 'sitemap: not cleared (no The SEO Framework API found)';
}

/** Writes the log to wp-content/rosmarops-private/ (closed to the web; created by GTM-94 if missing). */
function rosmarops_gtm97_write_log($log) {
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-gtm97: cannot create ' . $dir);
		return;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . '/gtm97-es.log', implode("\n", $log) . "\n");
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_gtm97_run();
});
