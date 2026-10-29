<?php
// CLI helper for test_daily.py: `php daily-cli.php store <file> <date>` prints "stored" or "not stored".
require __DIR__ . '/daily-stub.php';
[$_, $cmd, $file, $date] = $argv + [null, null, null, null];
if ($cmd === 'store') {
	$d = json_decode(file_get_contents($file), true);
	echo rosmarops_daily_store($d, $date) ? "stored\n" : "not stored\n";
}
