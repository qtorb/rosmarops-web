<?php
// Minimal WordPress stand-in for test_gtm103_noindex.py: posts, post meta, terms, term meta and options in a JSON file (GTM103_DB).
// `php gtm103-stub.php <home_url>` loads the retired list, runs the migration once and prints the log as JSON.
define('ABSPATH', '/');
define('WP_CONTENT_DIR', getenv('GTM103_CONTENT'));
$GLOBALS['db'] = json_decode(file_get_contents(getenv('GTM103_DB')), true);
function db_save() { file_put_contents(getenv('GTM103_DB'), json_encode($GLOBALS['db'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)); }
function add_action(...$a) {}
function add_filter(...$a) {}
function wp_doing_ajax() { return false; }
function wp_doing_cron() { return false; }
function home_url() { return $GLOBALS['home']; }
function get_option($k, $d = false) { return $GLOBALS['db']['options'][$k] ?? $d; }
function add_option($k, $v, $x = '', $a = true) { if (array_key_exists($k, $GLOBALS['db']['options'])) return false; $GLOBALS['db']['options'][$k] = $v; return true; }
function update_option($k, $v, $a = null) { $GLOBALS['db']['options'][$k] = $v; return true; }
function delete_option($k) { unset($GLOBALS['db']['options'][$k]); return true; }
function get_posts($q) {
	$out = [];
	foreach ($GLOBALS['db']['posts'] as $p) {
		if ($p['post_type'] === $q['post_type'] && $p['post_status'] === $q['post_status']) $out[] = (object) $p;
	}
	return $out;
}
function get_post_meta($id, $k, $single) { return $GLOBALS['db']['postmeta'][(string) $id][$k] ?? ''; }
function update_post_meta($id, $k, $v) { $GLOBALS['db']['postmeta'][(string) $id][$k] = $v; return true; }
function get_terms($q) { return array_map(fn($t) => (object) $t, $GLOBALS['db']['terms']); }
function get_term_meta($id, $k, $single) { return $GLOBALS['db']['termmeta'][(string) $id][$k] ?? ''; }
function update_term_meta($id, $k, $v) { $GLOBALS['db']['termmeta'][(string) $id][$k] = $v; return true; }
eval('namespace The_SEO_Framework\Sitemap; class Cache { static function clear_sitemap_caches() { $GLOBALS["db"]["options"]["sitemap_cleared"] = "tsf5"; } }');
require __DIR__ . '/../mu-plugins/rosmarops-gtm103-noindex.php';
require __DIR__ . '/../mu-plugins/rosmarops-retired.php';
$GLOBALS['home'] = $argv[1];
$log = rosmarops_gtm103_run();
db_save();
echo json_encode($log, JSON_UNESCAPED_UNICODE);
