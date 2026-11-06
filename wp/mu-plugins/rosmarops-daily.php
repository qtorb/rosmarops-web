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
	'kiro.dev', 'devin.ai', 'visualstudio.com', 'cisa.gov',
	'dev.meta.ai', 'docs.n8n.io', // F29 Muse Code and F31 n8n (GTM-90)
	'trae.cn', 'moonshotai.github.io', 'codebuddy.cn', 'qoder.cn', // F32-F36 (GTM-93)
];
const ROSMAROPS_DAILY_PREFIX = ['en' => '/observatory/daily/', 'es' => '/es/observatorio/diario/', 'ca' => '/ca/observatori/diari/'];
const ROSMAROPS_DAILY_FEED_ITEMS = 30;
// GTM-89: the agent files, read from the same public repository, for the security changes shown on the Observatory.
const ROSMAROPS_AGENTS_RAW = 'https://raw.githubusercontent.com/qtorb/rosmarops-web/main/observatory/data/agents/';
const ROSMAROPS_AGENTS_MAX = 524288; // bytes per agent file
const ROSMAROPS_CATEGORIES = ['permissions', 'approval_mode', 'sandbox', 'default_value', 'config_path_or_format', 'mcp', 'hooks', 'instructions', 'credentials', 'telemetry', 'data_destination', 'agent_scope'];

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
	$keys = ['date', 'reviewed_at', 'status', 'items', 'checked', 'held', 'summary_ref'];
	if (is_array($d) && array_key_exists('not_checked', $d)) {
		$keys[] = 'not_checked';
	}
	if (!rosmarops_daily_keys_exact($d, $keys)) {
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
	if (($d['status'] === 'published' && count($d['items']) === 0) || ($d['status'] === 'no_changes' && count($d['items']) > 0)) {
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
	if (!is_array($d['checked']) || !array_is_list($d['checked']) || count($d['checked']) > 40
		|| ($d['status'] !== 'incomplete' && count($d['checked']) < 1)) {
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
	if (array_key_exists('not_checked', $d)) {
		if (!is_array($d['not_checked']) || !array_is_list($d['not_checked']) || count($d['not_checked']) > 40) {
			return 'not_checked';
		}
		foreach ($d['not_checked'] as $n) {
			if (!rosmarops_daily_is_str($n, 1, 80)) {
				return 'not_checked entry';
			}
		}
	}
	if ($d['status'] === 'incomplete' && (!array_key_exists('not_checked', $d) || count($d['not_checked']) < 1)) {
		return 'not_checked for status';
	}
	if (!is_array($d['held']) || !array_is_list($d['held'])) {
		return 'held';
	}
	if (!is_string($d['summary_ref']) || !preg_match('#^docs/observatorio/\d{4}-\d{2}-\d{2}\.md$#', $d['summary_ref'])) {
		return 'summary_ref';
	}
	return true;
}

/** Store a decoded daily file if valid. Returns true when stored. */
function rosmarops_daily_store($d, $date) {
	$ok = rosmarops_daily_validate($d, $date);
	if ($ok !== true) {
		error_log("rosmarops-daily: $date rejected ($ok)");
		return false;
	}
	// Only what the pages use is kept; `held` stays in the repository.
	$keep = ['date' => $d['date'], 'reviewed_at' => $d['reviewed_at'], 'status' => $d['status'], 'items' => $d['items'], 'checked' => $d['checked'], 'not_checked' => $d['not_checked'] ?? []];
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
add_action('rosmarops_daily_fetch', 'rosmarops_agents_fetch');

// ------------------------------------------------------------------ agent files (GTM-89)

/** A prose object {en, es?, ca?} as in observatory.v1 $defs/text. */
function rosmarops_agents_is_text($v) {
	if (!is_array($v) || !isset($v['en']) || array_diff(array_keys($v), ['en', 'es', 'ca'])) {
		return false;
	}
	foreach ($v as $s) {
		if (!is_string($s) || mb_strlen($s) < 1 || mb_strlen($s) > 280) {
			return false;
		}
	}
	return true;
}

/** One entry of changes[] as in observatory.v1 (required keys, no extra keys, enums, formats). */
function rosmarops_agents_change_ok($c) {
	$keys = ['id', 'version', 'date', 'category', 'before', 'after', 'source', 'verified', 'rosmarops_impact', 'correction'];
	if (!is_array($c) || array_diff(array_keys($c), $keys)) {
		return false;
	}
	foreach (['id', 'date', 'category', 'before', 'after', 'source', 'verified', 'rosmarops_impact'] as $k) {
		if (!array_key_exists($k, $c)) {
			return false;
		}
	}
	if (!is_string($c['id']) || !preg_match('/^chg-[a-z0-9-]{1,60}$/', $c['id'])) {
		return false;
	}
	if (isset($c['version']) && (!is_string($c['version']) || mb_strlen($c['version']) > 40)) {
		return false;
	}
	if (!rosmarops_daily_is_day($c['date']) || !in_array($c['category'], ROSMAROPS_CATEGORIES, true)) {
		return false;
	}
	if (!rosmarops_agents_is_text($c['before']) || !rosmarops_agents_is_text($c['after'])) {
		return false;
	}
	$src = $c['source'];
	if (!rosmarops_daily_keys_exact($src, ['url', 'official', 'accessed_at']) || !is_string($src['url']) || strpos($src['url'], 'https://') !== 0
		|| filter_var($src['url'], FILTER_VALIDATE_URL) === false || !is_bool($src['official']) || !rosmarops_daily_is_day($src['accessed_at'])) {
		return false;
	}
	$v = $c['verified'];
	if (!rosmarops_daily_keys_exact($v, ['by', 'at', 'how']) || !in_array($v['by'], ['advisor', 'writer'], true) || !rosmarops_daily_is_day($v['at'])
		|| !in_array($v['how'], ['official_doc', 'official_changelog', 'lab_observation'], true)) {
		return false;
	}
	if (!in_array($c['rosmarops_impact'], ['none', 'knowledge', 'rule'], true)) {
		return false;
	}
	if (isset($c['correction']) && (!rosmarops_daily_keys_exact($c['correction'], ['at', 'reason']) || !rosmarops_daily_is_day($c['correction']['at'])
		|| !rosmarops_agents_is_text($c['correction']['reason']))) {
		return false;
	}
	return true;
}

/** What the pages need from an agent file ({agent: {id, name}, changes}), or null if it does not match observatory.v1 there. */
function rosmarops_agents_validate($a, $id) {
	if (!is_array($a) || !is_array($a['agent'] ?? null) || ($a['agent']['id'] ?? null) !== $id
		|| !is_string($a['agent']['name'] ?? null) || mb_strlen($a['agent']['name']) < 1 || mb_strlen($a['agent']['name']) > 60
		|| !is_array($a['changes'] ?? null) || !array_is_list($a['changes'])) {
		return null;
	}
	foreach ($a['changes'] as $c) {
		if (!rosmarops_agents_change_ok($c)) {
			return null;
		}
	}
	return ['agent' => ['id' => $id, 'name' => $a['agent']['name']], 'changes' => $a['changes']];
}

/** Store a validated agent; an invalid file keeps what was stored before. */
function rosmarops_agents_store($a, $id) {
	$v = rosmarops_agents_validate($a, $id);
	if ($v === null) {
		error_log("rosmarops-daily: agent $id does not validate; keeping the previous copy");
		return false;
	}
	rosmarops_daily_set('rosmarops_agent_' . $id, $v);
	return true;
}

function rosmarops_agents_ids() {
	return (array) (rosmarops_daily_texts()['_agents'] ?? []);
}

function rosmarops_agents_fetch() {
	foreach (rosmarops_agents_ids() as $id) {
		if (!is_string($id) || !preg_match('/^[a-z0-9][a-z0-9-]{1,40}$/', $id)) {
			continue;
		}
		$res = wp_remote_get(ROSMAROPS_AGENTS_RAW . $id . '.json', ['timeout' => 10, 'sslverify' => true, 'redirection' => 0, 'limit_response_size' => ROSMAROPS_AGENTS_MAX + 1]);
		if (is_wp_error($res) || (int) wp_remote_retrieve_response_code($res) !== 200) {
			continue;
		}
		$body = (string) wp_remote_retrieve_body($res);
		if ($body === '' || strlen($body) > ROSMAROPS_AGENTS_MAX) {
			error_log("rosmarops-daily: agent $id body empty or too large");
			continue;
		}
		rosmarops_agents_store(json_decode($body, true), $id);
	}
}

/** Every agent, or null while any of them has not been stored yet (the pages then keep their static HTML). */
function rosmarops_agents_all() {
	$all = [];
	foreach (rosmarops_agents_ids() as $id) {
		$a = rosmarops_daily_get('rosmarops_agent_' . $id);
		if (!is_array($a)) {
			return null;
		}
		$all[$id] = $a;
	}
	return $all ?: null;
}

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
	if (count($d['items']) > 0) {
		$out .= '<ol class="changes box">';
		foreach ($d['items'] as $it) {
			$meta = rosmarops_daily_date($lang, $it['source_date']) . ' · ' . $it['subject'] . ($it['identifier'] ? ' · ' . $it['identifier'] : '');
			$out .= '<li><p class="meta">' . rosmarops_daily_e($meta) . '</p>'
				. '<p>' . rosmarops_daily_e($it['text'][$lang]) . '</p>'
				. '<p class="meta"><a href="' . rosmarops_daily_e($it['source_url']) . '" rel="noopener">' . rosmarops_daily_e(rosmarops_daily_host($it['source_url'])) . '</a></p></li>';
		}
		$out .= "</ol>\n";
	}
	if ($d['status'] === 'incomplete') {
		$out .= '<p class="empty box">' . rosmarops_daily_e(rosmarops_daily_partial($lang, $d)) . "</p>\n";
	} elseif (count($d['items']) === 0) {
		$out .= '<p class="empty box">' . rosmarops_daily_e(rosmarops_daily_t($lang, 'daily.empty')) . "</p>\n";
	}
	$out .= '<h2 id="checked">' . rosmarops_daily_e(rosmarops_daily_t($lang, 'daily.checked_h2')) . "</h2>\n";
	$out .= '<ul class="box">';
	foreach (rosmarops_daily_sources($d) as $c) {
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

/** GTM-74: an entry pointing at the internal repository is not a source: it is neither listed nor counted. */
function rosmarops_daily_is_internal($c) {
	return is_array($c) && is_string($c['url'] ?? null) && strpos($c['url'], 'https://github.com/qtorb/rosmarops-vigil/') === 0;
}

function rosmarops_daily_sources($d) {
	return array_values(array_filter((array) $d['checked'], function ($c) {
		return !rosmarops_daily_is_internal($c);
	}));
}

/** The incomplete-day sentence (GTM-48): partial with items, partial_empty without, none_checked when nothing was checked. */
function rosmarops_daily_partial($lang, $d) {
	$n = count(rosmarops_daily_sources($d));
	$nc = (array) ($d['not_checked'] ?? []);
	$key = count($d['items']) > 0 ? 'daily.partial' : ($n > 0 ? 'daily.partial_empty' : 'daily.none_checked');
	return strtr(rosmarops_daily_t($lang, $key), ['{n}' => (string) $n, '{total}' => (string) ($n + count($nc)), '{names}' => implode(', ', $nc)]);
}

function rosmarops_daily_first_line($lang, $d) {
	if (count($d['items']) > 0) {
		return $d['items'][0]['text'][$lang];
	}
	return $d['status'] === 'incomplete' ? rosmarops_daily_partial($lang, $d) : rosmarops_daily_t($lang, 'daily.empty');
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

/** «Today in the Observatory» (GTM-88): the block for the Observatory index, from the latest stored day. Every text escaped. */
function rosmarops_daily_today($lang, $d) {
	$checked = strtr(rosmarops_daily_t($lang, 'index.today_checked'), ['{date}' => rosmarops_daily_date($lang, $d['date']), '{checked}' => (string) count(rosmarops_daily_sources($d))]);
	$out = '<p class="note">' . rosmarops_daily_e($checked) . "</p>\n";
	if ($d['status'] === 'incomplete') {
		$out .= '<p class="note">' . rosmarops_daily_e(rosmarops_daily_t($lang, 'index.today_incomplete')) . "</p>\n";
	}
	$items = array_slice((array) $d['items'], 0, 5);
	if (count($items) > 0) {
		$out .= '<ol class="changes box">';
		foreach ($items as $it) {
			$out .= '<li><p>' . rosmarops_daily_e($it['text'][$lang]) . '</p>'
				. '<p class="meta">' . rosmarops_daily_e($it['subject'] . ' · ' . rosmarops_daily_date($lang, $it['source_date']) . ' · ')
				. '<a href="' . rosmarops_daily_e($it['source_url']) . '" rel="noopener">' . rosmarops_daily_e(rosmarops_daily_t($lang, 'index.today_source')) . '</a></p></li>';
		}
		$out .= "</ol>\n";
	} else {
		$out .= '<p class="empty box">' . rosmarops_daily_e(rosmarops_daily_t($lang, 'index.today_empty')) . "</p>\n";
	}
	return $out;
}

// ------------------------------------------------------------------ security changes, as observatory/build.py renders them (GTM-89)

/** [value, lang attribute]: EN with lang="en" when the language is missing (build.py loc()). */
function rosmarops_agents_loc($text, $lang) {
	if (!empty($text[$lang])) {
		return [$text[$lang], ''];
	}
	return [$text['en'], ' lang="en"'];
}

function rosmarops_agents_published($a) {
	if (!in_array($a['agent']['id'], (array) (rosmarops_daily_texts()['_published'] ?? []), true)) {
		return false;
	}
	foreach ($a['changes'] as $c) {
		foreach (array_merge([$c['before'], $c['after']], isset($c['correction']) ? [$c['correction']['reason']] : []) as $t) {
			if (empty($t['en']) || empty($t['es']) || empty($t['ca'])) {
				return false;
			}
		}
	}
	return true;
}

function rosmarops_agents_cmp($x, $y) {
	return [$y['date'], $y['id']] <=> [$x['date'], $x['id']]; // newest first, as build.py sorts by (date, id) reversed
}

function rosmarops_agents_change_item($lang, $a, $c, $with_agent) {
	$e = 'rosmarops_daily_e';
	$t = fn($k) => rosmarops_daily_t($lang, $k);
	$cat = $t('category.' . $c['category']);
	$date = rosmarops_daily_date($lang, $c['date']);
	if ($with_agent) {
		$label = $a['agent']['name'] . (!empty($c['version']) ? ' ' . $c['version'] : '');
		$meta = $e($date) . ' · ' . $e($label) . ' · ' . $e($cat);
	} elseif (!empty($c['version'])) {
		$meta = $e(strtr($t('agent.change_meta'), ['{date}' => $date, '{version}' => $c['version'], '{category}' => $cat]));
	} else {
		$meta = $e(strtr($t('agent.change_meta_noversion'), ['{date}' => $date, '{category}' => $cat]));
	}
	if (isset($c['correction'])) {
		$meta .= ' · ' . $e(strtr($t('agent.corrected'), ['{date}' => rosmarops_daily_date($lang, $c['correction']['at']), '{reason}' => rosmarops_agents_loc($c['correction']['reason'], $lang)[0]]));
	}
	$src = $c['source']['official'] ? $t('agent.source_official') : $t('agent.source_rosmarops');
	[$before, $bl] = rosmarops_agents_loc($c['before'], $lang);
	[$after, $al] = rosmarops_agents_loc($c['after'], $lang);
	$vat = rosmarops_daily_date($lang, $c['verified']['at']);
	if ($c['verified']['by'] === 'writer' && in_array($c['verified']['how'], ['official_changelog', 'official_doc'], true)) {
		$verified = strtr($t('agent.verified_writer_' . $c['verified']['how']), ['{date}' => $vat]);
	} else {
		$verified = strtr($t('agent.verified'), ['{date}' => $vat, '{how}' => $t('how.' . $c['verified']['how'])]);
	}
	$name_link = '';
	if ($with_agent && rosmarops_agents_published($a)) {
		$path = (rosmarops_daily_texts()['_index_paths'][$lang] ?? '') . $a['agent']['id'] . '/';
		$name_link = ' <a href="' . $e($path) . '">' . $e($a['agent']['name']) . '</a> ·';
	}
	return '<li>'
		. '<p class="meta">' . $meta . '</p>'
		. '<p><strong>' . $e($t('agent.before')) . '</strong> <span' . $bl . '>' . $e($before) . '</span></p>'
		. '<p><strong>' . $e($t('agent.after')) . '</strong> <span' . $al . '>' . $e($after) . '</span></p>'
		. '<p class="meta">' . $e($verified) . $name_link . ' <a href="' . $e($c['source']['url']) . '" rel="noopener">' . $e($src) . '</a></p>'
		. '</li>';
}

/** «Latest security changes» on the Observatory index: the 10 newest across agents. */
function rosmarops_agents_changes_html($lang, $all) {
	$rows = [];
	foreach ($all as $a) {
		foreach ($a['changes'] as $c) {
			$rows[] = ['date' => $c['date'], 'id' => $c['id'], 'c' => $c, 'a' => $a];
		}
	}
	usort($rows, 'rosmarops_agents_cmp');
	$rows = array_slice($rows, 0, 10);
	$line = rosmarops_agents_last_check_html($lang);
	if (!$rows) {
		return $line . '<p class="empty box">' . rosmarops_daily_e(rosmarops_daily_t($lang, 'index.changes_empty')) . '</p>';
	}
	return $line . '<ol class="changes box">' . implode('', array_map(fn($r) => rosmarops_agents_change_item($lang, $r['a'], $r['c'], true), $rows)) . '</ol>';
}

/** GTM-90: «Checked every day. Last check: {date}.» under «Latest security changes», from the newest stored daily.
 * Styled inline like the date on the cards (.changes .meta), so the static pages need no deploy. Empty with no daily. */
function rosmarops_agents_last_check_html($lang) {
	$days = rosmarops_daily_days(1);
	if (!$days) {
		return '';
	}
	$text = strtr(rosmarops_daily_t($lang, 'index.last_check'), ['{date}' => rosmarops_daily_date($lang, $days[0]['date'])]);
	return '<p class="meta last-check" style="margin:0 0 12px;font-size:14px;color:var(--muted)">' . rosmarops_daily_e($text) . '</p>';
}

/** The «Latest security change» cells: one span per agent, placed by today.js into td[data-last]. */
function rosmarops_agents_last_html($lang, $all) {
	$out = '';
	foreach ($all as $id => $a) {
		$changes = $a['changes'];
		usort($changes, 'rosmarops_agents_cmp');
		$text = $changes
			? rosmarops_daily_e(rosmarops_daily_date($lang, $changes[0]['date'])) . ' · ' . rosmarops_daily_e(rosmarops_daily_t($lang, 'category.' . $changes[0]['category']))
			: rosmarops_daily_e(rosmarops_daily_t($lang, 'index.no_change'));
		$out .= '<span data-agent="' . rosmarops_daily_e($id) . '">' . $text . '</span>';
	}
	return $out;
}

/** An agent page's history, newest first. */
function rosmarops_agents_history_html($lang, $a) {
	$changes = $a['changes'];
	usort($changes, 'rosmarops_agents_cmp');
	if (!$changes) {
		return '<p class="empty box">' . rosmarops_daily_e(rosmarops_daily_t($lang, 'agent.history_empty')) . '</p>';
	}
	return '<ol class="changes box">' . implode('', array_map(fn($c) => rosmarops_agents_change_item($lang, $a, $c, false), $changes)) . '</ol>';
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
		$desc = count($d['items']) > 0
			? implode(' · ', array_map(fn($it) => $it['text'][$lang], $d['items']))
			: ($d['status'] === 'incomplete' ? rosmarops_daily_partial($lang, $d) : rosmarops_daily_t($lang, 'daily.empty'));
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
		if ($rest === 'today.html') {
			$days = rosmarops_daily_days(1);
			if (!$days) {
				return [404, ['Content-Type' => 'text/plain; charset=UTF-8', 'Cache-Control' => 'public, max-age=900', 'X-Robots-Tag' => 'noindex'], ''];
			}
			return [200, $html + ['X-Robots-Tag' => 'noindex'], rosmarops_daily_today($lang, $days[0])];
		}
		if ($rest === 'changes.html' || $rest === 'last-change.html' || preg_match('#^history-([a-z0-9][a-z0-9-]{1,40})\.html$#', $rest, $hm)) {
			$miss = [404, ['Content-Type' => 'text/plain; charset=UTF-8', 'Cache-Control' => 'public, max-age=900', 'X-Robots-Tag' => 'noindex'], ''];
			$all = rosmarops_agents_all();
			if ($all === null) {
				return $miss;
			}
			if ($rest === 'changes.html') {
				$body = rosmarops_agents_changes_html($lang, $all);
			} elseif ($rest === 'last-change.html') {
				$body = rosmarops_agents_last_html($lang, $all);
			} elseif (isset($all[$hm[1]])) {
				$body = rosmarops_agents_history_html($lang, $all[$hm[1]]);
			} else {
				return $miss;
			}
			return [200, $html + ['X-Robots-Tag' => 'noindex'], $body];
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
