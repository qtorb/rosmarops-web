<?php
// Minimal WordPress stand-in for test_schedule_novedades_0_11.py: state in a JSON file (SCHED5_DB).
// `php sched5-stub.php <home_url> <now_unix>` runs one request (the one-time run and the fallback) and prints the log as JSON.
// time() cannot be overridden in PHP, so the plugin is loaded with time() renamed to sched5_now().
define('ABSPATH', '/');
define('WP_CONTENT_DIR', getenv('SCHED5_CONTENT'));
$GLOBALS['db'] = json_decode(file_get_contents(getenv('SCHED5_DB')), true);
function db_save() { file_put_contents(getenv('SCHED5_DB'), json_encode($GLOBALS['db'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)); }
function &db() { return $GLOBALS['db']; }
function sched5_now() { return (int) $GLOBALS['now']; }
function add_action(...$a) {}
function wp_doing_ajax() { return false; }
function wp_doing_cron() { return false; }
function home_url() { return $GLOBALS['home']; }
function get_option($k, $d = false) { return db()['options'][$k] ?? $d; }
function add_option($k, $v, $x = '', $a = true) { $db = &db(); if (array_key_exists($k, $db['options'])) return false; $db['options'][$k] = $v; return true; }
function update_option($k, $v, $a = null) { $db = &db(); $db['options'][$k] = $v; return true; }
function delete_option($k) { $db = &db(); unset($db['options'][$k]); return true; }
function get_date_from_gmt($gmt) { return (new DateTime($gmt, new DateTimeZone('UTC')))->setTimezone(new DateTimeZone('Europe/Madrid'))->format('Y-m-d H:i:s'); }
function get_posts($q) {
	$out = [];
	foreach (db()['posts'] as $p) {
		if ($p['post_name'] === $q['name'] && $p['post_type'] === $q['post_type'] && in_array($p['post_status'], $q['post_status'], true)) $out[] = (object) $p;
	}
	return $out;
}
function get_post_status($id) { foreach (db()['posts'] as $p) { if ($p['ID'] === $id) return $p['post_status']; } return false; }
function wp_update_post($a, $err) {
	if (array_diff(array_keys($a), ['ID', 'post_status', 'post_date', 'post_date_gmt', 'edit_date'])) throw new Exception('only status and date');
	$db = &db(); foreach ($db['posts'] as &$p) { if ($p['ID'] === $a['ID']) { $p = array_merge($p, array_diff_key($a, ['edit_date' => 1])); return $a['ID']; } }
	return 0;
}
function is_wp_error($x) { return false; }
function wp_publish_post($id) { $db = &db(); foreach ($db['posts'] as &$p) { if ($p['ID'] === $id) $p['post_status'] = 'publish'; } }
$src = file_get_contents(__DIR__ . '/../mu-plugins/rosmarops-schedule-novedades-0-11.php');
eval('?>' . preg_replace('/\btime\(\)/', 'sched5_now()', $src));
$GLOBALS['home'] = $argv[1];
$GLOBALS['now'] = $argv[2];
rosmarops_sched5_run();
rosmarops_sched5_fallback();
db_save();
echo json_encode(get_option(ROSMAROPS_SCHED5_LOG, []), JSON_UNESCAPED_UNICODE);
