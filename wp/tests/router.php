<?php
// php -S router: real HTTP for the download routes and the REST read endpoint (stubbed REST server).
require __DIR__ . '/wp-stub.php';
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
do_action('muplugins_loaded'); // redirects and exits on a download route
if (strpos($path, '/wp-json/') === 0) {
	do_action('rest_api_init');
	$route = substr($path, strlen('/wp-json'));
	$def = $GLOBALS['__routes'][$route] ?? null;
	if (!$def || $def['methods'] !== $_SERVER['REQUEST_METHOD']) { http_response_code(404); header('Content-Type: application/json'); echo '{"code":"rest_no_route"}'; return true; }
	$res = $def['callback']();
	foreach ($res->headers as $k => $v) header("$k: $v");
	header('Content-Type: application/json; charset=UTF-8');
	echo json_encode($res->data, JSON_UNESCAPED_SLASHES);
	return true;
}
http_response_code(404); echo 'not found';
