<?php
// Minimal WordPress stand-in for test_gtm124_agente.py: state in a JSON file (GTM124_DB).
// `php gtm124-stub.php <home_url>` runs the migration once and prints the log as JSON.
define('ABSPATH', '/');
define('WP_CONTENT_DIR', getenv('GTM124_CONTENT'));
$GLOBALS['db'] = json_decode(file_get_contents(getenv('GTM124_DB')), true);
function db_save() { file_put_contents(getenv('GTM124_DB'), json_encode($GLOBALS['db'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)); }
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
		if ($p['post_name'] === $q['name'] && $p['post_type'] === $q['post_type'] && $p['post_status'] === $q['post_status']) $out[] = (object) $p;
	}
	return $out;
}
function get_page_by_path($path) { foreach (db()['posts'] as $p) { if ($p['post_type'] === 'page' && $p['post_name'] === $path) return (object) $p; } return null; }
function get_post_meta($id, $k, $single) { return db()['post_meta'][$id][$k] ?? ''; }
function update_post_meta($id, $k, $v) { $db = &db(); $db['post_meta'][$id][$k] = $v; return true; }
function clean_post_cache($id) { $db = &db(); $db['cleaned'][] = $id; }
function wp_update_post(...$a) { throw new Exception('wp_update_post must not be used'); }
class StubWpdb {
	public $posts = 'wp_posts';
	public function update($table, $data, $where) {
		if ($table !== 'wp_posts' || array_keys($data) !== ['post_content'] || array_keys($where) !== ['ID']) throw new Exception('only post_content by ID');
		if (getenv('GTM124_WRITE_FAIL')) return false;
		$db = &db(); foreach ($db['posts'] as &$p) { if ($p['ID'] === $where['ID']) { $p['post_content'] = $data['post_content']; return 1; } }
		return 0;
	}
}
$GLOBALS['wpdb'] = new StubWpdb();
require __DIR__ . '/../mu-plugins/rosmarops-gtm124-agente.php';
$GLOBALS['home'] = $argv[1];
$log = rosmarops_gtm124_run();
db_save();
echo json_encode($log, JSON_UNESCAPED_UNICODE);
