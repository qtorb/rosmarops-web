<?php
/**
 * Plugin Name: RosmarOps: schedule the AI agent map post for 17-11 at 06:00 Madrid (one-time, per site)
 * Description: Once per site (EN /, ES /es/, CA /ca/), finds the draft of the post «The AI agent map» (GTM-149) by its slug and schedules it in WordPress for 2026-11-17 06:00 Europe/Madrid (05:00 UTC), with status «future». Signed by Albert on 13-11 («firmo»: publish it on Tuesday 17-11 at 06:00). Same mechanism as rosmarops-schedule-he-terminado.php. Only the status and the date change: title, content, category, tags, image and SEO fields are left as the drafts loader created them. A post is left alone and logged if it is not a draft, if the slug matches no post or more than one, or if the time has already passed. As a fallback for when WP-Cron does not fire, any request after that time publishes a post of this plan that is still «future». Never deletes, never touches another post. Idempotent: a per-site option marks it done, with a lock. The log (slugs, ids and statuses only) goes to the option rosmarops_sched4_log and to wp-content/rosmarops-private/sched4-<lang>.log, which the deploy reads over SFTP. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_SCHED4_DONE = 'rosmarops_sched4_done';
const ROSMAROPS_SCHED4_LOCK = 'rosmarops_sched4_lock';
const ROSMAROPS_SCHED4_LOG  = 'rosmarops_sched4_log';
const ROSMAROPS_SCHED4_LIVE = 'rosmarops_sched4_live';
const ROSMAROPS_SCHED4_GMT  = '2026-11-17 05:00:00'; // 06:00 in Madrid (CET, UTC+1)

/** The plan for one site, by its home URL, or null for any other site. */
function rosmarops_sched4_plan($home_url) {
	$plans = [
		'https://rosmarops.com'    => ['lang' => 'en', 'post' => 'ai-agent-map'],
		'https://rosmarops.com/es' => ['lang' => 'es', 'post' => 'mapa-agentes-ia'],
		'https://rosmarops.com/ca' => ['lang' => 'ca', 'post' => 'mapa-agents-ia'],
	];
	return $plans[rtrim((string) $home_url, '/')] ?? null;
}

/** The posts with the plan's slug, in any status but the bin. */
function rosmarops_sched4_find($slug) {
	return get_posts(['name' => $slug, 'post_type' => 'post', 'post_status' => ['publish', 'draft', 'pending', 'future', 'private'], 'numberposts' => 2]);
}

/** Runs once on this site. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_sched4_run() {
	$plan = rosmarops_sched4_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_SCHED4_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_SCHED4_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_SCHED4_LOCK) < 600) {
			return null; // another request is running it
		}
		update_option(ROSMAROPS_SCHED4_LOCK, time(), false); // a run that died more than ten minutes ago: take over
	}
	$log = ['Schedule the AI agent map post, site ' . $plan['lang'] . ', ' . gmdate('Y-m-d H:i:s') . ' UTC'];

	$found = rosmarops_sched4_find($plan['post']);
	if (count($found) !== 1) {
		$log[] = 'skipped: ' . count($found) . ' posts with slug ' . $plan['post'] . ', 1 expected';
		return rosmarops_sched4_finish($plan['lang'], $log);
	}
	$post = $found[0];
	if ($post->post_status !== 'draft') {
		$log[] = "skipped: post {$post->ID} ({$plan['post']}) is {$post->post_status}, not draft; left as it is";
		return rosmarops_sched4_finish($plan['lang'], $log);
	}
	if (time() >= strtotime(ROSMAROPS_SCHED4_GMT . ' UTC')) {
		$log[] = "skipped: post {$post->ID} ({$plan['post']}): " . ROSMAROPS_SCHED4_GMT . ' UTC has passed; still draft';
		return rosmarops_sched4_finish($plan['lang'], $log);
	}
	$res = wp_update_post([
		'ID'            => $post->ID,
		'post_status'   => 'future',
		'post_date'     => get_date_from_gmt(ROSMAROPS_SCHED4_GMT),
		'post_date_gmt' => ROSMAROPS_SCHED4_GMT,
		'edit_date'     => true,
	], true);
	if (is_wp_error($res) || !$res) {
		$log[] = "failed: post {$post->ID} ({$plan['post']}) still draft";
	} else {
		$log[] = "done: post {$post->ID} ({$plan['post']}) scheduled for " . ROSMAROPS_SCHED4_GMT . ' UTC, status ' . get_post_status($post->ID);
	}
	return rosmarops_sched4_finish($plan['lang'], $log);
}

/** After the time, publishes the plan's post if it is still «future» (WP-Cron did not fire). Stops checking once the post is published. */
function rosmarops_sched4_fallback() {
	$plan = rosmarops_sched4_plan(home_url());
	if ($plan === null || !get_option(ROSMAROPS_SCHED4_DONE) || get_option(ROSMAROPS_SCHED4_LIVE)
		|| time() < strtotime(ROSMAROPS_SCHED4_GMT . ' UTC')) {
		return;
	}
	$found = rosmarops_sched4_find($plan['post']);
	if (count($found) !== 1) {
		return;
	}
	$line = null;
	if ($found[0]->post_status === 'future') {
		wp_publish_post($found[0]->ID);
		$line = 'fallback: post ' . $found[0]->ID . ' published by a request at ' . gmdate('Y-m-d H:i:s') . ' UTC';
	}
	if (get_post_status($found[0]->ID) !== 'future') {
		update_option(ROSMAROPS_SCHED4_LIVE, gmdate('c'), false); // published (by WP-Cron, by this or by hand) or changed by hand: stop checking
		$line = $line ?? 'post ' . $found[0]->ID . ' is ' . get_post_status($found[0]->ID) . ' at ' . gmdate('Y-m-d H:i:s') . ' UTC';
	}
	if ($line !== null) {
		$log = (array) get_option(ROSMAROPS_SCHED4_LOG, []);
		$log[] = $line;
		update_option(ROSMAROPS_SCHED4_LOG, $log, false);
		rosmarops_sched4_write($plan['lang'], [$line]);
	}
}

function rosmarops_sched4_finish($lang, $log) {
	update_option(ROSMAROPS_SCHED4_LOG, $log, false);
	update_option(ROSMAROPS_SCHED4_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_SCHED4_LOCK);
	rosmarops_sched4_write($lang, $log);
	return $log;
}

/** Appends lines to wp-content/rosmarops-private/sched4-<lang>.log, closed to the web. */
function rosmarops_sched4_write($lang, $lines) {
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-sched4: cannot create ' . $dir);
		return;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . '/sched4-' . $lang . '.log', implode("\n", $lines) . "\n", FILE_APPEND);
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_sched4_run();
	rosmarops_sched4_fallback();
});
