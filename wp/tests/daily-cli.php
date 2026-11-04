<?php
// CLI helper for test_daily.py: `php daily-cli.php store <file> <date>` prints "stored" or "not stored".
require __DIR__ . '/daily-stub.php';
[$_, $cmd, $file, $date] = $argv + [null, null, null, null];
if ($cmd === 'store') {
	$d = json_decode(file_get_contents($file), true);
	echo rosmarops_daily_store($d, $date) ? "stored\n" : "not stored\n";
}
// `php daily-cli.php today <file> <lang>` prints the «Today in the Observatory» block for that day (GTM-88).
if ($cmd === 'today') {
	echo rosmarops_daily_today($date, json_decode(file_get_contents($file), true));
}
// GTM-89. `store-agent <file> <id>` prints "stored" or "not stored"; `history <file> <lang>` prints the history of a
// validated agent file (or "invalid"); `route <path>` prints the status line and the body the router answers.
if ($cmd === 'store-agent') {
	echo rosmarops_agents_store(json_decode(file_get_contents($file), true), $date) ? "stored\n" : "not stored\n";
}
if ($cmd === 'history') {
	$a = json_decode(file_get_contents($file), true);
	$v = rosmarops_agents_validate($a, $a['agent']['id'] ?? '');
	echo $v === null ? 'invalid' : rosmarops_agents_history_html($date, $v);
}
if ($cmd === 'route') {
	$r = rosmarops_daily_route($file);
	echo $r === null ? "null\n" : $r[0] . "\n" . $r[2];
}
