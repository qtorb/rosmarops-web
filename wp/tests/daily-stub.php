<?php
// Minimal WordPress stand-in for wp/mu-plugins/rosmarops-daily.php (GTM-23). Test-only: not deployed.
// Network options live in a JSON file (DAILY_STORE), so the CLI seeding and the php -S router share them.
define('ABSPATH', __DIR__ . '/');
define('ROSMAROPS_DAILY_DIR', __DIR__ . '/../daily');
$GLOBALS['__actions'] = [];
function add_action($hook, $cb) { $GLOBALS['__actions'][$hook][] = $cb; }
function do_action($hook) { foreach ($GLOBALS['__actions'][$hook] ?? [] as $cb) { $cb(); } }
function __store() { $f = getenv('DAILY_STORE'); return $f && is_file($f) ? (json_decode(file_get_contents($f), true) ?: []) : []; }
function get_site_option($k, $d = null) { $s = __store(); return array_key_exists($k, $s) ? $s[$k] : $d; }
function update_site_option($k, $v) { $s = __store(); $s[$k] = $v; file_put_contents(getenv('DAILY_STORE'), json_encode($s)); return true; }
function is_main_site() { return true; }
function wp_next_scheduled($h) { return true; }
function wp_schedule_event() { return true; }
require __DIR__ . '/../mu-plugins/rosmarops-daily.php';
