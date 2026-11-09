<?php
// Minimal WordPress stand-in to exercise wp/mu-plugins/rosmarops-downloads.php against a real MySQL/MariaDB.
// Test-only: not deployed.
define('ABSPATH', __DIR__ . '/');
define('ARRAY_A', 'ARRAY_A');
$GLOBALS['__actions'] = [];
$GLOBALS['__routes']  = [];
function add_action($hook, $cb) { $GLOBALS['__actions'][$hook][] = $cb; }
function do_action($hook) { foreach ($GLOBALS['__actions'][$hook] ?? [] as $cb) { $cb(); } }
function register_rest_route($ns, $route, $args) { $GLOBALS['__routes']["/$ns$route"][$args['methods']] = $args; } // like WordPress: one route, several methods
function __return_true() { return true; }
class WP_REST_Response {
	public $data; public $status; public $headers = [];
	public function __construct($data = null, $status = 200) { $this->data = $data; $this->status = $status; }
	public function header($k, $v) { $this->headers[$k] = $v; }
}
class StubWpdb {
	public $base_prefix; public $last_error = ''; private $db; private $suppress = false;
	public function __construct($prefix) {
		$this->base_prefix = $prefix;
		$this->db = new mysqli('127.0.0.1', getenv('DB_USER') ?: 'root', getenv('DB_PASS') ?: '', getenv('DB_NAME') ?: 'wptest');
	}
	public function prepare($q, ...$a) {
		$i = 0;
		return preg_replace_callback('/%s/', function () use (&$i, $a) { return "'" . $this->db->real_escape_string((string) $a[$i++]) . "'"; }, $q);
	}
	public function suppress_errors($s = true) { $old = $this->suppress; $this->suppress = $s; return $old; }
	public function query($q) { $this->last_error = ''; try { $r = $this->db->query($q); } catch (Throwable $e) { $this->last_error = $e->getMessage(); return false; } return $r === false ? false : ($r === true ? $this->db->affected_rows : $r->num_rows); }
	public function get_results($q, $o) { $this->last_error = ''; try { $r = $this->db->query($q); } catch (Throwable $e) { $this->last_error = $e->getMessage(); return []; } return $r ? $r->fetch_all(MYSQLI_ASSOC) : []; } // like WordPress: [] on error, last_error set
	public function get_charset_collate() { return 'DEFAULT CHARSET=utf8mb4'; }
	public function raw() { return $this->db; }
}
$GLOBALS['wpdb'] = new StubWpdb(getenv('DB_PREFIX') ?: 'wptest_');
// GTM-111 visits: the switch, the static pages folder and the published posts come from the test.
define('ROSMAROPS_VISITS_ON', (bool) getenv('VISITS_ON')); // the test decides, whatever the plugin's default
if (getenv('VISITS_DOCROOT')) { define('ROSMAROPS_VISITS_DOCROOT', getenv('VISITS_DOCROOT')); }
// GTM-125 people per day: the test fixes the UTC day; network options live in a real table, like wp_sitemeta.
if (getenv('VISITS_TODAY')) { define('ROSMAROPS_VISITS_TODAY', getenv('VISITS_TODAY')); }
function __opt_table() { return $GLOBALS['wpdb']->base_prefix . 'stub_sitemeta'; }
function __opt_q($sql) { $db = $GLOBALS['wpdb']->raw(); $db->query('CREATE TABLE IF NOT EXISTS `' . __opt_table() . '` (k VARCHAR(191) PRIMARY KEY, v LONGTEXT)'); return $db->query($sql); }
function get_site_option($k, $d = false) { $db = $GLOBALS['wpdb']->raw(); $r = __opt_q("SELECT v FROM `" . __opt_table() . "` WHERE k = '" . $db->real_escape_string($k) . "'"); $row = $r ? $r->fetch_row() : null; return $row ? unserialize($row[0]) : $d; }
function add_site_option($k, $v) { $db = $GLOBALS['wpdb']->raw(); try { return (bool) __opt_q("INSERT INTO `" . __opt_table() . "` VALUES ('" . $db->real_escape_string($k) . "', '" . $db->real_escape_string(serialize($v)) . "')"); } catch (Throwable $e) { return false; } }
function update_site_option($k, $v) { $db = $GLOBALS['wpdb']->raw(); return (bool) __opt_q("REPLACE INTO `" . __opt_table() . "` VALUES ('" . $db->real_escape_string($k) . "', '" . $db->real_escape_string(serialize($v)) . "')"); }
function delete_site_option($k) { $db = $GLOBALS['wpdb']->raw(); return (bool) __opt_q("DELETE FROM `" . __opt_table() . "` WHERE k = '" . $db->real_escape_string($k) . "'"); }
function wp_next_scheduled($hook) { return $GLOBALS['__scheduled'][$hook] ?? false; }
function wp_schedule_event($ts, $rec, $hook) { $GLOBALS['__scheduled'][$hook] = $ts; return true; }
function url_to_postid($url) { return in_array($url, array_filter(explode(' ', (string) getenv('VISITS_POSTS'))), true) ? 7 : 0; }
function wp_enqueue_script(...$a) { $GLOBALS['__enqueued'][] = $a; }
require __DIR__ . '/../mu-plugins/rosmarops-downloads.php';
