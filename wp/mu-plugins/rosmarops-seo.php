<?php
/**
 * Plugin Name: RosmarOps SEO
 * Description: hreflang between the EN, ES and CA versions of a post or page, BlogPosting structured data on posts, the Spanish and Catalan sitemaps and the download routes (Disallow) in robots.txt; IndexNow ping on publish. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

// URL of the same content in the other language (EN <-> ES), stored on each post or page.
const ROSMAROPS_ALT_META = 'rosmarops_translation_url';
// URL of the same content in a given language: rosmarops_url_en, rosmarops_url_es, rosmarops_url_ca.
const ROSMAROPS_LANGS = ['en', 'es', 'ca'];

add_action('init', function () {
	$keys = [ROSMAROPS_ALT_META];
	foreach (ROSMAROPS_LANGS as $l) {
		$keys[] = 'rosmarops_url_' . $l;
	}
	foreach (['post', 'page'] as $type) {
		foreach ($keys as $key) {
			register_post_meta($type, $key, [
				'type'              => 'string',
				'single'            => true,
				'show_in_rest'      => true,
				'sanitize_callback' => 'esc_url_raw',
				'auth_callback'     => function () {
					return current_user_can('edit_posts');
				},
			]);
		}
	}
});

function rosmarops_lang() {
	$l = substr(get_locale(), 0, 2);
	return in_array($l, ROSMAROPS_LANGS, true) ? $l : 'en';
}

// hreflang: only where at least one translation URL is set.
add_action('wp_head', function () {
	if (is_home()) {
		$id = (int) get_option('page_for_posts');
	} elseif (is_singular()) {
		$id = get_queried_object_id();
	} else {
		return;
	}
	if (!$id) {
		return;
	}
	$self = rosmarops_lang();
	$urls = [];
	$alt  = get_post_meta($id, ROSMAROPS_ALT_META, true);
	if ($alt && $self !== 'ca') {
		$urls[$self === 'es' ? 'en' : 'es'] = $alt;
	}
	foreach (ROSMAROPS_LANGS as $l) {
		$u = get_post_meta($id, 'rosmarops_url_' . $l, true);
		if ($u && $l !== $self) {
			$urls[$l] = $u;
		}
	}
	if (!$urls) {
		return;
	}
	$urls[$self] = get_permalink($id);
	foreach (ROSMAROPS_LANGS as $l) {
		if (isset($urls[$l])) {
			printf("<link rel=\"alternate\" hreflang=\"%s\" href=\"%s\" />\n", $l, esc_url($urls[$l]));
		}
	}
	if (isset($urls['en'])) {
		printf("<link rel=\"alternate\" hreflang=\"x-default\" href=\"%s\" />\n", esc_url($urls['en']));
	}
}, 5);

// The founder, the same Person as on the homes and the About pages (#founder).
function rosmarops_author($name) {
	if ($name !== 'Albert Garcia Pujadas') {
		return ['@type' => 'Person', 'name' => $name];
	}
	return [
		'@type'  => 'Person',
		'@id'    => 'https://rosmarops.com/#founder',
		'name'   => 'Albert Garcia Pujadas',
		'url'    => 'https://www.qtorb.com/',
		'sameAs' => ['https://www.qtorb.com/', 'https://www.linkedin.com/in/albertgpujadas/', 'https://x.com/qtorb'],
	];
}

// BlogPosting structured data on single posts.
add_action('wp_head', function () {
	if (!is_singular('post')) {
		return;
	}
	$p    = get_queried_object();
	$url  = get_permalink($p);
	$data = [
		'@context'         => 'https://schema.org',
		'@type'            => 'BlogPosting',
		'@id'              => $url . '#article',
		'headline'         => wp_strip_all_tags(get_the_title($p)),
		'description'      => wp_strip_all_tags(get_the_excerpt($p)),
		'datePublished'    => get_the_date('c', $p),
		'dateModified'     => get_the_modified_date('c', $p),
		'inLanguage'       => rosmarops_lang(),
		'mainEntityOfPage' => $url,
		'author'           => rosmarops_author(get_the_author_meta('display_name', $p->post_author)),
		'publisher'        => [
			'@type' => 'Organization',
			'@id'   => 'https://rosmarops.com/#org',
			'name'  => 'RosmarOps',
			'url'   => 'https://rosmarops.com/',
			'logo'  => 'https://rosmarops.com/assets/brand/rosmarops-logo@2x.png',
		],
	];
	$img = get_the_post_thumbnail_url($p, 'full');
	if ($img) {
		$data['image'] = $img;
	}
	echo '<script type="application/ld+json">' . wp_json_encode($data, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . "</script>\n";
}, 20);

// AboutPage + Person structured data on the About pages (EN about, ES/CA que-es-rosmarops).
add_action('wp_head', function () {
	if (!is_page(['about', 'que-es-rosmarops'])) {
		return;
	}
	$p    = get_queried_object();
	$url  = get_permalink($p);
	$data = [
		'@context' => 'https://schema.org',
		'@graph'   => [
			[
				'@type'        => 'AboutPage',
				'@id'          => $url . '#page',
				'url'          => $url,
				'name'         => wp_strip_all_tags(get_the_title($p)),
				'inLanguage'   => rosmarops_lang(),
				'dateModified' => get_the_modified_date('c', $p),
				'about'        => ['@id' => 'https://rosmarops.com/#org'],
				'mainEntity'   => ['@id' => 'https://rosmarops.com/#org'],
			],
			[
				'@type'   => 'Organization',
				'@id'     => 'https://rosmarops.com/#org',
				'name'    => 'RosmarOps',
				'url'     => 'https://rosmarops.com/',
				'logo'    => 'https://rosmarops.com/assets/brand/rosmarops-logo@2x.png',
				'founder' => ['@id' => 'https://rosmarops.com/#founder'],
				'sameAs'  => ['https://github.com/qtorb/rosmarops', 'https://x.com/RosmarOps'],
			],
			[
				'@type'  => 'Person',
				'@id'    => 'https://rosmarops.com/#founder',
				'name'   => 'Albert Garcia Pujadas',
				'url'    => 'https://www.qtorb.com/',
				'sameAs' => ['https://www.qtorb.com/', 'https://www.linkedin.com/in/albertgpujadas/', 'https://x.com/qtorb'],
			],
		],
	];
	echo '<script type="application/ld+json">' . wp_json_encode($data, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . "</script>\n";
}, 20);

// The SEO Framework fields, writable over the REST API by editors, so titles and
// descriptions can be set without the editor screen.
add_action('init', function () {
	foreach (['post', 'page'] as $type) {
		foreach (['_genesis_title', '_genesis_description', '_tsf_title_no_blogname'] as $key) {
			register_post_meta($type, $key, [
				'type'          => 'string',
				'single'        => true,
				'show_in_rest'  => true,
				'auth_callback' => function () {
					return current_user_can('edit_posts');
				},
			]);
		}
	}
}, 20);

// The posts page (/blog/, /ca/blog/) prints no heading in GeneratePress: give it its H1.
add_action('generate_before_main_content', function () {
	if (!is_home() || is_front_page()) {
		return;
	}
	$id = (int) get_option('page_for_posts');
	if (!$id) {
		return;
	}
	printf('<header class="page-header"><h1 class="page-title">%s</h1></header>', esc_html(get_the_title($id)));
});

// robots.txt (served by the main site): the download routes are not for crawlers (they would be counted as
// downloads, GTM-18), nor are the raw sample reports (their pages are; decision 2026-10-29), and the Spanish, Catalan and static-page sitemaps are announced.
function rosmarops_robots_txt($output) {
	if (!is_main_site() || strpos($output, '/es/sitemap.xml') !== false) {
		return $output;
	}
	$disallow = "Disallow: /download\nDisallow: /es/descargar\nDisallow: /ca/descarregar\nDisallow: /sample-report/sample-report\n";
	if (preg_match('/^User-agent: \*\R/m', $output)) {
		$output = preg_replace('/^(User-agent: \*\R)/m', '$1' . $disallow, $output, 1);
	} else {
		$output = "User-agent: *\n" . $disallow . "\n" . $output;
	}
	return rtrim($output) . "\nSitemap: https://rosmarops.com/es/sitemap.xml\nSitemap: https://rosmarops.com/ca/sitemap.xml\nSitemap: https://rosmarops.com/sitemap-pages.xml\n";
}
add_filter('robots_txt', 'rosmarops_robots_txt', 20);

// IndexNow (GTM-21): tell Bing and the other IndexNow engines when a post or page is published or updated.
// Only the published address is sent. Same public key as the static deploy.
const ROSMAROPS_INDEXNOW_KEY = '24a8c2078ff9b0ee590acf6cd5901e32';
function rosmarops_indexnow($new_status, $old_status, $post) {
	if ($new_status !== 'publish' || !in_array($post->post_type, ['post', 'page'], true)) {
		return;
	}
	if (wp_is_post_revision($post) || wp_is_post_autosave($post)) {
		return;
	}
	wp_remote_post('https://api.indexnow.org/indexnow', [
		'blocking' => false,
		'timeout'  => 5,
		'headers'  => ['Content-Type' => 'application/json; charset=utf-8'],
		'body'     => wp_json_encode([
			'host'        => 'rosmarops.com',
			'key'         => ROSMAROPS_INDEXNOW_KEY,
			'keyLocation' => 'https://rosmarops.com/' . ROSMAROPS_INDEXNOW_KEY . '.txt',
			'urlList'     => [get_permalink($post)],
		]),
	]);
}
add_action('transition_post_status', 'rosmarops_indexnow', 10, 3);
