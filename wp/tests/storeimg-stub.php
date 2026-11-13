<?php
// Minimal WordPress stand-in for test_store_image.py: state in a JSON file (STOREIMG_DB).
// `php storeimg-stub.php <home_url>` runs one request and prints the log as JSON.
define('ABSPATH', '/nonexistent/');
define('WP_CONTENT_DIR', getenv('STOREIMG_CONTENT'));
define('ROSMAROPS_DRAFTS_DIR', getenv('STOREIMG_DRAFTS'));
$GLOBALS['db'] = json_decode(file_get_contents(getenv('STOREIMG_DB')), true);
$GLOBALS['home'] = $argv[1];
function db_save() { file_put_contents(getenv('STOREIMG_DB'), json_encode($GLOBALS['db'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)); }
class WP_Error {}
function is_wp_error($x) { return $x instanceof WP_Error; }
function add_action(...$a) {}
function wp_doing_ajax() { return false; }
function wp_doing_cron() { return false; }
function home_url() { return $GLOBALS['home']; }
function get_option($k, $d = false) { return $GLOBALS['db']['options'][$k] ?? $d; }
function add_option($k, $v, $x = '', $a = true) { if (array_key_exists($k, $GLOBALS['db']['options'])) return false; $GLOBALS['db']['options'][$k] = $v; return true; }
function update_option($k, $v, $a = null) { $GLOBALS['db']['options'][$k] = $v; return true; }
function delete_option($k) { unset($GLOBALS['db']['options'][$k]); return true; }
function get_posts($q) { return array_map(function ($p) { return (object) $p; }, array_values(array_filter($GLOBALS['db']['posts'], function ($p) use ($q) { return $p['post_name'] === $q['name']; }))); }
function get_post_meta($id, $k, $s) { return $GLOBALS['db']['meta'][$id][$k] ?? ''; }
function update_post_meta($id, $k, $v) { $GLOBALS['db']['meta'][$id][$k] = $v; return true; }
function wp_upload_bits($name, $x, $bits) { $f = WP_CONTENT_DIR . '/uploads-' . $name; file_put_contents($f, $bits); return ['file' => $f, 'error' => false]; }
function wp_insert_attachment($a, $file, $parent, $e) { $id = 900 + count($GLOBALS['db']['attachments'] ?? []); $GLOBALS['db']['attachments'][] = ['ID' => $id, 'file' => basename($file), 'parent' => $parent]; return $id; }
function wp_generate_attachment_metadata($id, $file) { return []; }
function wp_update_attachment_metadata($id, $m) { return true; }
function set_post_thumbnail($id, $att) { $GLOBALS['db']['meta'][$id]['_thumbnail_id'] = $att; return true; }
require __DIR__ . '/../mu-plugins/rosmarops-store-image.php';
rosmarops_storeimg_run();
db_save();
echo json_encode(get_option(ROSMAROPS_STOREIMG_LOG, []), JSON_UNESCAPED_UNICODE);
