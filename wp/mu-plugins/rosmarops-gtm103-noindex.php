<?php
/**
 * Plugin Name: RosmarOps legacy posts and old categories to noindex (GTM-103, one-time migration)
 * Description: Once, on the Spanish site (/es/) only, marks noindex in The SEO Framework the 27 legacy posts that are still published (groups 1 and 2 of the legacy blog cut: every published post that is neither a product post nor in the retired list of rosmarops-retired.php) and every category that is not one of the blog's categories, then clears the sitemap cache so they leave /es/sitemap.xml. Asked by Albert 07-11 (D4 of the 48 h plan). Deletes nothing, changes no text and no status; reversible by unticking noindex. If the legacy posts found are not exactly 27, nothing changes and the list is logged. Idempotent (option rosmarops_gtm103_done, with a lock). The log (slugs only) goes to the option rosmarops_gtm103_log and to wp-content/rosmarops-private/gtm103-es.log, which the deploy reads over SFTP. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_GTM103_DONE = 'rosmarops_gtm103_done';
const ROSMAROPS_GTM103_LOCK = 'rosmarops_gtm103_lock';
const ROSMAROPS_GTM103_LOG  = 'rosmarops_gtm103_log';
const ROSMAROPS_GTM103_EXPECTED = 27;

// The product's posts on /es/ (as in GTM-97): never marked noindex.
const ROSMAROPS_GTM103_PRODUCT = [
	'que-es-rosmarops', 'que-claves-puede-leer-tu-agente-de-ia', 'puede-un-agente-de-ia-cambiar-la-configuracion-de-otro',
	'herramientas-que-revisan-a-que-llegan-tus-agentes-de-ia', 'mi-maquina-saco-un-18-de-100', 'rosmarops-ya-se-puede-descargar',
	'rosmarops-0-3-0', 'rosmarops-0-4-0', 'como-funciona-la-nota-de-exposicion', 'antes-de-decirle-a-tu-agente-que-lo-instale',
	'lo-que-no-se-leyo-no-cuenta-como-limpio', 'modo-auto-claude-code-que-puede-leer',
	'servidores-mcp-de-markdown-que-buscaban-credenciales-en-la-nube',
];

/** Runs once on /es/. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_gtm103_run() {
	if (rtrim((string) home_url(), '/') !== 'https://rosmarops.com/es' || get_option(ROSMAROPS_GTM103_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_GTM103_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_GTM103_LOCK) < 600) {
			return null; // another request is running it
		}
		update_option(ROSMAROPS_GTM103_LOCK, time(), false); // a run that died more than ten minutes ago: take over
	}
	$log = ['GTM-103 legacy posts and old categories to noindex, site es, ' . gmdate('Y-m-d H:i:s') . ' UTC'];
	if (!defined('ROSMAROPS_RETIRED') || !defined('ROSMAROPS_BLOG_CATEGORIES')) {
		$log[] = 'stopped: rosmarops-retired.php is not loaded; nothing changed';
		return rosmarops_gtm103_stop($log);
	}
	$legacy = [];
	foreach (get_posts(['post_type' => 'post', 'post_status' => 'publish', 'numberposts' => -1]) as $p) {
		if (!in_array($p->post_name, ROSMAROPS_GTM103_PRODUCT, true) && !in_array($p->post_name, ROSMAROPS_RETIRED, true)) {
			$legacy[] = $p;
		}
	}
	if (count($legacy) !== ROSMAROPS_GTM103_EXPECTED) {
		$log[] = 'stopped: ' . count($legacy) . ' legacy posts found, ' . ROSMAROPS_GTM103_EXPECTED . ' expected; nothing changed';
		foreach ($legacy as $p) {
			$log[] = "found: {$p->post_name}";
		}
		return rosmarops_gtm103_stop($log);
	}
	$posts = 0;
	foreach ($legacy as $p) {
		if ((int) get_post_meta($p->ID, '_genesis_noindex', true) === 1) {
			$log[] = "skipped: post {$p->post_name} is already noindex";
			continue;
		}
		update_post_meta($p->ID, '_genesis_noindex', 1);
		$posts++;
		$log[] = "post done: {$p->post_name} noindex";
	}
	$cats = 0;
	$default = (int) get_option('default_category');
	foreach (get_terms(['taxonomy' => 'category', 'hide_empty' => false]) as $t) {
		if (in_array($t->slug, ROSMAROPS_BLOG_CATEGORIES, true)) {
			continue;
		}
		if ((int) $t->term_id === $default) {
			$log[] = "skipped: category {$t->slug} is the site's default category";
			continue;
		}
		$settings = get_term_meta($t->term_id, 'autodescription-term-settings', true);
		$settings = is_array($settings) ? $settings : [];
		if ((int) ($settings['noindex'] ?? 0) === 1) {
			$log[] = "skipped: category {$t->slug} is already noindex";
			continue;
		}
		$settings['noindex'] = 1;
		update_term_meta($t->term_id, 'autodescription-term-settings', $settings);
		$cats++;
		$log[] = "category done: {$t->slug} noindex ({$t->count} posts)";
	}
	$log[] = "total: {$posts} posts and {$cats} categories marked noindex";
	$log[] = rosmarops_gtm103_clear_sitemap();
	update_option(ROSMAROPS_GTM103_LOG, $log, false);
	update_option(ROSMAROPS_GTM103_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_GTM103_LOCK);
	rosmarops_gtm103_write_log($log);
	return $log;
}

/** Ends a run that changed nothing: not marked done, so it runs again once the cause is fixed. */
function rosmarops_gtm103_stop($log) {
	update_option(ROSMAROPS_GTM103_LOG, $log, false);
	delete_option(ROSMAROPS_GTM103_LOCK);
	rosmarops_gtm103_write_log($log);
	return $log;
}

/** Clears The SEO Framework sitemap cache (as GTM-97); returns a log line. */
function rosmarops_gtm103_clear_sitemap() {
	if (class_exists('\The_SEO_Framework\Sitemap\Cache') && method_exists('\The_SEO_Framework\Sitemap\Cache', 'clear_sitemap_caches')) {
		\The_SEO_Framework\Sitemap\Cache::clear_sitemap_caches();
		return 'sitemap: cache cleared (The SEO Framework 5, Sitemap\Cache::clear_sitemap_caches)';
	}
	if (function_exists('tsf') && method_exists(tsf(), 'delete_cache')) {
		tsf()->delete_cache('sitemap');
		return "sitemap: cache cleared (The SEO Framework 4, delete_cache('sitemap'))";
	}
	return 'sitemap: not cleared (no The SEO Framework API found)';
}

/** Writes the log to wp-content/rosmarops-private/ (closed to the web). */
function rosmarops_gtm103_write_log($log) {
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-gtm103: cannot create ' . $dir);
		return;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . '/gtm103-es.log', implode("\n", $log) . "\n");
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_gtm103_run();
});
