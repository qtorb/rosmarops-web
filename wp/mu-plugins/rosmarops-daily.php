<?php
/**
 * Plugin Name: RosmarOps daily synopsis
 * Description: Daily synopsis of the Observatory (GTM-23): fetches observatory/daily/<date>.json from the public repo qtorb/rosmarops-web, validates it and renders /observatory/daily/ pages and RSS in EN, ES and CA. Data only; no HTML or code is fetched. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_DAILY_RAW   = 'https://raw.githubusercontent.com/qtorb/rosmarops-web/main/observatory/daily/';
const ROSMAROPS_DAILY_MAX   = 102400; // bytes
const ROSMAROPS_DAILY_HOSTS = [
	'anthropic.com', 'claude.com', 'cursor.com', 'openai.com', 'github.com', 'github.blog',
	'antigravity.google', 'nousresearch.com', 'cline.bot', 'continue.dev', 'osv.dev',
	'nvd.nist.gov', 'npmjs.com', 'pypi.org',
];
const ROSMAROPS_DAILY_PREFIX = ['en' => '/observatory/daily/', 'es' => '/es/observatorio/diario/', 'ca' => '/ca/observatori/diari/'];
const ROSMAROPS_DAILY_FEED_ITEMS = 30;

function rosmarops_daily_dir() {
	return defined('ROSMAROPS_DAILY_DIR') ? ROSMAROPS_DAILY_DIR : __DIR__ . '/rosmarops-daily';
}

/** Network-wide storage, so /, /es/ and /ca/ read the same data. */
function rosmarops_daily_get($key, $default = null) {
	return function_exists('get_site_option') ? get_site_option($key, $default) : get_option($key, $default);
}
function rosmarops_daily_set($key, $value) {
	return function_exists('update_site_option') ? update_site_option($key, $value) : update_option($key, $value, false);
}

function rosmarops_daily_texts() {
	static $t = null;
	if ($t === null) {
		$t = json_decode((string) @file_get_contents(rosmarops_daily_dir() . '/i18n.json'), true) ?: [];
	}
	return $t;
}

function rosmarops_daily_t($lang, $key) {
	$t = rosmarops_daily_texts();
	return $t[$lang][$key] ?? '';
}

function rosmarops_daily_date($lang, $iso) {
	[$y, $m, $d] = array_map('intval', explode('-', $iso));
	$months = rosmarops_daily_t($lang, 'common.months');
	return strtr(rosmarops_daily_t($lang, 'common.date'), ['{day}' => (string) $d, '{month}' => $months[$m - 1] ?? '', '{year}' => (string) $y]);
}

function rosmarops_daily_title($lang, $iso) {
	return str_replace('{date}', rosmarops_daily_date($lang, $iso), rosmarops_daily_t($lang, 'daily.title'));
}

// ------------------------------------------------------------------ validation (mirrors daily.v1.schema.json)

function rosmarops_daily_is_day($v) {
	return is_string($v) && preg_match('/^\d{4}-\d{2}-\d{2}$/', $v) && checkdate((int) substr($v, 5, 2), (int) substr($v, 8, 2), (int) substr($v, 0, 4));
}

function rosmarops_daily_is_str($v, $min, $max) {
	return is_string($v) && mb_strlen($v, 'UTF-8') >= $min && mb_strlen($v, 'UTF-8') <= $max;
}

function rosmarops_daily_url_ok($v) {
	if (!is_string($v) || strlen($v) > 500 || !preg_match('#^https://[^\s]+$#', $v)) {
		return false;
	}
	$host = strtolower((string) parse_url($v, PHP_URL_HOST));
	foreach (ROSMAROPS_DAILY_HOSTS as $h) {
		if ($host === $h || substr($host, -strlen('.' . $h)) === '.' . $h) {
			return true;
		}
	}
	return false;
}

function rosmarops_daily_keys_exact($o, $keys) {
	if (!is_array($o)) {
		return false;
	}
	$k = array_keys($o);
	sort($k);
	sort($keys);
	return $k === $keys;
}

/** True if $d is a valid daily file for $date; otherwise a string with the first error. */
function rosmarops_daily_validate($d, $date) {
	if (!rosmarops_daily_keys_exact($d, ['date', 'reviewed_at', 'status', 'items', 'checked', 'held', 'summary_ref'])) {
		return 'top-level keys';
	}
	if ($d['date'] !== $date || !rosmarops_daily_is_day($d['date'])) {
		return 'date';
	}
	if (!is_string($d['reviewed_at']) || !preg_match('/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/', $d['reviewed_at'])) {
		return 'reviewed_at';
	}
	if (!in_array($d['status'], ['published', 'no_changes', 'incomplete'], true)) {
		return 'status';
	}
	if (!is_array($d['items']) || !array_is_list($d['items']) || count($d['items']) > 5) {
		return 'items';
	}
	if (($d['status'] === 'published') !== (count($d['items']) > 0)) {
		return 'items for status';
	}
	foreach ($d['items'] as $it) {
		if (!rosmarops_daily_keys_exact($it, ['source_url', 'source_date', 'subject', 'identifier', 'text'])) {
			return 'item keys';
		}
		if (!rosmarops_daily_url_ok($it['source_url']) || !rosmarops_daily_is_day($it['source_date']) || !rosmarops_daily_is_str($it['subject'], 1, 60)) {
			return 'item source or subject';
		}
		if ($it['identifier'] !== null && !(is_string($it['identifier']) && preg_match('/^(MAL-\d{4}-\d+|GHSA(-[23456789cfghjmpqrvwx]{4}){3}|CVE-\d{4}-\d{4,})$/', $it['identifier']))) {
			return 'item identifier';
		}
		if (!rosmarops_daily_keys_exact($it['text'], ['en', 'es', 'ca'])) {
			return 'item text keys';
		}
		foreach ($it['text'] as $s) {
			if (!rosmarops_daily_is_str($s, 1, 400)) {
				return 'item text';
			}
		}
	}
	if (!is_array($d['checked']) || !array_is_list($d['checked']) || count($d['checked']) < 1 || count($d['checked']) > 40) {
		return 'checked';
	}
	foreach ($d['checked'] as $c) {
		if (!rosmarops_daily_keys_exact($c, ['name', 'url', 'latest_seen', 'latest_date'])
			|| !rosmarops_daily_is_str($c['name'], 1, 80) || !rosmarops_daily_url_ok($c['url'])
			|| !rosmarops_daily_is_str($c['latest_seen'], 0, 40)
			|| !($c['latest_date'] === null || rosmarops_daily_is_day($c['latest_date']))) {
			return 'checked entry';
		}
	}
	if (!is_array($d['held']) || !array_is_list($d['held'])) {
		return 'held';
	}
	if (!is_string($d['summary_ref']) || !preg_match('#^docs/observatorio/\d{4}-\d{2}-\d{2}\.md$#', $d['summary_ref'])) {
		return 'summary_ref';
	}
	return true;
}

/** Store a decoded daily file if valid and not incomplete. Returns true when stored. */
function rosmarops_daily_store($d, $date) {
	$ok = rosmarops_daily_validate($d, $date);
	if ($ok !== true) {
		error_log("rosmarops-daily: $date rejected ($ok)");
		return false;
	}
	if ($d['status'] === 'incomplete') {
		return false;
	}
	// Only what the pages use is kept; `held` stays in the repository.
	$keep = ['date' => $d['date'], 'reviewed_at' => $d['reviewed_at'], 'status' => $d['status'], 'items' => $d['items'], 'checked' => $d['checked']];
	rosmarops_daily_set('rosmarops_daily_' . $date, $keep);
	$dates = (array) rosmarops_daily_get('rosmarops_daily_dates', []);
	$dates[] = $date;
	$dates = array_values(array_unique($dates));
	rsort($dates);
	rosmarops_daily_set('rosmarops_daily_dates', $dates);
	return true;
}

// ------------------------------------------------------------------ fetch (wp-cron, hourly, main site only)

function rosmarops_daily_fetch() {
	$tz = new DateTimeZone('Europe/Madrid');
	$today = new DateTime('now', $tz);
	$dates = [$today->format('Y-m-d'), (clone $today)->modify('-1 day')->format('Y-m-d')];
	foreach ($dates as $date) {
		$res = wp_remote_get(ROSMAROPS_DAILY_RAW . $date . '.json', ['timeout' => 10, 'sslverify' => true, 'redirection' => 0, 'limit_response_size' => ROSMAROPS_DAILY_MAX + 1]);
		if (is_wp_error($res) || (int) wp_remote_retrieve_response_code($res) !== 200) {
			continue;
		}
		$body = (string) wp_remote_retrieve_body($res);
		if ($body === '' || strlen($body) > ROSMAROPS_DAILY_MAX) {
			error_log("rosmarops-daily: $date body empty or too large");
			continue;
		}
		$d = json_decode($body, true);
		if (!is_array($d)) {
			error_log("rosmarops-daily: $date is not JSON");
			continue;
		}
		rosmarops_daily_store($d, $date);
	}
}
add_action('rosmarops_daily_fetch', 'rosmarops_daily_fetch');

add_action('init', function () {
	if (function_exists('is_main_site') && !is_main_site()) {
		return;
	}
	if (!wp_next_scheduled('rosmarops_daily_fetch')) {
		wp_schedule_event(time() + 60, 'hourly', 'rosmarops_daily_fetch');
	}
});

// ------------------------------------------------------------------ rendering

function rosmarops_daily_e($s) {
	return htmlspecialchars((string) $s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function rosmarops_daily_host($url) {
	return (string) parse_url($url, PHP_URL_HOST);
}

function rosmarops_daily_shell($lang, $vals) {
	$shell = (string) @file_get_contents(rosmarops_daily_dir() . "/shell-$lang.html");
	$map = [];
	foreach (['TITLE', 'DESCRIPTION', 'PATH', 'ALT_EN', 'ALT_ES', 'ALT_CA', 'RSS_TITLE', 'RSS_PATH'] as $k) {
		$map["@@$k@@"] = rosmarops_daily_e($vals[$k]);
	}
	$map['@@BODY@@'] = $vals['BODY']; // built from escaped parts below
	return strtr($shell, $map);
}

function rosmarops_daily_hero($lang, $h1) {
	return "<section class=\"hero\">\n"
		. '<p class="obs-brand"><img src="/assets/brand/observatory/observatory-mark.svg" width="64" height="64" alt="">' . rosmarops_daily_e(rosmarops_daily_t($lang, 'site.observatory_brand')) . "</p>\n"
		. '<h1>' . rosmarops_daily_e($h1) . "</h1>\n"
		. '<p class="lead">' . rosmarops_daily_e(rosmarops_daily_t($lang, 'daily.lead')) . "</p>\n"
		. "</section>\n";
}

function rosmarops_daily_day_body($lang, $d) {
	$out = rosmarops_daily_hero($lang, rosmarops_daily_title($lang, $d['date']));
	if ($d['status'] === 'published') {
		$out .= '<ol class="changes box">';
		foreach ($d['items'] as $it) {
			$meta = rosmarops_daily_date($lang, $it['source_date']) . ' · ' . $it['subject'] . ($it['identifier'] ? ' · ' . $it['identifier'] : '');
			$out .= '<li><p class="meta">' . rosmarops_daily_e($meta) . '</p>'
				. '<p>' . rosmarops_daily_e($it['text'][$lang]) . '</p>'
				. '<p class="meta"><a href="' . rosmarops_daily_e($it['source_url']) . '" rel="noopener">' . rosmarops_daily_e(rosmarops_daily_host($it['source_url'])) . '</a></p></li>';
		}
		$out .= "</ol>\n";
	} else {
		$out .= '<p class="empty box">' . rosmarops_daily_e(rosmarops_daily_t($lang, 'daily.empty')) . "</p>\n";
	}
	$out .= '<h2 id="checked">' . rosmarops_daily_e(rosmarops_daily_t($lang, 'daily.checked_h2')) . "</h2>\n";
	$out .= '<ul class="box">';
	foreach ($d['checked'] as $c) {
		$line = '<a href="' . rosmarops_daily_e($c['url']) . '" rel="noopener">' . rosmarops_daily_e($c['name']) . '</a>';
		if ($c['latest_seen'] !== '') {
			$line .= ' · ' . rosmarops_daily_e($c['latest_seen']);
		}
		if ($c['latest_date'] !== null) {
			$line .= ' · ' . rosmarops_daily_e(rosmarops_daily_date($lang, $c['latest_date']));
		}
		$out .= "<li>$line</li>";
	}
	$out .= "</ul>\n";
	$out .= '<p class="disclaimer">' . rosmarops_daily_e(rosmarops_daily_t($lang, 'daily.disclaimer')) . '</p>';
	return $out;
}

function rosmarops_daily_first_line($lang, $d) {
	return $d['status'] === 'published' ? $d['items'][0]['text'][$lang] : rosmarops_daily_t($lang, 'daily.empty');
}

function rosmarops_daily_index_body($lang, $days) {
	$out = rosmarops_daily_hero($lang, rosmarops_daily_t($lang, 'daily.index_h1'));
	$out .= '<ol class="changes box">';
	foreach ($days as $d) {
		$out .= '<li><p class="meta"><a href="' . rosmarops_daily_e(ROSMAROPS_DAILY_PREFIX[$lang] . $d['date'] . '/') . '">' . rosmarops_daily_e(rosmarops_daily_title($lang, $d['date'])) . '</a></p>'
			. '<p>' . rosmarops_daily_e(rosmarops_daily_first_line($lang, $d)) . '</p></li>';
	}
	$out .= "</ol>\n";
	$out .= '<p class="disclaimer">' . rosmarops_daily_e(rosmarops_daily_t($lang, 'daily.disclaimer')) . '</p>';
	return $out;
}

function rosmarops_daily_days($limit = null) {
	$days = [];
	foreach ((array) rosmarops_daily_get('rosmarops_daily_dates', []) as $date) {
		$d = rosmarops_daily_get('rosmarops_daily_' . $date);
		if (is_array($d)) {
			$days[] = $d;
		}
		if ($limit && count($days) >= $limit) {
			break;
		}
	}
	return $days;
}

function rosmarops_daily_feed($lang, $days) {
	$x = fn($s) => htmlspecialchars((string) $s, ENT_XML1 | ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
	$base = 'https://rosmarops.com';
	$out = '<?xml version="1.0" encoding="UTF-8"?>' . "\n" . '<rss version="2.0"><channel>'
		. '<title>' . $x(rosmarops_daily_t($lang, 'daily.rss_title')) . '</title>'
		. '<link>' . $x($base . ROSMAROPS_DAILY_PREFIX[$lang]) . '</link>'
		. '<description>' . $x(rosmarops_daily_t($lang, 'daily.lead')) . '</description>'
		. '<language>' . $lang . '</language>';
	foreach ($days as $d) {
		$url = $base . ROSMAROPS_DAILY_PREFIX[$lang] . $d['date'] . '/';
		$desc = $d['status'] === 'published'
			? implode(' · ', array_map(fn($it) => $it['text'][$lang], $d['items']))
			: rosmarops_daily_t($lang, 'daily.empty');
		$out .= '<item><title>' . $x(rosmarops_daily_title($lang, $d['date'])) . '</title>'
			. '<link>' . $x($url) . '</link><guid isPermaLink="true">' . $x($url) . '</guid>'
			. '<pubDate>' . $x(gmdate('D, d M Y H:i:s', strtotime($d['reviewed_at'])) . ' +0000') . '</pubDate>'
			. '<description>' . $x($desc) . '</description></item>';
	}
	return $out . "</channel></rss>\n";
}

/** Route a request path. Returns [status, headers, body] or null when it is not ours (or the date is unknown: WordPress answers 404). */
function rosmarops_daily_route($path) {
	foreach (ROSMAROPS_DAILY_PREFIX as $lang => $prefix) {
		$bare = rtrim($prefix, '/');
		if ($path === $bare || preg_match('#^' . preg_quote($prefix, '#') . '\d{4}-\d{2}-\d{2}$#', $path)) {
			return [301, ['Location' => 'https://rosmarops.com' . $path . '/', 'Cache-Control' => 'public, max-age=900'], ''];
		}
		if (strpos($path, $prefix) !== 0) {
			continue;
		}
		$rest = substr($path, strlen($prefix));
		$alts = function ($suffix) {
			return ['ALT_EN' => ROSMAROPS_DAILY_PREFIX['en'] . $suffix, 'ALT_ES' => ROSMAROPS_DAILY_PREFIX['es'] . $suffix, 'ALT_CA' => ROSMAROPS_DAILY_PREFIX['ca'] . $suffix];
		};
		$html = ['Content-Type' => 'text/html; charset=UTF-8', 'Cache-Control' => 'public, max-age=900'];
		if ($rest === '') {
			$body = rosmarops_daily_shell($lang, ['TITLE' => rosmarops_daily_t($lang, 'daily.index_h1'), 'DESCRIPTION' => rosmarops_daily_t($lang, 'daily.lead'), 'PATH' => $prefix,
				'RSS_TITLE' => rosmarops_daily_t($lang, 'daily.rss_title'), 'RSS_PATH' => $prefix . 'feed.xml', 'BODY' => rosmarops_daily_index_body($lang, rosmarops_daily_days())] + $alts(''));
			return [200, $html, $body];
		}
		if ($rest === 'feed.xml') {
			return [200, ['Content-Type' => 'application/rss+xml; charset=UTF-8', 'Cache-Control' => 'public, max-age=900'], rosmarops_daily_feed($lang, rosmarops_daily_days(ROSMAROPS_DAILY_FEED_ITEMS))];
		}
		if (preg_match('#^(\d{4}-\d{2}-\d{2})/$#', $rest, $m)) {
			$d = rosmarops_daily_get('rosmarops_daily_' . $m[1]);
			if (!is_array($d)) {
				return null;
			}
			$body = rosmarops_daily_shell($lang, ['TITLE' => rosmarops_daily_title($lang, $d['date']), 'DESCRIPTION' => rosmarops_daily_t($lang, 'daily.lead'), 'PATH' => $prefix . $m[1] . '/',
				'RSS_TITLE' => rosmarops_daily_t($lang, 'daily.rss_title'), 'RSS_PATH' => $prefix . 'feed.xml', 'BODY' => rosmarops_daily_day_body($lang, $d)] + $alts($m[1] . '/'));
			return [200, $html, $body];
		}
		return null;
	}
	return null;
}

// Answer before WordPress resolves the request, as rosmarops-downloads.php does. GET and HEAD only.
add_action('muplugins_loaded', function () {
	$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
	if ($method !== 'GET' && $method !== 'HEAD') {
		return;
	}
	$path = parse_url((string) ($_SERVER['REQUEST_URI'] ?? ''), PHP_URL_PATH);
	if (!is_string($path)) {
		return;
	}
	$r = rosmarops_daily_route($path);
	if ($r === null) {
		return;
	}
	[$status, $headers, $body] = $r;
	http_response_code($status);
	foreach ($headers as $k => $v) {
		header("$k: $v");
	}
	if ($method === 'GET') {
		echo $body;
	}
	exit;
});
