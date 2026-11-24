<?php
// Minimal WordPress stand-in for test_gtm121_titulos.py: state in a JSON file (GTM121_DB).
// `php gtm121-stub.php <home_url>` runs the change once and prints the log as JSON.
define('ABSPATH', '/');
define('WP_CONTENT_DIR', getenv('GTM121_CONTENT'));
$GLOBALS['db'] = json_decode(file_get_contents(getenv('GTM121_DB')), true);
function db_save() { file_put_contents(getenv('GTM121_DB'), json_encode($GLOBALS['db'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)); }
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
	foreach (db()['posts'] as $p) {
		if ($p['post_name'] !== $q['name'] || !in_array($p['post_type'], (array) $q['post_type'], true) || !in_array($p['post_status'], (array) $q['post_status'], true)) continue;
		$out[] = (object) $p;
	}
	return array_slice($out, 0, $q['numberposts']);
}
function get_post_meta($id, $k, $single) { return db()['post_meta'][$id][$k] ?? ''; }
function update_post_meta($id, $k, $v) { $db = &db(); $db['post_meta'][$id][$k] = $v; return true; }
function clean_post_cache($id) { $db = &db(); $db['cleaned'][] = $id; }
function wp_update_post(...$a) { throw new Exception('wp_update_post must not be used'); }
class StubWpdb { public function __call($n, $a) { throw new Exception('no direct writes expected: ' . $n); } }
$GLOBALS['wpdb'] = new StubWpdb();
require __DIR__ . '/../mu-plugins/rosmarops-gtm121-titulos.php';
$GLOBALS['home'] = $argv[1];
$log = rosmarops_gtm121_run();
db_save();
echo json_encode($log, JSON_UNESCAPED_UNICODE);
