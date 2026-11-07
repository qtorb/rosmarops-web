<?php
// php -S router: real HTTP for the download routes and the REST read endpoint (stubbed REST server).
require __DIR__ . '/wp-stub.php';
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
do_action('muplugins_loaded'); // redirects and exits on a download route
if (preg_match('#^(/es|/ca)?/wp-json(/.*)$#', $path, $rm)) { // each language site has its own REST base
	do_action('rest_api_init');
	$route = $rm[2];
	$def = $GLOBALS['__routes'][$route][$_SERVER['REQUEST_METHOD']] ?? null;
	if (!$def) { http_response_code(404); header('Content-Type: application/json'); echo '{"code":"rest_no_route"}'; return true; }
	$res = $def['callback']();
	http_response_code($res->status ?? 200);
	foreach ($res->headers as $k => $v) header("$k: $v");
	if (($res->status ?? 200) === 204) return true;
	header('Content-Type: application/json; charset=UTF-8');
	echo json_encode($res->data, JSON_UNESCAPED_SLASHES);
	return true;
}
http_response_code(404); echo 'not found';
