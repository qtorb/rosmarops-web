<?php
// php -S router for the daily synopsis routes. Anything the mu-plugin does not answer gets "wp-404" (WordPress would answer 404).
require __DIR__ . '/daily-stub.php';
do_action('muplugins_loaded');
http_response_code(404);
echo 'wp-404';
