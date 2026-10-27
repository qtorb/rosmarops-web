<?php
/**
 * Plugin Name: RosmarOps SEO
 * Description: hreflang between the EN and ES versions of a post or page, BlogPosting structured data on posts, and the Spanish sitemap in robots.txt. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

// URL of the same content in the other language, stored on each post or page.
const ROSMAROPS_ALT_META = 'rosmarops_translation_url';

add_action('init', function () {
	foreach (['post', 'page'] as $type) {
		register_post_meta($type, ROSMAROPS_ALT_META, [
			'type'              => 'string',
			'single'            => true,
			'show_in_rest'      => true,
			'sanitize_callback' => 'esc_url_raw',
			'auth_callback'     => function () {
				return current_user_can('edit_posts');
			},
		]);
	}
});

function rosmarops_is_es() {
	return strpos(get_locale(), 'es') === 0;
}

// hreflang: only where a translation URL is set.
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
	$alt = get_post_meta($id, ROSMAROPS_ALT_META, true);
	if (!$alt) {
		return;
	}
	$self = get_permalink($id);
	$en   = rosmarops_is_es() ? $alt : $self;
	$es   = rosmarops_is_es() ? $self : $alt;
	printf("<link rel=\"alternate\" hreflang=\"en\" href=\"%s\" />\n", esc_url($en));
	printf("<link rel=\"alternate\" hreflang=\"es\" href=\"%s\" />\n", esc_url($es));
	printf("<link rel=\"alternate\" hreflang=\"x-default\" href=\"%s\" />\n", esc_url($en));
}, 5);

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
		'inLanguage'       => rosmarops_is_es() ? 'es' : 'en',
		'mainEntityOfPage' => $url,
		'author'           => [
			'@type' => 'Person',
			'name'  => get_the_author_meta('display_name', $p->post_author),
		],
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

// robots.txt (served by the main site): also announce the Spanish sitemap.
add_filter('robots_txt', function ($output) {
	if (!is_main_site() || strpos($output, '/es/sitemap.xml') !== false) {
		return $output;
	}
	return rtrim($output) . "\nSitemap: https://rosmarops.com/es/sitemap.xml\nSitemap: https://rosmarops.com/sitemap-pages.xml\n";
}, 20);
