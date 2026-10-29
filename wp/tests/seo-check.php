<?php
// Checks for wp/mu-plugins/rosmarops-seo.php (GTM-21): robots.txt Disallow and sitemaps, IndexNow on publish, linked author.
// Test-only stand-in for WordPress; exits 1 on the first failure. Run: php wp/tests/seo-check.php
define('ABSPATH', __DIR__ . '/');
$GLOBALS['__hooks'] = [];
$GLOBALS['__posts'] = [];
function add_action($h, $cb, $p = 10, $n = 1) { $GLOBALS['__hooks'][$h][] = $cb; }
function add_filter($h, $cb, $p = 10, $n = 1) { $GLOBALS['__hooks'][$h][] = $cb; }
function is_main_site() { return true; }
function wp_is_post_revision($p) { return $p->post_type === 'revision'; }
function wp_is_post_autosave($p) { return false; }
function get_permalink($p) { return 'https://rosmarops.com/blog/' . $p->post_name . '/'; }
function wp_json_encode($d) { return json_encode($d, JSON_UNESCAPED_SLASHES); }
function wp_remote_post($url, $args) { $GLOBALS['__posts'][] = [$url, $args]; return []; }
require __DIR__ . '/../mu-plugins/rosmarops-seo.php';

function check($cond, $msg) { if (!$cond) { fwrite(STDERR, "FAIL $msg\n"); exit(1); } echo "ok   $msg\n"; }

$wp = "User-agent: *\nDisallow: /wp-admin/\nAllow: /wp-admin/admin-ajax.php\n\nSitemap: https://rosmarops.com/sitemap.xml\n";
$r = rosmarops_robots_txt($wp);
check(strpos($r, "User-agent: *\nDisallow: /download\nDisallow: /es/descargar\nDisallow: /ca/descarregar\nDisallow: /wp-admin/") !== false, 'robots: download routes disallowed under User-agent: *');
check(substr_count($r, 'Sitemap: https://rosmarops.com/es/sitemap.xml') === 1 && strpos($r, 'Sitemap: https://rosmarops.com/sitemap-pages.xml') !== false, 'robots: sitemaps announced once');
check(rosmarops_robots_txt($r) === $r, 'robots: idempotent');

$post = (object) ['post_type' => 'post', 'post_name' => 'example'];
rosmarops_indexnow('publish', 'draft', $post);
check(count($GLOBALS['__posts']) === 1 && $GLOBALS['__posts'][0][0] === 'https://api.indexnow.org/indexnow', 'indexnow: publish pings once');
$body = json_decode($GLOBALS['__posts'][0][1]['body'], true);
check($body === ['host' => 'rosmarops.com', 'key' => '24a8c2078ff9b0ee590acf6cd5901e32', 'keyLocation' => 'https://rosmarops.com/24a8c2078ff9b0ee590acf6cd5901e32.txt', 'urlList' => ['https://rosmarops.com/blog/example/']], 'indexnow: body is the key and the published URL only');
check($GLOBALS['__posts'][0][1]['blocking'] === false, 'indexnow: non-blocking');
rosmarops_indexnow('draft', 'draft', $post);
rosmarops_indexnow('publish', 'publish', (object) ['post_type' => 'revision', 'post_name' => 'x']);
rosmarops_indexnow('publish', 'draft', (object) ['post_type' => 'attachment', 'post_name' => 'x']);
check(count($GLOBALS['__posts']) === 1, 'indexnow: drafts, revisions and attachments are not pinged');

$a = rosmarops_author('Albert Garcia Pujadas');
check($a['@id'] === 'https://rosmarops.com/#founder' && count($a['sameAs']) === 3, 'author: founder linked');
check(rosmarops_author('Someone') === ['@type' => 'Person', 'name' => 'Someone'], 'author: others unchanged');
