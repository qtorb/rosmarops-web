<?php
// Minimal WordPress stand-in for test_blog_drafts.py: posts, meta, users and options in a JSON file (DRAFTS_DB).
// `php drafts-stub.php <home_url>` runs the drafts once and prints the log as JSON.
define('ABSPATH', '/');
define('WP_CONTENT_DIR', getenv('DRAFTS_CONTENT'));
define('ROSMAROPS_DRAFTS_DIR', getenv('DRAFTS_DIR'));
$GLOBALS['db'] = json_decode(file_get_contents(getenv('DRAFTS_DB')), true);
function db_save() { file_put_contents(getenv('DRAFTS_DB'), json_encode($GLOBALS['db'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)); }
class WP_Error { function get_error_message() { return 'x'; } }
function is_wp_error($x) { return $x instanceof WP_Error; }
function add_action(...$a) {}
function wp_doing_ajax() { return false; }
function wp_doing_cron() { return false; }
function home_url() { return $GLOBALS['home']; }
function get_current_blog_id() { return 1; }
function get_option($k, $d = false) { return $GLOBALS['db']['options'][$k] ?? $d; }
function add_option($k, $v, $x = '', $a = true) { if (array_key_exists($k, $GLOBALS['db']['options'])) return false; $GLOBALS['db']['options'][$k] = $v; return true; }
function update_option($k, $v, $a = null) { $GLOBALS['db']['options'][$k] = $v; return true; }
function delete_option($k) { unset($GLOBALS['db']['options'][$k]); return true; }
function get_users($q) { return array_map(function ($u) { return (object) $u; }, $GLOBALS['db']['users']); }
function get_posts($q) {
	$out = [];
	foreach ($GLOBALS['db']['posts'] as $p) {
		if ($p['post_name'] !== $q['name'] || !in_array($p['post_type'], (array) $q['post_type'], true)) continue;
		if ($q['post_status'] === 'any' && in_array($p['post_status'], ['trash', 'auto-draft'], true)) continue;
		if ($q['post_status'] !== 'any' && $p['post_status'] !== $q['post_status']) continue;
		$out[] = (object) $p;
	}
	return $out;
}
function wp_insert_post($args, $wp_error = false) {
	if (getenv('DRAFTS_FAIL')) return new WP_Error();
	$id = count($GLOBALS['db']['posts']) + 100;
	$GLOBALS['db']['posts'][] = ['ID' => $id] + $args;
	return $id;
}
function update_post_meta($id, $k, $v) { $GLOBALS['db']['meta'][$id][$k] = $v; return true; }
require __DIR__ . '/../mu-plugins/rosmarops-blog-drafts.php';
$GLOBALS['home'] = $argv[1];
$log = rosmarops_drafts_run();
db_save();
echo json_encode($log, JSON_UNESCAPED_UNICODE);
