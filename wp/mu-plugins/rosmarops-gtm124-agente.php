<?php
/**
 * Plugin Name: RosmarOps «agent», not «assistant», in the credit line of two posts, and the /blog/ description (GTM-124, one-time, per site)
 * Description: Once per site (EN /, ES /es/, CA /ca/), in the published loop engineering post and the «what wasn't read» post of that site (found by slug), replaces the one word «assistants» / «asistentes» / «assistents» of the final credit line with «agents» / «agentes» / «agents» (GTM-122 rule, asked by Albert in GTM-124 M4). Nothing else in the text changes: only post_content is written, with the post's date, status and revisions left as they are. A post is left alone and logged if it is not published, or if the word does not appear exactly once in it, in the expected phrase. On the EN site it also sets The SEO Framework description of the /blog/ page to the text of GTM-25 §1, only if it still has the previous text. Idempotent: a per-site option marks it done, with a lock. The log (slugs only) goes to the option rosmarops_gtm124_log and to wp-content/rosmarops-private/gtm124-<lang>.log, which the deploy reads over SFTP. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_GTM124_DONE = 'rosmarops_gtm124_done';
const ROSMAROPS_GTM124_LOCK = 'rosmarops_gtm124_lock';
const ROSMAROPS_GTM124_LOG  = 'rosmarops_gtm124_log';
const ROSMAROPS_GTM124_WORD = '/asistent|assistent|assistant/i';
const ROSMAROPS_GTM124_BLOG_OLD = 'Notes from building RosmarOps: what AI coding agents like Claude Code and Cursor can reach on your machine, how the Agent Posture Score works, and what I learn along the way.';
const ROSMAROPS_GTM124_BLOG_NEW = 'Notes from building RosmarOps: what AI coding agents like Claude Code and Cursor can reach on your machine, and how the Agent Posture Score works.';

/** The plan for one site, by its home URL, or null for any other site. Each phrase is a pattern and its replacement. */
function rosmarops_gtm124_plan($home_url) {
	$en = ['/\bAI assistants\b/', 'AI agents'];
	$es = ['/\basistentes de IA\b/u', 'agentes de IA'];
	$ca = ["/\\bassistents d(['\x{2019}]|&#8217;|&rsquo;)IA\\b/u", 'agents d$1IA'];
	$plans = [
		'https://rosmarops.com'    => ['lang' => 'en', 'phrase' => $en, 'blog' => true,
			'posts' => ['loop-engineering-agents-working-alone', 'what-wasnt-read-doesnt-count-as-clean']],
		'https://rosmarops.com/es' => ['lang' => 'es', 'phrase' => $es, 'blog' => false,
			'posts' => ['loop-engineering-agentes-trabajando-solos', 'lo-que-no-se-leyo-no-cuenta-como-limpio']],
		'https://rosmarops.com/ca' => ['lang' => 'ca', 'phrase' => $ca, 'blog' => false,
			'posts' => ['loop-engineering-agents-treballant-sols', 'el-que-no-sha-llegit-no-compta-com-a-net']],
	];
	return $plans[rtrim((string) $home_url, '/')] ?? null;
}

/** The content with the one word replaced, or a string starting with «skipped:» saying why it was left alone. */
function rosmarops_gtm124_replace($content, $phrase) {
	$words = preg_match_all(ROSMAROPS_GTM124_WORD, $content);
	if ($words !== 1) {
		return "skipped: the word appears {$words} times, 1 expected";
	}
	$out = preg_replace($phrase[0], $phrase[1], $content, -1, $n);
	if ($n !== 1 || $out === null) {
		return 'skipped: the word is not in the expected phrase';
	}
	return $out;
}

/** Runs once on this site. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_gtm124_run() {
	$plan = rosmarops_gtm124_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_GTM124_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_GTM124_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_GTM124_LOCK) < 600) {
			return null; // another request is running it
		}
		update_option(ROSMAROPS_GTM124_LOCK, time(), false); // a run that died more than ten minutes ago: take over
	}
	global $wpdb;
	$log = ['GTM-124 agent, not assistant, site ' . $plan['lang'] . ', ' . gmdate('Y-m-d H:i:s') . ' UTC'];
	foreach ($plan['posts'] as $slug) {
		$found = get_posts(['name' => $slug, 'post_type' => 'post', 'post_status' => 'publish', 'numberposts' => 1]);
		if (!$found) {
			$log[] = "skipped: post {$slug} is not published here";
			continue;
		}
		$p = $found[0];
		$new = rosmarops_gtm124_replace((string) $p->post_content, $plan['phrase']);
		if (strpos($new, 'skipped:') === 0) {
			$log[] = "{$new} (post {$slug})";
			continue;
		}
		// Only post_content: wp_update_post would also run the content filters and move the modified date.
		if ($wpdb->update($wpdb->posts, ['post_content' => $new], ['ID' => (int) $p->ID]) !== 1) {
			$log[] = "failed: post {$slug} could not be written";
			continue;
		}
		clean_post_cache((int) $p->ID);
		$log[] = "post done: {$slug}";
	}
	if ($plan['blog']) {
		$page = get_page_by_path('blog');
		if (!$page) {
			$log[] = 'skipped: no /blog/ page';
		} else {
			$cur = (string) get_post_meta($page->ID, '_genesis_description', true);
			if ($cur === ROSMAROPS_GTM124_BLOG_NEW) {
				$log[] = 'skipped: /blog/ description already set';
			} elseif ($cur !== ROSMAROPS_GTM124_BLOG_OLD) {
				$log[] = 'skipped: /blog/ description is not the expected previous text';
			} else {
				update_post_meta($page->ID, '_genesis_description', ROSMAROPS_GTM124_BLOG_NEW);
				$log[] = 'blog done: /blog/ description';
			}
		}
	}
	update_option(ROSMAROPS_GTM124_LOG, $log, false);
	update_option(ROSMAROPS_GTM124_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_GTM124_LOCK);
	rosmarops_gtm124_write_log($plan['lang'], $log);
	return $log;
}

/** Writes the log to wp-content/rosmarops-private/ (closed to the web). */
function rosmarops_gtm124_write_log($lang, $log) {
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-gtm124: cannot create ' . $dir);
		return;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . "/gtm124-{$lang}.log", implode("\n", $log) . "\n");
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_gtm124_run();
});
