<?php
/**
 * Plugin Name: RosmarOps «Loop engineering» blog category (one-time, per site)
 * Description: Once per site (EN /, ES /es/, CA /ca/), creates the «Loop engineering» category (slug loop-engineering) with its description (ES and CA signed by Albert on 08-11; EN pending the product advisor), sets The SEO Framework noindex on it while it has fewer than three published posts, adds it to the loop engineering post of that site (found by slug, in any status but the bin) and removes the default category from that post, and sets the post's featured image from rosmarops-drafts/rosmarops-img-13-loop-engineering.jpg if it has none. Never publishes, never deletes a post or a category, never replaces a featured image. Anything not where the plan expects is left alone and logged. Idempotent: a per-site option marks it done, with a lock. The log (no personal data) goes to the option rosmarops_loopcat_log and to wp-content/rosmarops-private/loopcat-<lang>.log, which the deploy reads over SFTP. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_LOOPCAT_DONE  = 'rosmarops_loopcat_done';
const ROSMAROPS_LOOPCAT_LOCK  = 'rosmarops_loopcat_lock';
const ROSMAROPS_LOOPCAT_LOG   = 'rosmarops_loopcat_log';
const ROSMAROPS_LOOPCAT_SLUG  = 'loop-engineering';
const ROSMAROPS_LOOPCAT_IMAGE = 'rosmarops-img-13-loop-engineering.jpg';
const ROSMAROPS_LOOPCAT_TSF   = 'autodescription-term-settings';

/** The plan for one site, by its home URL, or null for any other site. */
function rosmarops_loopcat_plan($home_url) {
	$plans = [
		'https://rosmarops.com' => [
			'lang' => 'en',
			'description' => 'What happens when you leave an AI agent working in a loop: what starts it, who checks what it does, when it stops and what it costs. With dated studies and cases, and their sources.',
			'post' => 'loop-engineering-agents-working-alone',
			'alt'  => 'An AI agent at the centre of a loop of documents going round, with a hand checking one of them with a magnifying glass.',
		],
		'https://rosmarops.com/es' => [
			'lang' => 'es',
			'description' => 'Qué pasa cuando dejas a un agente de IA trabajando en bucle: qué lo pone en marcha, quién comprueba lo que hace, cuándo para y cuánto cuesta. Con estudios y casos fechados, y su fuente.',
			'post' => 'loop-engineering-agentes-trabajando-solos',
			'alt'  => 'Un agente de IA en el centro de un bucle de documentos que dan vueltas, y una mano que revisa uno de ellos con una lupa.',
		],
		'https://rosmarops.com/ca' => [
			'lang' => 'ca',
			'description' => "Què passa quan deixes un agent d'IA treballant en bucle: què el posa en marxa, qui comprova el que fa, quan s'atura i quant costa. Amb estudis i casos datats, i la seva font.",
			'post' => 'loop-engineering-agents-treballant-sols',
			'alt'  => "Un agent d'IA al centre d'un bucle de documents que donen voltes, i una mà que en revisa un amb una lupa.",
		],
	];
	return $plans[rtrim((string) $home_url, '/')] ?? null;
}

/** Folder with the image (deployed next to this file, with the drafts). */
function rosmarops_loopcat_dir() {
	return defined('ROSMAROPS_DRAFTS_DIR') ? ROSMAROPS_DRAFTS_DIR : __DIR__ . '/rosmarops-drafts';
}

/** Runs once on this site. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_loopcat_run() {
	$plan = rosmarops_loopcat_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_LOOPCAT_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_LOOPCAT_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_LOOPCAT_LOCK) < 600) {
			return null; // another request is running it
		}
		update_option(ROSMAROPS_LOOPCAT_LOCK, time(), false); // a run that died more than ten minutes ago: take over
	}
	$log = ['Loop engineering category, site ' . $plan['lang'] . ', ' . gmdate('Y-m-d H:i:s') . ' UTC'];

	// A. The category.
	$term = get_term_by('slug', ROSMAROPS_LOOPCAT_SLUG, 'category');
	if ($term) {
		$log[] = 'A skipped: category ' . ROSMAROPS_LOOPCAT_SLUG . ' already exists; left as it is';
	} else {
		$res = wp_insert_term('Loop engineering', 'category', ['slug' => ROSMAROPS_LOOPCAT_SLUG, 'description' => $plan['description']]);
		if (is_wp_error($res)) {
			$log[] = 'A failed: category not created; nothing else done';
			return rosmarops_loopcat_finish($plan['lang'], $log, false); // not marked done: it runs again
		}
		$term = get_term_by('slug', ROSMAROPS_LOOPCAT_SLUG, 'category');
		$log[] = 'A done: category ' . ROSMAROPS_LOOPCAT_SLUG . ' created';
	}
	$term_id = (int) $term->term_id;

	// B. noindex while it has fewer than three published posts.
	$count = count(get_posts(['category' => $term_id, 'post_type' => 'post', 'post_status' => 'publish', 'numberposts' => 3, 'fields' => 'ids']));
	$meta  = get_term_meta($term_id, ROSMAROPS_LOOPCAT_TSF, true);
	$meta  = is_array($meta) ? $meta : [];
	if ($count >= 3) {
		$log[] = "B skipped: {$count} published posts; stays indexable";
	} elseif ((int) ($meta['noindex'] ?? 0) === 1) {
		$log[] = 'B skipped: already noindex';
	} else {
		$meta['noindex'] = 1;
		update_term_meta($term_id, ROSMAROPS_LOOPCAT_TSF, $meta);
		$log[] = "B done: noindex ({$count} published posts)";
	}

	// C. The post: the category, without the default one.
	$found = get_posts(['name' => $plan['post'], 'post_type' => 'post', 'post_status' => ['publish', 'draft', 'pending', 'future', 'private'], 'numberposts' => 2]);
	if (count($found) !== 1) {
		$log[] = "C skipped: post {$plan['post']} " . ($found ? 'matches more than one post' : 'not found') . '; D skipped too';
		return rosmarops_loopcat_finish($plan['lang'], $log, true);
	}
	$post = $found[0];
	$cats = array_map('intval', wp_get_post_categories($post->ID));
	$new  = array_values(array_diff(array_unique(array_merge($cats, [$term_id])), [(int) get_option('default_category')]));
	sort($cats);
	$sorted = $new;
	sort($sorted);
	if ($sorted === $cats) {
		$log[] = "C skipped: post {$post->ID} already has the category";
	} else {
		wp_set_post_categories($post->ID, $new);
		$log[] = "C done: post {$post->ID} ({$post->post_status}) in " . ROSMAROPS_LOOPCAT_SLUG . ($post->post_status === 'publish' ? '' : '; still ' . $post->post_status);
	}

	// D. The featured image, only if the post has none.
	if (has_post_thumbnail($post->ID)) {
		$log[] = "D skipped: post {$post->ID} already has a featured image; not replaced";
		return rosmarops_loopcat_finish($plan['lang'], $log, true);
	}
	$file = rosmarops_loopcat_dir() . '/' . ROSMAROPS_LOOPCAT_IMAGE;
	if (!is_file($file)) {
		$log[] = 'D skipped: ' . ROSMAROPS_LOOPCAT_IMAGE . ' not found';
		return rosmarops_loopcat_finish($plan['lang'], $log, true);
	}
	$up = wp_upload_bits(ROSMAROPS_LOOPCAT_IMAGE, null, (string) file_get_contents($file));
	if (!empty($up['error'])) {
		$log[] = 'D failed: image not uploaded';
		return rosmarops_loopcat_finish($plan['lang'], $log, true);
	}
	$att = wp_insert_attachment(['post_mime_type' => 'image/jpeg', 'post_title' => 'Loop engineering', 'post_status' => 'inherit'], $up['file'], $post->ID, true);
	if (is_wp_error($att) || !$att) {
		$log[] = 'D failed: attachment not created';
		return rosmarops_loopcat_finish($plan['lang'], $log, true);
	}
	foreach (['file.php', 'media.php', 'image.php'] as $inc) { // the admin helpers that build the image sizes
		if (is_file(ABSPATH . 'wp-admin/includes/' . $inc)) {
			require_once ABSPATH . 'wp-admin/includes/' . $inc;
		}
	}
	wp_update_attachment_metadata($att, wp_generate_attachment_metadata($att, $up['file']));
	update_post_meta($att, '_wp_attachment_image_alt', $plan['alt']);
	set_post_thumbnail($post->ID, $att);
	$log[] = "D done: featured image {$att} on post {$post->ID}";
	return rosmarops_loopcat_finish($plan['lang'], $log, true);
}

/** Stores and writes the log, marks the site done when asked, and releases the lock. */
function rosmarops_loopcat_finish($lang, $log, $done) {
	update_option(ROSMAROPS_LOOPCAT_LOG, $log, false);
	if ($done) {
		update_option(ROSMAROPS_LOOPCAT_DONE, gmdate('c'), false);
	}
	delete_option(ROSMAROPS_LOOPCAT_LOCK);
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-loopcat: cannot create ' . $dir);
		return $log;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . '/loopcat-' . $lang . '.log', implode("\n", $log) . "\n", FILE_APPEND);
	return $log;
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_loopcat_run();
});
