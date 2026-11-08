<?php
// Minimal WordPress stand-in for test_category_loop_engineering.py: state in a JSON file (LOOPCAT_DB).
// `php loopcat-stub.php <home_url>` runs the migration once and prints the log as JSON.
define('ABSPATH', '/');
define('WP_CONTENT_DIR', getenv('LOOPCAT_CONTENT'));
define('ROSMAROPS_DRAFTS_DIR', getenv('LOOPCAT_DIR'));
$GLOBALS['db'] = json_decode(file_get_contents(getenv('LOOPCAT_DB')), true);
function db_save() { file_put_contents(getenv('LOOPCAT_DB'), json_encode($GLOBALS['db'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)); }
function &db() { return $GLOBALS['db']; }
class WP_Error {}
function is_wp_error($x) { return $x instanceof WP_Error; }
function add_action(...$a) {}
function wp_doing_ajax() { return false; }
function wp_doing_cron() { return false; }
function home_url() { return $GLOBALS['home']; }
function get_option($k, $d = false) { return db()['options'][$k] ?? $d; }
function add_option($k, $v, $x = '', $a = true) { $db = &db(); if (array_key_exists($k, $db['options'])) return false; $db['options'][$k] = $v; return true; }
function update_option($k, $v, $a = null) { $db = &db(); $db['options'][$k] = $v; return true; }
function delete_option($k) { $db = &db(); unset($db['options'][$k]); return true; }
function get_term_by($f, $v, $tax) { foreach (db()['terms'] as $t) { if ($t['slug'] === $v) return (object) $t; } return false; }
function wp_insert_term($name, $tax, $args) {
	if (getenv('LOOPCAT_TERM_FAIL')) return new WP_Error();
	$db = &db(); $id = 500 + count($db['terms']);
	$db['terms'][] = ['term_id' => $id, 'name' => $name, 'slug' => $args['slug'], 'description' => $args['description']];
	return ['term_id' => $id];
}
function get_term_meta($id, $k, $single) { return db()['term_meta'][$id][$k] ?? ''; }
function update_term_meta($id, $k, $v) { $db = &db(); $db['term_meta'][$id][$k] = $v; return true; }
function get_posts($q) {
	$out = [];
	foreach (db()['posts'] as $p) {
		if (isset($q['category'])) {
			if (in_array($q['category'], $p['cats'], true) && $p['post_status'] === $q['post_status']) $out[] = $p['ID'];
			continue;
		}
		if ($p['post_name'] === $q['name'] && in_array($p['post_status'], (array) $q['post_status'], true)) $out[] = (object) $p;
	}
	return $out;
}
function wp_get_post_categories($id) { foreach (db()['posts'] as $p) { if ($p['ID'] === $id) return $p['cats']; } return []; }
function wp_set_post_categories($id, $cats) { $db = &db(); foreach ($db['posts'] as &$p) { if ($p['ID'] === $id) $p['cats'] = array_values($cats); } return true; }
function has_post_thumbnail($id) { return !empty(db()['thumbs'][$id]); }
function wp_upload_bits($name, $x, $bits) { $db = &db(); $db['uploads'][] = [$name, strlen($bits)]; return ['file' => '/uploads/' . $name, 'error' => false]; }
function wp_insert_attachment($a, $file, $parent, $err) { $db = &db(); $id = 900 + count($db['uploads']); $db['attachments'][$id] = ['file' => $file, 'parent' => $parent] + $a; return $id; }
function wp_generate_attachment_metadata($id, $file) { return ['file' => $file]; }
function wp_update_attachment_metadata($id, $m) { return true; }
function update_post_meta($id, $k, $v) { $db = &db(); $db['post_meta'][$id][$k] = $v; return true; }
function set_post_thumbnail($post, $att) { $db = &db(); $db['thumbs'][$post] = $att; return true; }
function wp_update_post(...$a) { throw new Exception('must not update posts'); }
require __DIR__ . '/../mu-plugins/rosmarops-category-loop-engineering.php';
$GLOBALS['home'] = $argv[1];
$log = rosmarops_loopcat_run();
db_save();
echo json_encode($log, JSON_UNESCAPED_UNICODE);
