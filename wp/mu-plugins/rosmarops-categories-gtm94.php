<?php
/**
 * Plugin Name: RosmarOps blog categories (GTM-94, one-time migration)
 * Description: Once per site (EN /, ES /es/, CA /ca/), renames the «Methodology» category, creates four categories with their signed descriptions, moves six posts out of «What your agent can do», deletes that category only when it is left empty, and sets The SEO Framework noindex on the new categories with fewer than three posts. Idempotent: a per-site option marks it done and a second run changes nothing. Never deletes a post. Anything not where the table expects is left alone and logged. The log (no personal data) goes to the option rosmarops_gtm94_log and to wp-content/rosmarops-private/gtm94-<lang>.log, which the deploy reads over SFTP. Signed by Albert on 06-11. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_GTM94_DONE = 'rosmarops_gtm94_done';
const ROSMAROPS_GTM94_LOCK = 'rosmarops_gtm94_lock';
const ROSMAROPS_GTM94_LOG  = 'rosmarops_gtm94_log';
const ROSMAROPS_TSF_TERM_META = 'autodescription-term-settings';

/** The plan for one site, by its home URL, or null for any other site. Texts signed by Albert on 06-11. */
function rosmarops_gtm94_plan($home_url) {
	$home = rtrim((string) $home_url, '/');
	$plans = [
		'https://rosmarops.com' => [
			'lang'   => 'en',
			'old'    => 'ai-agents',
			'rename' => ['from' => 'methodology', 'name' => 'Agent Posture Score', 'slug' => 'agent-posture-score',
				'description' => "How RosmarOps calculates the 0–100 score it gives each agent, what counts and what doesn't, and why what wasn't read doesn't count as clean."],
			'create' => [
				['name' => 'Approval modes', 'slug' => 'approval-modes',
					'description' => "What your agent decides without asking and what it asks you to approve: auto mode, allowlists and sandboxes, agent by agent. With each version's changes, dated and sourced."],
				['name' => 'API keys and .env files', 'slug' => 'api-keys-and-env-files',
					'description' => 'Which API keys, tokens and .env files your AI agent can read on your computer, and where agents keep their own. With Observatory data and official sources.'],
				['name' => 'CLAUDE.md, AGENTS.md and rules', 'slug' => 'claude-md-agents-md-and-rules',
					'description' => "The instruction files your agent reads every session (CLAUDE.md, AGENTS.md, rules and memory), which agents read other agents' files, and who can change them."],
				['name' => 'MCP servers', 'slug' => 'mcp-servers',
					'description' => 'What you install when you add an MCP server, a skill or a hook to your agent: what it can read, where it sends data, and which malicious packages have been recorded.'],
			],
			'moves' => [
				'claude-code-auto-mode-what-it-can-read'               => 'approval-modes',
				'which-keys-can-your-ai-coding-agent-read'             => 'api-keys-and-env-files',
				'can-one-ai-agent-change-another-agents-configuration' => 'claude-md-agents-md-and-rules',
				'before-you-tell-your-agent-to-install-it'             => 'mcp-servers',
				'tools-that-check-what-your-ai-coding-agents-can-reach' => 'agent-posture-score',
			],
			'noindex' => ['approval-modes', 'api-keys-and-env-files', 'claude-md-agents-md-and-rules', 'mcp-servers'],
		],
		'https://rosmarops.com/es' => [
			'lang'   => 'es',
			'old'    => 'que-puede-hacer-tu-agente',
			'rename' => ['from' => 'metodologia', 'name' => 'Nota de exposición', 'slug' => 'nota-de-exposicion',
				'description' => 'Cómo se calcula la nota de 0 a 100 que RosmarOps da a cada agente, qué cuenta y qué no, y por qué lo que no se leyó no cuenta como limpio.'],
			'create' => [
				['name' => 'Modos y aprobaciones', 'slug' => 'modos-y-aprobaciones',
					'description' => 'Qué decide tu agente sin preguntarte y qué te pide aprobar: modo auto, listas de permitidos y sandbox, agente por agente. Con los cambios de cada versión, fechados y con su fuente.'],
				['name' => 'Claves de API y .env', 'slug' => 'claves-de-api-y-env',
					'description' => 'Qué claves de API, tokens y ficheros .env puede leer tu agente de IA en tu ordenador, y dónde guardan los agentes las suyas. Con datos del Observatorio y su fuente oficial.'],
				['name' => 'CLAUDE.md, AGENTS.md y reglas', 'slug' => 'claude-md-agents-md-y-reglas',
					'description' => 'Los ficheros de instrucciones que tu agente lee en cada sesión (CLAUDE.md, AGENTS.md, reglas y memoria), qué agentes leen los de otros y quién puede cambiarlos.'],
				['name' => 'Servidores MCP', 'slug' => 'servidores-mcp',
					'description' => 'Qué instalas cuando añades un servidor MCP, un skill o un hook a tu agente: qué puede leer, adónde envía datos y qué paquetes maliciosos se han registrado.'],
			],
			'moves' => [
				'modo-auto-claude-code-que-puede-leer'                            => 'modos-y-aprobaciones',
				'que-claves-puede-leer-tu-agente-de-ia'                           => 'claves-de-api-y-env',
				'puede-un-agente-de-ia-cambiar-la-configuracion-de-otro'          => 'claude-md-agents-md-y-reglas',
				'antes-de-decirle-a-tu-agente-que-lo-instale'                     => 'servidores-mcp',
				'servidores-mcp-de-markdown-que-buscaban-credenciales-en-la-nube' => 'servidores-mcp',
				'herramientas-que-revisan-a-que-llegan-tus-agentes-de-ia'         => 'nota-de-exposicion',
			],
			'noindex' => ['modos-y-aprobaciones', 'claves-de-api-y-env', 'claude-md-agents-md-y-reglas', 'servidores-mcp'],
		],
		'https://rosmarops.com/ca' => [
			'lang'   => 'ca',
			'old'    => 'agents-ia',
			'rename' => ['from' => 'metodologia', 'name' => "Nota d'exposició", 'slug' => 'nota-dexposicio',
				'description' => "Com es calcula la nota de 0 a 100 que RosmarOps dona a cada agent, què compta i què no, i per què el que no s'ha llegit no compta com a net."],
			'create' => [
				['name' => 'Modes i aprovacions', 'slug' => 'modes-i-aprovacions',
					'description' => 'Què decideix el teu agent sense preguntar-te i què et demana aprovar: mode auto, llistes de permesos i sandbox, agent per agent. Amb els canvis de cada versió, datats i amb la seva font.'],
				['name' => "Claus d'API i .env", 'slug' => 'claus-dapi-i-env',
					'description' => "Quines claus d'API, tokens i fitxers .env pot llegir el teu agent d'IA al teu ordinador, i on guarden els agents les seves. Amb dades de l'Observatori i la seva font oficial."],
				['name' => 'CLAUDE.md, AGENTS.md i regles', 'slug' => 'claude-md-agents-md-i-regles',
					'description' => "Els fitxers d'instruccions que el teu agent llegeix a cada sessió (CLAUDE.md, AGENTS.md, regles i memòria), quins agents llegeixen els d'altres i qui els pot canviar."],
				['name' => 'Servidors MCP', 'slug' => 'servidors-mcp',
					'description' => "Què instal·les quan afegeixes un servidor MCP, un skill o un hook al teu agent: què pot llegir, on envia dades i quins paquets maliciosos s'han registrat."],
			],
			'moves' => [
				'mode-auto-claude-code-que-pot-llegir'                => 'modes-i-aprovacions',
				'quines-claus-pot-llegir-el-teu-agent-dia'            => 'claus-dapi-i-env',
				'pot-un-agent-dia-canviar-la-configuracio-dun-altre'  => 'claude-md-agents-md-i-regles',
				'abans-de-dir-al-teu-agent-que-ho-instal-li'          => 'servidors-mcp',
				'eines-que-revisen-a-que-arriben-els-teus-agents-dia' => 'nota-dexposicio',
			],
			'noindex' => ['modes-i-aprovacions', 'claus-dapi-i-env', 'claude-md-agents-md-i-regles', 'servidors-mcp'],
		],
	];
	return $plans[$home] ?? null;
}

/** Runs the plan once on the current site. Returns the log lines (also stored), or null when there is nothing to run. */
function rosmarops_gtm94_run() {
	$plan = rosmarops_gtm94_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_GTM94_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_GTM94_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_GTM94_LOCK) < 600) {
			return null; // another request is running it
		}
		update_option(ROSMAROPS_GTM94_LOCK, time(), false); // a run that died more than ten minutes ago: take over
	}
	$log = [];
	$say = function ($s) use (&$log) { $log[] = $s; };
	$say('GTM-94 categories, site ' . $plan['lang'] . ', ' . gmdate('Y-m-d H:i:s') . ' UTC');

	// A. Rename.
	$r = $plan['rename'];
	$from = get_term_by('slug', $r['from'], 'category');
	$to   = get_term_by('slug', $r['slug'], 'category');
	if ($to) {
		$say("A skipped: category {$r['slug']} already exists");
	} elseif (!$from) {
		$say("A skipped: category {$r['from']} not found");
	} else {
		$res = wp_update_term($from->term_id, 'category', ['name' => $r['name'], 'slug' => $r['slug'], 'description' => $r['description']]);
		$say(is_wp_error($res) ? "A failed: {$r['from']}: " . $res->get_error_message() : "A done: {$r['from']} renamed to {$r['slug']} ({$r['name']}), description set");
	}

	// B. Create.
	foreach ($plan['create'] as $c) {
		if (get_term_by('slug', $c['slug'], 'category')) {
			$say("B skipped: category {$c['slug']} already exists");
			continue;
		}
		$res = wp_insert_term($c['name'], 'category', ['slug' => $c['slug'], 'description' => $c['description']]);
		$say(is_wp_error($res) ? "B failed: {$c['slug']}: " . $res->get_error_message() : "B done: category {$c['slug']} ({$c['name']}) created");
	}

	// C. Move posts out of the old category.
	$old = get_term_by('slug', $plan['old'], 'category');
	if (!$old) {
		$say("C skipped: old category {$plan['old']} not found; no post moved");
	}
	foreach ($plan['moves'] as $post_slug => $cat_slug) {
		if (!$old) {
			break;
		}
		$posts = get_posts(['name' => $post_slug, 'post_type' => 'post', 'post_status' => 'publish', 'numberposts' => 1]);
		$cat = get_term_by('slug', $cat_slug, 'category');
		if (!$posts) {
			$say("C skipped: published post {$post_slug} not found");
			continue;
		}
		if (!$cat) {
			$say("C skipped: {$post_slug}: category {$cat_slug} not found");
			continue;
		}
		$ids = array_map('intval', wp_get_post_categories($posts[0]->ID));
		if (!in_array((int) $old->term_id, $ids, true)) {
			$say(in_array((int) $cat->term_id, $ids, true)
				? "C skipped: {$post_slug} is already in {$cat_slug}"
				: "C skipped: {$post_slug} is not in {$plan['old']}; left as it is");
			continue;
		}
		$new = array_values(array_unique(array_merge(array_diff($ids, [(int) $old->term_id]), [(int) $cat->term_id])));
		$res = wp_set_post_categories($posts[0]->ID, $new);
		$say(is_wp_error($res) || $res === false ? "C failed: {$post_slug}" : "C done: {$post_slug} moved from {$plan['old']} to {$cat_slug}");
	}

	// D. Delete the old category only when it is left with no post at all (any status).
	if ($old) {
		clean_term_cache($old->term_id, 'category');
		$left = get_posts(['category' => $old->term_id, 'post_type' => 'post', 'post_status' => 'any', 'numberposts' => 1, 'fields' => 'ids']);
		if ($left) {
			$say("D skipped: {$plan['old']} still has posts; not deleted");
		} elseif ((int) get_option('default_category') === (int) $old->term_id) {
			$say("D skipped: {$plan['old']} is the site's default category; not deleted");
		} else {
			$res = wp_delete_term($old->term_id, 'category');
			$say($res === true ? "D done: empty category {$plan['old']} deleted (no post deleted)" : "D failed: {$plan['old']} not deleted");
		}
	}

	// E. The SEO Framework noindex on the new categories with fewer than three posts.
	foreach ($plan['noindex'] as $slug) {
		$t = get_term_by('slug', $slug, 'category');
		if (!$t) {
			$say("E skipped: category {$slug} not found");
			continue;
		}
		$count = (int) count(get_posts(['category' => $t->term_id, 'post_type' => 'post', 'post_status' => 'publish', 'numberposts' => 3, 'fields' => 'ids']));
		if ($count >= 3) {
			$say("E skipped: {$slug} has {$count} posts; stays indexable");
			continue;
		}
		$meta = get_term_meta($t->term_id, ROSMAROPS_TSF_TERM_META, true);
		$meta = is_array($meta) ? $meta : [];
		if ((int) ($meta['noindex'] ?? 0) === 1) {
			$say("E skipped: {$slug} already noindex");
			continue;
		}
		$meta['noindex'] = 1;
		update_term_meta($t->term_id, ROSMAROPS_TSF_TERM_META, $meta);
		$say("E done: {$slug} noindex ({$count} posts)");
	}

	update_option(ROSMAROPS_GTM94_LOG, $log, false);
	update_option(ROSMAROPS_GTM94_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_GTM94_LOCK);
	rosmarops_gtm94_write_log($plan['lang'], $log);
	return $log;
}

/** Writes the log to wp-content/rosmarops-private/, a folder closed to the web, for the deploy to read over SFTP. */
function rosmarops_gtm94_write_log($lang, $log) {
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-gtm94: cannot create ' . $dir);
		return;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	if (!file_exists($dir . '/index.php')) {
		@file_put_contents($dir . '/index.php', "<?php\n");
	}
	@file_put_contents($dir . '/gtm94-' . $lang . '.log', implode("\n", $log) . "\n");
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_gtm94_run();
});
