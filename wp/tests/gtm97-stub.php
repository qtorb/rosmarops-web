<?php
// Minimal WordPress stand-in for test_gtm97_drafts.py: posts and options in a JSON file (GTM97_DB).
// `php gtm97-stub.php <home_url> [tsf5|tsf4|none]` loads the retired list, runs the migration once and prints the log as JSON.
define('ABSPATH', '/');
define('WP_CONTENT_DIR', getenv('GTM97_CONTENT'));
$GLOBALS['db'] = json_decode(file_get_contents(getenv('GTM97_DB')), true);
function db_save() { file_put_contents(getenv('GTM97_DB'), json_encode($GLOBALS['db'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)); }
class WP_Error { function get_error_message() { return 'x'; } }
function is_wp_error($x) { return $x instanceof WP_Error; }
function add_action(...$a) {}
function wp_doing_ajax() { return false; }
function wp_doing_cron() { return false; }
function wp_redirect(...$a) {}
function home_url() { return $GLOBALS['home']; }
function get_option($k, $d = false) { return $GLOBALS['db']['options'][$k] ?? $d; }
function add_option($k, $v, $x = '', $a = true) { if (array_key_exists($k, $GLOBALS['db']['options'])) return false; $GLOBALS['db']['options'][$k] = $v; return true; }
function update_option($k, $v, $a = null) { $GLOBALS['db']['options'][$k] = $v; return true; }
function delete_option($k) { unset($GLOBALS['db']['options'][$k]); return true; }
function get_posts($q) {
	$out = [];
	foreach ($GLOBALS['db']['posts'] as $p) {
		if ($p['post_name'] !== $q['name'] || !in_array($p['post_type'], (array) $q['post_type'], true)) continue;
		if ($q['post_status'] !== 'any' && $p['post_status'] !== $q['post_status']) continue;
		if (in_array($p['post_status'], ['trash', 'auto-draft'], true)) continue;
		$out[] = (object) $p;
	}
	return $out;
}
function wp_update_post($args, $wp_error = false) {
	foreach ($GLOBALS['db']['posts'] as &$p) { if ($p['ID'] === $args['ID']) { $p['post_status'] = $args['post_status']; return $p['ID']; } }
	return 0;
}
$mode = $argv[2] ?? 'tsf5';
if ($mode === 'tsf5') {
	eval('namespace The_SEO_Framework\Sitemap; class Cache { static function clear_sitemap_caches() { $GLOBALS["db"]["options"]["sitemap_cleared"] = "tsf5"; } }');
}
require __DIR__ . '/../mu-plugins/rosmarops-gtm97-drafts.php';
require __DIR__ . '/../mu-plugins/rosmarops-retired.php';
$GLOBALS['home'] = $argv[1];
$log = rosmarops_gtm97_run();
db_save();
echo json_encode($log, JSON_UNESCAPED_UNICODE);
