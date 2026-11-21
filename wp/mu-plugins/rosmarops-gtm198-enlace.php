<?php
/**
 * Plugin Name: RosmarOps: link from the 21-11 post to the orchestrators page (GTM-198, one-time, per site)
 * Description: Once per site (EN /, ES /es/, CA /ca/), adds one line to the published post «When one agent puts other agents to work» (EN 1258, ES 1248, CA 101): a paragraph pointing to the new standing page «What is an AI agent orchestrator?», placed at the end of the post, after its last paragraph. Nothing else in the post changes. Text signed by Albert (qtorb/rosmarops-vigil docs/research/2026-11-21-gtm-198-textos.md, «Enlaces entrantes» §3). The post is checked by ID, type, slug and status before it is written, and is left alone and logged if anything differs or if it already has the line. The write goes by ID with $wpdb (no wp_update_post), so the post's dates stay as they are. Idempotent: a per-site option marks it done, with a lock. The log (ids, slugs and statuses only) goes to the option rosmarops_gtm198_log and to wp-content/rosmarops-private/gtm198-<lang>.log, which the deploy reads over SFTP; the deploy then removes this file from the server. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_GTM198_DONE = 'rosmarops_gtm198_done';
const ROSMAROPS_GTM198_LOCK = 'rosmarops_gtm198_lock';
const ROSMAROPS_GTM198_LOG  = 'rosmarops_gtm198_log';
// Marks the line, so that the post never gets it twice.
const ROSMAROPS_GTM198_MARK = 'rosmarops-gtm198';

/** The plan for one site, by its home URL, or null for any other site. */
function rosmarops_gtm198_plan($home_url) {
	$plans = [
		'https://rosmarops.com'    => ['lang' => 'en', 'id' => 1258, 'slug' => 'when-one-agent-puts-other-agents-to-work',
			'text' => 'More on what an orchestrator is: <a href="/agent-orchestrators/">What is an AI agent orchestrator?</a>'],
		'https://rosmarops.com/es' => ['lang' => 'es', 'id' => 1248, 'slug' => 'cuando-un-agente-pone-a-trabajar-a-otros-agentes',
			'text' => 'Más sobre qué es un orquestador: <a href="/es/orquestadores-de-agentes/">¿Qué es un orquestador de agentes de IA?</a>'],
		'https://rosmarops.com/ca' => ['lang' => 'ca', 'id' => 101, 'slug' => 'quan-un-agent-posa-a-treballar-altres-agents',
			'text' => 'Més sobre què és un orquestrador: <a href="/ca/orquestradors-dagents/">Què és un orquestrador d\'agents d\'IA?</a>'],
	];
	return $plans[rtrim((string) $home_url, '/')] ?? null;
}

/** The line as a paragraph block. */
function rosmarops_gtm198_line($text) {
	return '<!-- wp:paragraph {"className":"' . ROSMAROPS_GTM198_MARK . '"} -->' . "\n"
		. '<p class="' . ROSMAROPS_GTM198_MARK . '">' . $text . '</p>' . "\n"
		. "<!-- /wp:paragraph -->\n\n";
}

/** Runs once on this site. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_gtm198_run() {
	$plan = rosmarops_gtm198_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_GTM198_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_GTM198_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_GTM198_LOCK) < 600) {
			return null; // another request is running it
		}
		update_option(ROSMAROPS_GTM198_LOCK, time(), false); // a run that died more than ten minutes ago: take over
	}
	global $wpdb;
	$id   = $plan['id'];
	$slug = $plan['slug'];
	$log  = ['GTM-198 link to the orchestrators page, site ' . $plan['lang'] . ', ' . gmdate('Y-m-d H:i:s') . ' UTC'];

	$p = get_post($id);
	$log[] = $p ? "post {$id}: {$p->post_type} {$p->post_status} at {$p->post_name}" : "post {$id}: not found";
	if (!$p || $p->post_type !== 'post' || $p->post_status !== 'publish' || $p->post_name !== $slug) {
		$log[] = "skipped: post {$id} is not the published post at {$slug}";
	} elseif (strpos($p->post_content, ROSMAROPS_GTM198_MARK) !== false) {
		$log[] = "skipped: post {$id} already has the line";
	} else {
		$content = rtrim($p->post_content) . "\n\n" . rtrim(rosmarops_gtm198_line($plan['text'])) . "\n";
		if ($wpdb->update($wpdb->posts, ['post_content' => $content], ['ID' => $id]) !== 1) {
			$log[] = "failed: post {$id} could not be written";
		} else {
			clean_post_cache($id);
			$log[] = "done: post {$id} {$slug} has the line at its end";
		}
	}

	update_option(ROSMAROPS_GTM198_LOG, $log, false);
	update_option(ROSMAROPS_GTM198_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_GTM198_LOCK);
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-gtm198: cannot create ' . $dir);
		return $log;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . '/gtm198-' . $plan['lang'] . '.log', implode("\n", $log) . "\n", FILE_APPEND);
	return $log;
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_gtm198_run();
});
