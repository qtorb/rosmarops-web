<?php
// Test-only: just enough WordPress to load a mu-plugin and call its pure functions (no database, no hooks run).
define('ABSPATH', __DIR__ . '/');
function add_action($hook, $cb, $prio = 10) {}
function register_rest_route($ns, $route, $args) {}
