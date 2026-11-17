<?php
// Minimal WordPress stand-in for test_slug7_sandbox.py: state in a JSON file (SLUG7_DB).
// `php slug7-stub.php <home_url>` runs one request and prints the log as JSON. Every call to a write function is
// recorded in db.calls, so the test can check that wp_delete_post is never called.
define('ABSPATH', '/');
define('WP_CONTENT_DIR', getenv('SLUG7_CONTENT'));
$GLOBALS['db'] = json_decode(file_get_contents(getenv('SLUG7_DB')), true);
$GLOBALS['db']['calls'] = $GLOBALS['db']['calls'] ?? [];
function db_save() { file_put_contents(getenv('SLUG7_DB'), json_encode($GLOBALS['db'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)); }
function &db() { return $GLOBALS['db']; }
function called($f) { $db = &db(); $db['calls'][] = $f; }
function add_action(...$a) {}
function wp_doing_ajax() { return false; }
function wp_doing_cron() { return false; }
function home_url() { return $GLOBALS['home']; }
function get_option($k, $d = false) { return db()['options'][$k] ?? $d; }
function add_option($k, $v, $x = '', $a = true) { $db = &db(); if (array_key_exists($k, $db['options'])) return false; $db['options'][$k] = $v; return true; }
function update_option($k, $v, $a = null) { $db = &db(); $db['options'][$k] = $v; return true; }
function delete_option($k) { $db = &db(); unset($db['options'][$k]); return true; }
function get_post($id) { foreach (db()['posts'] as $p) { if ($p['ID'] === $id) return (object) $p; } return null; }
function get_posts($q) {
	$out = [];
	foreach (db()['posts'] as $p) {
		if ($p['post_name'] === $q['name'] && in_array($p['post_type'], (array) $q['post_type'], true) && in_array($p['post_status'], $q['post_status'], true)) $out[] = (object) $p;
	}
	return $out;
}
function get_post_field($f, $id) { foreach (db()['posts'] as $p) { if ($p['ID'] === $id) return $p[$f]; } return ''; }
// As WordPress does: the bin keeps the post and frees its slug with «__trashed».
function wp_trash_post($id) {
	called('wp_trash_post');
	$db = &db();
	foreach ($db['posts'] as &$p) { if ($p['ID'] === $id) { $p['post_status'] = 'trash'; $p['post_name'] .= '__trashed'; return (object) $p; } }
	return false;
}
function wp_delete_post(...$a) { called('wp_delete_post'); throw new Exception('never delete'); }
function wp_update_post($a, $err) {
	called('wp_update_post');
	if (array_diff(array_keys($a), ['ID', 'post_name'])) throw new Exception('only the slug');
	$db = &db(); foreach ($db['posts'] as &$p) { if ($p['ID'] === $a['ID']) { $p['post_name'] = $a['post_name']; return $a['ID']; } }
	return 0;
}
function is_wp_error($x) { return false; }
require __DIR__ . '/../mu-plugins/rosmarops-slug7-sandbox.php';
$GLOBALS['home'] = $argv[1];
rosmarops_slug7_run();
db_save();
echo json_encode(get_option(ROSMAROPS_SLUG7_LOG, []), JSON_UNESCAPED_UNICODE);
