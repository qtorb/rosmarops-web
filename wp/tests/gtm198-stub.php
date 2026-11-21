<?php
// Minimal WordPress stand-in for test_gtm198_enlace.py: state in a JSON file (GTM198_DB).
// `php gtm198-stub.php <home_url>` runs the change once and prints the log as JSON.
define('ABSPATH', '/');
define('WP_CONTENT_DIR', getenv('GTM198_CONTENT'));
$GLOBALS['db'] = json_decode(file_get_contents(getenv('GTM198_DB')), true);
function db_save() { file_put_contents(getenv('GTM198_DB'), json_encode($GLOBALS['db'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)); }
function &db() { return $GLOBALS['db']; }
function add_action(...$a) {}
function wp_doing_ajax() { return false; }
function wp_doing_cron() { return false; }
function home_url() { return $GLOBALS['home']; }
function get_option($k, $d = false) { return db()['options'][$k] ?? $d; }
function add_option($k, $v, $x = '', $a = true) { $db = &db(); if (array_key_exists($k, $db['options'])) return false; $db['options'][$k] = $v; return true; }
function update_option($k, $v, $a = null) { $db = &db(); $db['options'][$k] = $v; return true; }
function delete_option($k) { $db = &db(); unset($db['options'][$k]); return true; }
function get_post($id) { foreach (db()['posts'] as $p) { if ($p['ID'] === (int) $id) return (object) $p; } return null; }
function get_posts($q) {
	$out = [];
	foreach (db()['posts'] as $p) {
		if ($p['post_name'] !== $q['name'] || !in_array($p['post_type'], (array) $q['post_type'], true) || !in_array($p['post_status'], (array) $q['post_status'], true)) continue;
		if (isset($q['post_parent']) && (int) ($p['post_parent'] ?? 0) !== (int) $q['post_parent']) continue;
		$out[] = (object) $p;
	}
	return array_slice($out, 0, $q['numberposts']);
}
function get_users($q) { return array_map(function ($u) { return (object) $u; }, db()['users'] ?? []); }
function get_current_blog_id() { return 1; }
function wp_insert_post($a, $err = false) {
	$db = &db(); $id = 9000 + count($db['posts']);
	$db['posts'][] = array_merge(['ID' => $id, 'post_parent' => 0], $a);
	return $id;
}
function is_wp_error($x) { return false; }
function update_post_meta($id, $k, $v) { $db = &db(); $db['post_meta'][$id][$k] = $v; return true; }
function clean_post_cache($id) { $db = &db(); $db['cleaned'][] = $id; }
function current_time($t) { return '2026-11-18 19:00:00'; }
function get_gmt_from_date($d) { return '2026-11-18 18:00:00'; }
function wp_update_post(...$a) { throw new Exception('wp_update_post must not be used'); }
class StubWpdb {
	public $posts = 'wp_posts';
	public function update($table, $data, $where) {
		$ok = [['post_content']];
		if ($table !== 'wp_posts' || !in_array(array_keys($data), $ok, true) || array_keys($where) !== ['ID']) throw new Exception('unexpected write');
		$db = &db(); foreach ($db['posts'] as &$p) { if ($p['ID'] === $where['ID']) { $p = array_merge($p, $data); return 1; } }
		return 0;
	}
}
$GLOBALS['wpdb'] = new StubWpdb();
require __DIR__ . '/../mu-plugins/rosmarops-gtm198-enlace.php';
$GLOBALS['home'] = $argv[1];
$log = rosmarops_gtm198_run();
db_save();
echo json_encode($log, JSON_UNESCAPED_UNICODE);
