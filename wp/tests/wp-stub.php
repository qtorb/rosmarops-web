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
if (getenv('VISITS_ON')) { define('ROSMAROPS_VISITS_ON', true); }
if (getenv('VISITS_DOCROOT')) { define('ROSMAROPS_VISITS_DOCROOT', getenv('VISITS_DOCROOT')); }
function url_to_postid($url) { return in_array($url, array_filter(explode(' ', (string) getenv('VISITS_POSTS'))), true) ? 7 : 0; }
function wp_enqueue_script(...$a) { $GLOBALS['__enqueued'][] = $a; }
require __DIR__ . '/../mu-plugins/rosmarops-downloads.php';
