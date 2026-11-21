<?php
// Minimal WordPress stand-in for test_papelera_0_16.py: state in a JSON file (BIN016_DB).
// `php bin016-stub.php <home_url>` runs one request and prints the log as JSON. Every call to a write function is
// recorded in db.calls, so the test can check that wp_delete_post is never called.
define('ABSPATH', '/');
define('WP_CONTENT_DIR', getenv('BIN016_CONTENT'));
$GLOBALS['db'] = json_decode(file_get_contents(getenv('BIN016_DB')), true);
$GLOBALS['db']['calls'] = $GLOBALS['db']['calls'] ?? [];
function db_save() { file_put_contents(getenv('BIN016_DB'), json_encode($GLOBALS['db'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)); }
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
function get_post_field($f, $id) { foreach (db()['posts'] as $p) { if ($p['ID'] === $id) return $p[$f]; } return ''; }
// As WordPress does: the bin keeps the post and frees its slug with «__trashed».
function wp_trash_post($id) {
	called('wp_trash_post');
	$db = &db();
	foreach ($db['posts'] as &$p) { if ($p['ID'] === $id) { $p['post_status'] = 'trash'; $p['post_name'] .= '__trashed'; return (object) $p; } }
	return false;
}
function wp_delete_post(...$a) { called('wp_delete_post'); throw new Exception('never delete'); }
function wp_update_post(...$a) { called('wp_update_post'); throw new Exception('never update'); }
require __DIR__ . '/../mu-plugins/rosmarops-papelera-0-16.php';
$GLOBALS['home'] = $argv[1];
rosmarops_bin016_run();
db_save();
echo json_encode(get_option(ROSMAROPS_BIN016_LOG, []), JSON_UNESCAPED_UNICODE);
