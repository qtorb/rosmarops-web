<?php
// Minimal WordPress stand-in for test_categories_gtm94.py: categories, posts, options and term meta in a JSON file
// ($_ENV GTM94_DB). `php gtm94-stub.php run <home_url>` runs the migration once and prints the log as JSON.
define('ABSPATH', '/');
define('WP_CONTENT_DIR', getenv('GTM94_CONTENT'));
$GLOBALS['db'] = json_decode(file_get_contents(getenv('GTM94_DB')), true);
function db_save() { file_put_contents(getenv('GTM94_DB'), json_encode($GLOBALS['db'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)); }
class WP_Error { public $m; function __construct($c = '', $m = '') { $this->m = $m; } function get_error_message() { return $this->m; } }
function is_wp_error($x) { return $x instanceof WP_Error; }
function add_action(...$a) {}
function wp_doing_ajax() { return false; }
function wp_doing_cron() { return false; }
function home_url() { return $GLOBALS['home']; }
function get_option($k, $d = false) { return $GLOBALS['db']['options'][$k] ?? $d; }
function add_option($k, $v, $x = '', $a = true) { if (array_key_exists($k, $GLOBALS['db']['options'])) return false; $GLOBALS['db']['options'][$k] = $v; return true; }
function update_option($k, $v, $a = null) { $GLOBALS['db']['options'][$k] = $v; return true; }
function delete_option($k) { unset($GLOBALS['db']['options'][$k]); return true; }
function term_obj($t) { return $t ? (object) $t : false; }
function get_term_by($f, $v, $tax) { foreach ($GLOBALS['db']['terms'] as $t) { if ($t[$f] === $v) return term_obj($t); } return false; }
function wp_update_term($id, $tax, $args) {
	foreach ($GLOBALS['db']['terms'] as &$t) { if ($t['term_id'] === $id) { $t = array_merge($t, $args); return ['term_id' => $id]; } }
	return new WP_Error('x', 'no term');
}
function wp_insert_term($name, $tax, $args) {
	$id = 1 + max(array_column($GLOBALS['db']['terms'], 'term_id') ?: [0]);
	$GLOBALS['db']['terms'][] = ['term_id' => $id, 'name' => $name, 'slug' => $args['slug'], 'description' => $args['description']];
	return ['term_id' => $id];
}
function wp_delete_term($id, $tax) { $GLOBALS['db']['terms'] = array_values(array_filter($GLOBALS['db']['terms'], fn($t) => $t['term_id'] !== $id)); return true; }
function clean_term_cache(...$a) {}
function get_posts($q) {
	$out = [];
	foreach ($GLOBALS['db']['posts'] as $p) {
		if (isset($q['name']) && $p['post_name'] !== $q['name']) continue;
		if (isset($q['category']) && !in_array($q['category'], $p['cats'], true)) continue;
		if (($q['post_status'] ?? 'publish') !== 'any' && $p['post_status'] !== ($q['post_status'] ?? 'publish')) continue;
		$out[] = ($q['fields'] ?? '') === 'ids' ? $p['ID'] : (object) $p;
	}
	return array_slice($out, 0, $q['numberposts'] ?? 5);
}
function wp_get_post_categories($id) { foreach ($GLOBALS['db']['posts'] as $p) { if ($p['ID'] === $id) return $p['cats']; } return []; }
function wp_set_post_categories($id, $cats) {
	foreach ($GLOBALS['db']['posts'] as &$p) { if ($p['ID'] === $id) { $p['cats'] = array_values($cats); return $cats; } }
	return false;
}
function get_term_meta($id, $k, $single) { return $GLOBALS['db']['termmeta'][(string) $id][$k] ?? ''; }
function update_term_meta($id, $k, $v) { $GLOBALS['db']['termmeta'][(string) $id][$k] = $v; return true; }
require __DIR__ . '/../mu-plugins/rosmarops-categories-gtm94.php';
[$_, $cmd, $home] = $argv + [null, null, null];
$GLOBALS['home'] = $home;
$log = rosmarops_gtm94_run();
db_save();
echo json_encode($log, JSON_UNESCAPED_UNICODE);
