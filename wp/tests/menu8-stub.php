<?php
// Minimal WordPress stand-in for test_menu8_sandbox.py: state in a JSON file (MENU8_DB).
// `php menu8-stub.php <home_url>` runs one request and prints the log as JSON.
define('ABSPATH', '/');
define('WP_CONTENT_DIR', getenv('MENU8_CONTENT'));
$GLOBALS['db'] = json_decode(file_get_contents(getenv('MENU8_DB')), true);
function db_save() { file_put_contents(getenv('MENU8_DB'), json_encode($GLOBALS['db'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)); }
function &db() { return $GLOBALS['db']; }
function add_action(...$a) {}
function wp_doing_ajax() { return false; }
function wp_doing_cron() { return false; }
function home_url() { return $GLOBALS['home']; }
function get_option($k, $d = false) { return db()['options'][$k] ?? $d; }
function add_option($k, $v, $x = '', $a = true) { $db = &db(); if (array_key_exists($k, $db['options'])) return false; $db['options'][$k] = $v; return true; }
function update_option($k, $v, $a = null) { $db = &db(); $db['options'][$k] = $v; return true; }
function delete_option($k) { $db = &db(); unset($db['options'][$k]); return true; }
function esc_html($s) { return htmlspecialchars($s, ENT_QUOTES); }
function wp_slash($s) { return addslashes($s); }
function is_wp_error($x) { return false; }
function get_nav_menu_locations() { return db()['locations'] ?? []; }
function wp_get_nav_menu_items($menu, $args = []) {
	$out = [];
	foreach (db()['menu_items'] as $it) { if ($it['menu'] === $menu) $out[] = (object) $it; }
	usort($out, function ($a, $b) { return [$a->menu_order, $a->ID] <=> [$b->menu_order, $b->ID]; });
	// As WordPress does with its default ARRAY_A output: menu_order becomes the display position 1..n, whatever is stored.
	foreach ($out as $i => $o) { $out[$i] = clone $o; $out[$i]->menu_order = $i + 1; }
	return $out;
}
function wp_update_nav_menu_item($menu, $id, $a) {
	$db = &db();
	$new = 1000 + count($db['menu_items']);
	$db['menu_items'][] = ['ID' => $new, 'menu' => $menu, 'url' => $a['menu-item-url'], 'title' => $a['menu-item-title'],
		'menu_order' => $a['menu-item-position'] ?? 0, 'menu_item_parent' => 0, 'type' => $a['menu-item-type']];
	return $new;
}
function get_posts($q) {
	$out = [];
	foreach (db()['posts'] as $p) {
		if ($p['post_name'] === $q['name'] && in_array($p['post_type'], (array) $q['post_type'], true) && in_array($p['post_status'], $q['post_status'], true)) $out[] = (object) $p;
	}
	return $out;
}
function get_post_field($f, $id) { foreach (db()['posts'] as $p) { if ($p['ID'] === $id) return $p[$f]; } return ''; }
function wp_update_post($a, $err = false) {
	$db = &db();
	if (array_key_exists('menu_order', $a)) {
		foreach ($db['menu_items'] as &$it) { if ($it['ID'] === $a['ID']) { $it['menu_order'] = $a['menu_order']; return $a['ID']; } }
		return 0;
	}
	if (array_diff(array_keys($a), ['ID', 'post_content'])) throw new Exception('only the content');
	foreach ($db['posts'] as &$p) { if ($p['ID'] === $a['ID']) { $p['post_content'] = stripslashes($a['post_content']); return $a['ID']; } }
	return 0;
}
require __DIR__ . '/../mu-plugins/rosmarops-menu8-sandbox.php';
$GLOBALS['home'] = $argv[1];
rosmarops_menu8_run();
db_save();
echo json_encode(get_option(ROSMAROPS_MENU8_LOG, []), JSON_UNESCAPED_UNICODE);
