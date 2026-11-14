<?php
// Minimal WordPress stand-in for test_gtm164_sin_version.py: state in a JSON file (GTM164_DB).
// `php gtm164-stub.php <home_url>` runs the change once and prints the log as JSON.
define('ABSPATH', '/');
define('WP_CONTENT_DIR', getenv('GTM164_CONTENT'));
$GLOBALS['db'] = json_decode(file_get_contents(getenv('GTM164_DB')), true);
function db_save() { file_put_contents(getenv('GTM164_DB'), json_encode($GLOBALS['db'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)); }
function &db() { return $GLOBALS['db']; }
function add_action(...$a) {}
function wp_doing_ajax() { return false; }
function wp_doing_cron() { return false; }
function home_url() { return $GLOBALS['home']; }
function get_option($k, $d = false) { return db()['options'][$k] ?? $d; }
function add_option($k, $v, $x = '', $a = true) { $db = &db(); if (array_key_exists($k, $db['options'])) return false; $db['options'][$k] = $v; return true; }
function update_option($k, $v, $a = null) { $db = &db(); $db['options'][$k] = $v; return true; }
function delete_option($k) { $db = &db(); unset($db['options'][$k]); return true; }
function get_posts($q) {
	$out = [];
	$types = (array) $q['post_type'];
	foreach (db()['posts'] as $p) {
		if ($p['post_name'] === $q['name'] && in_array($p['post_type'], $types, true) && in_array($p['post_status'], (array) $q['post_status'], true)) $out[] = (object) $p;
	}
	return array_slice($out, 0, $q['numberposts']);
}
function add_post_meta($id, $k, $v) { $db = &db(); $db['post_meta'][$id][$k][] = $v; return true; }
function update_post_meta($id, $k, $v) { $db = &db(); $db['post_meta'][$id][$k] = $v; return true; }
function clean_post_cache($id) { $db = &db(); $db['cleaned'][] = $id; }
function wp_update_post(...$a) { throw new Exception('wp_update_post must not be used'); }
class StubWpdb {
	public $posts = 'wp_posts';
	public function update($table, $data, $where) {
		if ($table !== 'wp_posts' || array_keys($data) !== ['post_title', 'post_name'] || array_keys($where) !== ['ID']) throw new Exception('only post_title and post_name by ID');
		$db = &db(); foreach ($db['posts'] as &$p) { if ($p['ID'] === $where['ID']) { $p = array_merge($p, $data); return 1; } }
		return 0;
	}
}
$GLOBALS['wpdb'] = new StubWpdb();
require __DIR__ . '/../mu-plugins/rosmarops-gtm164-sin-version.php';
$GLOBALS['home'] = $argv[1];
$log = rosmarops_gtm164_run();
db_save();
echo json_encode($log, JSON_UNESCAPED_UNICODE);
