<?php
/**
 * Plugin Name: RosmarOps blog drafts from the repository (one time per draft and site)
 * Description: Creates, as a DRAFT and never published, each blog post described in wp-content/mu-plugins/rosmarops-drafts/*.json on the site of its language (EN /, ES /es/, CA /ca/), with its title, slug, excerpt, content (the HTML file named in the JSON), The SEO Framework title and description, the addresses of its translations for hreflang and, when the JSON names them, its category (an existing one, by slug), its tags (created if missing) and its featured image with alt text (a .jpg next to the JSON; added on 09-11 for posts 2 and 3 of the series and the 0.10 news post). Asked by Albert on 08-11 so that posts reach WordPress without signing in to the admin. A slug already used by any post or page on that site (in any status) is left alone and logged; nothing is ever updated, published or deleted. Idempotent: an option per draft marks it done, with a lock. The log (slugs, ids and statuses only) goes to the option rosmarops_drafts_log and to wp-content/rosmarops-private/drafts-<lang>.log, which the deploy reads over SFTP. Albert publishes from WordPress. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_DRAFTS_SITES  = ['en' => 'https://rosmarops.com', 'es' => 'https://rosmarops.com/es', 'ca' => 'https://rosmarops.com/ca'];
const ROSMAROPS_DRAFTS_LOCK   = 'rosmarops_drafts_lock';
const ROSMAROPS_DRAFTS_LOG    = 'rosmarops_drafts_log';
const ROSMAROPS_DRAFTS_AUTHOR = 'Albert Garcia Pujadas';

/** Folder with the draft descriptions (deployed next to this file). */
function rosmarops_drafts_dir() {
	return defined('ROSMAROPS_DRAFTS_DIR') ? ROSMAROPS_DRAFTS_DIR : __DIR__ . '/rosmarops-drafts';
}

/** Language of this site, or null if it is none of the three. */
function rosmarops_drafts_site_lang() {
	$home = rtrim((string) home_url(), '/');
	$lang = array_search($home, ROSMAROPS_DRAFTS_SITES, true);
	return $lang === false ? null : $lang;
}

/** The drafts for a language that are well formed; problems go to the log. */
function rosmarops_drafts_for($lang, &$log) {
	$out = [];
	foreach (glob(rosmarops_drafts_dir() . '/*.json') ?: [] as $file) {
		$d = json_decode((string) file_get_contents($file), true);
		$name = basename($file);
		if (!is_array($d) || ($d['lang'] ?? '') !== $lang) {
			continue;
		}
		foreach (['id', 'slug', 'title', 'excerpt', 'content', 'seo_title', 'seo_description'] as $k) {
			if (!is_string($d[$k] ?? null) || $d[$k] === '') {
				$log[] = "skipped: {$name} lacks {$k}";
				continue 2;
			}
		}
		if (!preg_match('/^[a-z0-9-]+$/', $d['id']) || !preg_match('/^[a-z0-9-]+$/', $d['slug']) || !preg_match('/^[a-z0-9-]+\.html$/', $d['content'])) {
			$log[] = "skipped: {$name} has an id, slug or content file outside the allowed characters";
			continue;
		}
		if (!rosmarops_drafts_extras_ok($d)) {
			$log[] = "skipped: {$name} has a category, tag or image that is not well formed";
			continue;
		}
		$html = rosmarops_drafts_dir() . '/' . $d['content'];
		if (!is_file($html)) {
			$log[] = "skipped: {$name}: {$d['content']} not found";
			continue;
		}
		$d['html'] = (string) file_get_contents($html);
		$out[] = $d;
	}
	return $out;
}

/** Optional fields: category (slug), tags ({slug: name}), image (a .jpg file name) with alt (required with an image). */
function rosmarops_drafts_extras_ok($d) {
	if (isset($d['category']) && (!is_string($d['category']) || !preg_match('/^[a-z0-9-]+$/', $d['category']))) {
		return false;
	}
	if (isset($d['tags'])) {
		if (!is_array($d['tags'])) {
			return false;
		}
		foreach ($d['tags'] as $slug => $tag) {
			if (!is_string($slug) || !preg_match('/^[a-z0-9-]+$/', $slug) || !is_string($tag) || $tag === '') {
				return false;
			}
		}
	}
	if (isset($d['image'])) {
		if (!is_string($d['image']) || !preg_match('/^[a-z0-9-]+\.jpg$/', $d['image']) || !is_string($d['alt'] ?? null) || $d['alt'] === '') {
			return false;
		}
	}
	return true;
}

/** Puts the new draft in its category (only if it exists on this site) and adds its tags (creating missing ones). */
function rosmarops_drafts_terms($id, $d, &$log) {
	if (isset($d['category'])) {
		$cat = get_term_by('slug', $d['category'], 'category');
		if ($cat) {
			wp_set_post_categories($id, [(int) $cat->term_id], false);
			$log[] = "category: {$d['category']} on post {$id}";
		} else {
			$log[] = "category skipped: {$d['category']} does not exist on this site; post {$id} keeps the default";
		}
	}
	if (!empty($d['tags'])) {
		$ids = [];
		foreach ($d['tags'] as $slug => $tag) {
			$t = get_term_by('slug', $slug, 'post_tag');
			if ($t) {
				$ids[] = (int) $t->term_id;
				continue;
			}
			$res = wp_insert_term($tag, 'post_tag', ['slug' => $slug]);
			if (is_wp_error($res)) {
				$log[] = "tag failed: {$slug} not created";
				continue;
			}
			$ids[] = (int) $res['term_id'];
		}
		if ($ids) {
			wp_set_post_terms($id, $ids, 'post_tag', false);
			$log[] = 'tags: ' . implode(', ', array_keys($d['tags'])) . " on post {$id}";
		}
	}
}

/** Sets the featured image of the new draft from the .jpg named in its JSON, with its alt text. */
function rosmarops_drafts_image($id, $d, &$log) {
	if (!isset($d['image'])) {
		return;
	}
	$file = rosmarops_drafts_dir() . '/' . $d['image'];
	if (!is_file($file)) {
		$log[] = "image skipped: {$d['image']} not found";
		return;
	}
	$up = wp_upload_bits($d['image'], null, (string) file_get_contents($file));
	if (!empty($up['error'])) {
		$log[] = "image failed: {$d['image']} not uploaded";
		return;
	}
	$att = wp_insert_attachment(['post_mime_type' => 'image/jpeg', 'post_title' => $d['title'], 'post_status' => 'inherit'], $up['file'], $id, true);
	if (is_wp_error($att) || !$att) {
		$log[] = "image failed: attachment for {$d['image']} not created";
		return;
	}
	foreach (['file.php', 'media.php', 'image.php'] as $inc) { // the admin helpers that build the image sizes
		if (is_file(ABSPATH . 'wp-admin/includes/' . $inc)) {
			require_once ABSPATH . 'wp-admin/includes/' . $inc;
		}
	}
	wp_update_attachment_metadata($att, wp_generate_attachment_metadata($att, $up['file']));
	update_post_meta($att, '_wp_attachment_image_alt', $d['alt']);
	set_post_thumbnail($id, $att);
	$log[] = "image: attachment {$att} is the featured image of post {$id}";
}

/** The author of the drafts: the user named ROSMAROPS_DRAFTS_AUTHOR on this site, else its first administrator. */
function rosmarops_drafts_author() {
	$users = get_users(['blog_id' => get_current_blog_id(), 'role__in' => ['administrator', 'editor'], 'orderby' => 'ID', 'order' => 'ASC']);
	foreach ($users as $u) {
		if ($u->display_name === ROSMAROPS_DRAFTS_AUTHOR) {
			return (int) $u->ID;
		}
	}
	foreach ($users as $u) {
		if (in_array('administrator', (array) $u->roles, true)) {
			return (int) $u->ID;
		}
	}
	return 0;
}

/** Runs once per draft on this site. Returns the log lines (also stored), or null when there is nothing to do. */
function rosmarops_drafts_run() {
	$lang = rosmarops_drafts_site_lang();
	if ($lang === null) {
		return null;
	}
	$log    = [];
	$drafts = array_filter(rosmarops_drafts_for($lang, $log), function ($d) {
		return !get_option('rosmarops_draft_' . $d['id'] . '_done');
	});
	if (!$drafts) {
		return null; // nothing pending here (a malformed file is only logged next to a pending draft)
	}
	if (!add_option(ROSMAROPS_DRAFTS_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_DRAFTS_LOCK) < 600) {
			return null; // another request is running it
		}
		update_option(ROSMAROPS_DRAFTS_LOCK, time(), false); // a run that died more than ten minutes ago: take over
	}
	array_unshift($log, "Blog drafts, site {$lang}, " . gmdate('Y-m-d H:i:s') . ' UTC');
	$author = rosmarops_drafts_author();
	foreach ($drafts as $d) {
		$done = 'rosmarops_draft_' . $d['id'] . '_done';
		$taken = get_posts(['name' => $d['slug'], 'post_type' => ['post', 'page'], 'post_status' => 'any', 'numberposts' => 1]);
		$trash = get_posts(['name' => $d['slug'] . '__trashed', 'post_type' => ['post', 'page'], 'post_status' => 'trash', 'numberposts' => 1]);
		if ($taken || $trash) {
			$p = $taken ? $taken[0] : $trash[0];
			$log[] = "skipped: {$d['slug']} already used by {$p->post_type} {$p->ID} ({$p->post_status}); nothing changed";
			update_option($done, gmdate('c'), false);
			continue;
		}
		$id = wp_insert_post([
			'post_type'    => 'post',
			'post_status'  => 'draft', // never anything else: Albert publishes
			'post_author'  => $author,
			'post_title'   => $d['title'],
			'post_name'    => $d['slug'],
			'post_excerpt' => $d['excerpt'],
			'post_content' => $d['html'],
		], true);
		if (is_wp_error($id) || !$id) {
			$log[] = "failed: {$d['slug']} not created";
			continue; // not marked done: it is tried again on the next request
		}
		update_post_meta($id, '_genesis_title', $d['seo_title']);
		update_post_meta($id, '_genesis_description', $d['seo_description']);
		foreach ((array) ($d['translations'] ?? []) as $l => $url) {
			if (isset(ROSMAROPS_DRAFTS_SITES[$l]) && $l !== $lang && is_string($url) && strpos($url, ROSMAROPS_DRAFTS_SITES['en'] . '/') === 0) {
				update_post_meta($id, 'rosmarops_url_' . $l, $url);
			}
		}
		update_option($done, gmdate('c'), false);
		$log[] = "done: {$d['slug']} created as draft, post {$id}, author {$author}";
		rosmarops_drafts_terms($id, $d, $log);
		rosmarops_drafts_image($id, $d, $log);
	}
	update_option(ROSMAROPS_DRAFTS_LOG, $log, false);
	delete_option(ROSMAROPS_DRAFTS_LOCK);
	rosmarops_drafts_write_log($lang, $log);
	return $log;
}

/** Writes the log to wp-content/rosmarops-private/ (closed to the web; created by GTM-94 if missing). */
function rosmarops_drafts_write_log($lang, $log) {
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-blog-drafts: cannot create ' . $dir);
		return;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . '/drafts-' . $lang . '.log', implode("\n", $log) . "\n", FILE_APPEND);
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_drafts_run();
});
