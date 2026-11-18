<?php
/**
 * Plugin Name: RosmarOps 0.15.0 promise in WordPress (GTM-181, one-time, per site)
 * Description: Once per site (EN /, ES /es/, CA /ca/), puts the 0.15.0 promise («Nothing it reads on your computer leaves without your permission, and your keys never do») where WordPress serves it. Texts signed by Albert on 18-11 at 17:52 (qtorb/rosmarops-vigil docs/research/2026-11-18-promesa-0-15-0-web-propuesta.md §1, §3 and §4); published with his order «publica GTM-181» (18-11), by merging the pull request that carries this file. (1) The program's privacy policy: on EN (page 1175, /privacy/app/) and ES (page 1162, /es/privacidad/app/) the title and the whole content are replaced, and the page gets the address of the new CA version for hreflang; on CA a published parent page «privadesa» is created with no content (the static /ca/privadesa/ is what visitors see, as with EN 1168 and ES 1153) and, under it, the CA policy at /ca/privadesa/app/. (2) A dated line in italics goes at the start of 14 published posts (5 EN, 5 ES, 4 CA); nothing else in them changes. (3) Four published pages that the repository's static pages already serve at the same address go to draft: EN 993 (/) and 1153 (/blog/about/), ES 34 and CA 25 (/blog/que-es-rosmarops/). The parents of the policies, EN 1168 (/privacy/) and ES 1153 (/es/privacidad/), stay published on purpose (Albert, 18-11), so the policies keep their addresses. Every post and page is checked by ID, type, slug and status before it is written, and is left alone and logged if anything differs; a policy is only replaced if it still has the old text, a post only gets the line once. Writes go by ID with $wpdb (no wp_update_post), so post dates stay as they are, except the policies' modified date, which moves to now. Idempotent: a per-site option marks it done, with a lock. The log (ids, slugs and statuses only) goes to the option rosmarops_gtm181_log and to wp-content/rosmarops-private/gtm181-<lang>.log, which the deploy reads over SFTP. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_GTM181_DONE   = 'rosmarops_gtm181_done';
const ROSMAROPS_GTM181_LOCK   = 'rosmarops_gtm181_lock';
const ROSMAROPS_GTM181_LOG    = 'rosmarops_gtm181_log';
const ROSMAROPS_GTM181_AUTHOR = 'Albert Garcia Pujadas';
const ROSMAROPS_GTM181_POLICY = [
	'en' => 'https://rosmarops.com/privacy/app/',
	'es' => 'https://rosmarops.com/es/privacidad/app/',
	'ca' => 'https://rosmarops.com/ca/privadesa/app/',
];
// Text that only the old policy has: a policy without it is not replaced.
const ROSMAROPS_GTM181_OLD = ['en' => 'never connects to the network', 'es' => 'nunca se conecta a la red'];
// Marks the dated line, so that a post never gets it twice.
const ROSMAROPS_GTM181_MARK = 'rosmarops-gtm181';

/** The plan for one site, by its home URL, or null for any other site. */
function rosmarops_gtm181_plan($home_url) {
	$plans = [
		'https://rosmarops.com'    => ['lang' => 'en', 'policy' => 1175,
			'posts'  => [990 => 'my-machine-scored-18-of-100', 1176 => 'rosmarops-is-out', 1184 => 'rosmarops-0-3-0',
				1189 => 'rosmarops-0-4-0', 1202 => 'which-keys-can-your-ai-coding-agent-read'],
			'drafts' => [993 => 'home', 1153 => 'about']],
		'https://rosmarops.com/es' => ['lang' => 'es', 'policy' => 1162,
			'posts'  => [1144 => 'mi-maquina-saco-un-18-de-100', 1163 => 'rosmarops-ya-se-puede-descargar',
				1172 => 'rosmarops-0-3-0', 1177 => 'rosmarops-0-4-0', 1191 => 'que-claves-puede-leer-tu-agente-de-ia'],
			'drafts' => [34 => 'que-es-rosmarops']],
		'https://rosmarops.com/ca' => ['lang' => 'ca', 'policy' => null,
			'posts'  => [20 => 'la-meva-maquina-va-treure-un-18-de-100', 24 => 'rosmarops-ja-es-pot-descarregar',
				37 => 'rosmarops-0-4-0', 47 => 'quines-claus-pot-llegir-el-teu-agent-dia'],
			'drafts' => [25 => 'que-es-rosmarops']],
	];
	return $plans[rtrim((string) $home_url, '/')] ?? null;
}

/** The dated line for the start of a post, as a paragraph block. */
function rosmarops_gtm181_line($lang) {
	$lines = [
		'en' => 'Update, 18-11-2026: from version 0.15.0, RosmarOps can send usage statistics if you give permission. Nothing it reads on your computer leaves without your permission, and your keys never do. What exactly it sends: <a href="%s">the program\'s privacy policy</a>.',
		'es' => 'Actualización del 18-11-2026: desde la versión 0.15.0, RosmarOps puede enviar estadísticas de uso si das permiso. Lo que lee de tu ordenador no sale sin tu permiso, y tus claves nunca. Qué envía exactamente: <a href="%s">política de privacidad del programa</a>.',
		'ca' => 'Actualització del 18-11-2026: des de la versió 0.15.0, RosmarOps pot enviar estadístiques d\'ús si dones permís. El que llegeix del teu ordinador no surt sense el teu permís, i les teves claus mai. Què envia exactament: <a href="%s">política de privadesa del programa</a>.',
	];
	return '<!-- wp:paragraph {"className":"' . ROSMAROPS_GTM181_MARK . '"} -->' . "\n"
		. '<p class="' . ROSMAROPS_GTM181_MARK . '"><em>' . sprintf($lines[$lang], ROSMAROPS_GTM181_POLICY[$lang]) . '</em></p>' . "\n"
		. "<!-- /wp:paragraph -->\n\n";
}

/** The program's privacy policy for a language: [title, block markup]. */
function rosmarops_gtm181_policy($lang) {
	$t = [
		'en' => [
			'title' => 'RosmarOps program privacy policy',
			'intro' => ['Last updated: 18 November 2026.', 'Applies from version 0.15.0, on Windows, macOS and Linux.'],
			'short' => ['In short', 'RosmarOps reads the settings of your AI agents on your computer and writes a report right there. Nothing it reads on your computer leaves without your permission, and your keys never do. It never changes your files, settings, repositories, keys or agents.'],
			'sends' => ['What it sends, and only with your permission', 'Always over HTTPS and only to app.rosmarops.com. Every send is logged in rosmarops-sends.log, on your computer.', [
				'Your results, to your space: only if you connect this computer to your space. They are encrypted with your key. You can disconnect it at any time.',
				'The problem list: if something fails, it asks you, and it is only sent if you press «Send» or chose to send it without being asked. It carries error codes, version, system and day; a comment and your email only if you write them.',
				'Usage statistics: it asks you once. If you say yes, after each review it sends a summary: version, system, how you installed it, which agents it finds, the score, the class, the finding codes, whether your space and the Claude Code plugin are connected, the day and a random install id. The last one sent is in data/rosmarops-usage-last.json. Turn it off with rosmarops usage off. We keep it 400 days, not linked to any account.',
			]],
			'never' => ['What it never sends', 'Your keys, the content of your files or settings, paths, or the names of files, projects or computers.'],
			'out'   => ['What you take out yourself', [
				'the «Copy for your AI» text, if you paste it into an AI in the cloud. It contains no secret values or shortened previews, and replaces your user folder with ~. It can include the domain of a remote MCP server, never its full address. It may include the id RosmarOps gives a key (cred_ and 16 characters), which cannot be turned back into the key;',
				'the share card, if you publish it. It contains only the score, the band, the counts, the date and the method version.',
			]],
			'company' => ['If your company manages it', 'If your company installs RosmarOps with its own configuration, it can read a summary of each review on your computer with its management tool (Fleet). RosmarOps doesn\'t send it: the company reads it on your computer. The report says so in «Your company», and the company can\'t hide findings from you.'],
			'space' => ['Your space', 'What your space keeps is in the app.rosmarops.com privacy policy: <a href="https://app.rosmarops.com/privacy">https://app.rosmarops.com/privacy</a>'],
		],
		'es' => [
			'title' => 'Política de privacidad del programa RosmarOps',
			'intro' => ['Última actualización: 18 de noviembre de 2026.', 'Vale desde la versión 0.15.0, en Windows, macOS y Linux.'],
			'short' => ['En resumen', 'RosmarOps lee la configuración de tus agentes de IA en tu ordenador y escribe un informe ahí mismo. Lo que lee de tu ordenador no sale sin tu permiso, y tus claves nunca. Nunca cambia tus ficheros, ajustes, repositorios, claves ni agentes.'],
			'sends' => ['Qué envía, y solo con tu permiso', 'Siempre por HTTPS y solo a app.rosmarops.com. Cada envío queda anotado en rosmarops-sends.log, en tu ordenador.', [
				'Tus resultados, a tu espacio: solo si conectas este ordenador a tu espacio. Van cifrados con tu llave. Puedes desconectarlo cuando quieras.',
				'La lista de problemas: si algo falla, te pregunta, y solo se envía si pulsas «Enviar» o elegiste enviarla sin que te pregunte. Lleva códigos de error, versión, sistema y día; un comentario y tu correo, solo si los escribes tú.',
				'Estadísticas de uso: te lo pregunta una vez. Si dices que sí, después de cada revisión envía un resumen: versión, sistema, cómo lo instalaste, qué agentes encuentra, la nota, la clase, los códigos de aviso, si tu espacio y el plugin de Claude Code están conectados, el día y un identificador aleatorio de instalación. Lo último enviado está en data/rosmarops-usage-last.json. Se apaga con rosmarops usage off. Lo guardamos 400 días, sin relación con ninguna cuenta.',
			]],
			'never' => ['Qué no envía nunca', 'Tus claves, el contenido de tus ficheros o de tus ajustes, rutas, ni nombres de ficheros, proyectos u ordenadores.'],
			'out'   => ['Lo que sacas tú', [
				'el texto de «Copiar para tu IA», si lo pegas en una IA en la nube. No contiene valores de secretos ni vistas recortadas, y sustituye tu carpeta de usuario por ~. Puede incluir el dominio de un servidor MCP remoto, nunca su dirección completa. Puede incluir el identificador que RosmarOps da a una clave (cred_ y 16 caracteres), con el que no se puede reconstruir la clave;',
				'la tarjeta para compartir, si la publicas. Solo contiene la nota, la banda, los recuentos, la fecha y la versión del método.',
			]],
			'company' => ['Si tu empresa lo gestiona', 'Si tu empresa instala RosmarOps con su propia configuración, puede leer en tu ordenador un resumen de cada revisión con su herramienta de gestión (Fleet). RosmarOps no se lo envía: lo lee la empresa en tu equipo. El informe lo dice en «Tu empresa», y la empresa no puede ocultarte avisos.'],
			'space' => ['Tu espacio', 'Lo que guarda tu espacio está en la privacidad de app.rosmarops.com: <a href="https://app.rosmarops.com/privacy">https://app.rosmarops.com/privacy</a>'],
		],
		'ca' => [
			'title' => 'Política de privadesa del programa RosmarOps',
			'intro' => ['Darrera actualització: 18 de novembre de 2026.', 'Val des de la versió 0.15.0, a Windows, macOS i Linux.'],
			'short' => ['En resum', 'RosmarOps llegeix la configuració dels teus agents d\'IA al teu ordinador i hi escriu un informe. El que llegeix del teu ordinador no surt sense el teu permís, i les teves claus mai. Mai no canvia els teus fitxers, ajustos, repositoris, claus ni agents.'],
			'sends' => ['Què envia, i només amb el teu permís', 'Sempre per HTTPS i només a app.rosmarops.com. Cada enviament queda anotat a rosmarops-sends.log, al teu ordinador.', [
				'Els teus resultats, al teu espai: només si connectes aquest ordinador al teu espai. Van xifrats amb la teva clau. El pots desconnectar quan vulguis.',
				'La llista de problemes: si alguna cosa falla, t\'ho pregunta, i només s\'envia si prems «Enviar» o vas triar enviar-la sense que t\'ho pregunti. Porta codis d\'error, versió, sistema i dia; un comentari i el teu correu, només si els escrius tu.',
				'Estadístiques d\'ús: t\'ho pregunta un cop. Si dius que sí, després de cada revisió envia un resum: versió, sistema, com el vas instal·lar, quins agents troba, la nota, la classe, els codis d\'avís, si el teu espai i el plugin de Claude Code estan connectats, el dia i un identificador aleatori d\'instal·lació. L\'últim enviat és a data/rosmarops-usage-last.json. S\'apaga amb rosmarops usage off. El guardem 400 dies, sense relació amb cap compte.',
			]],
			'never' => ['Què no envia mai', 'Les teves claus, el contingut dels teus fitxers o ajustos, camins, ni noms de fitxers, projectes o ordinadors.'],
			// Translated by GTM from the current ES text, for the advisor to review.
			'out'   => ['El que treus tu', [
				'el text de «Copiar per a la teva IA», si l\'enganxes en una IA al núvol. No conté valors de secrets ni vistes retallades, i substitueix la teva carpeta d\'usuari per ~. Pot incloure el domini d\'un servidor MCP remot, mai la seva adreça completa. Pot incloure l\'identificador que RosmarOps dona a una clau (cred_ i 16 caràcters), amb el qual no es pot reconstruir la clau;',
				'la targeta per compartir, si la publiques. Només conté la nota, la banda, els recomptes, la data i la versió del mètode.',
			]],
			'company' => ['Si la teva empresa el gestiona', 'Si la teva empresa instal·la RosmarOps amb la seva pròpia configuració, pot llegir al teu ordinador un resum de cada revisió amb la seva eina de gestió (Fleet). RosmarOps no l\'hi envia: la llegeix l\'empresa al teu equip. L\'informe ho diu a «La teva empresa», i l\'empresa no et pot amagar avisos.'],
			'space' => ['El teu espai', 'El que guarda el teu espai és a la privadesa d\'app.rosmarops.com: <a href="https://app.rosmarops.com/privacy">https://app.rosmarops.com/privacy</a>'],
		],
	][$lang];
	$p  = function ($s) { return "<!-- wp:paragraph -->\n<p>{$s}</p>\n<!-- /wp:paragraph -->\n\n"; };
	$h  = function ($s) { return "<!-- wp:heading -->\n<h2 class=\"wp-block-heading\">{$s}</h2>\n<!-- /wp:heading -->\n\n"; };
	$li = function ($items, $ordered) {
		$tag  = $ordered ? 'ol' : 'ul';
		$attr = $ordered ? ' {"ordered":true}' : '';
		$out  = "<!-- wp:list{$attr} -->\n<{$tag} class=\"wp-block-list\">";
		foreach ($items as $i) {
			$out .= "<!-- wp:list-item -->\n<li>{$i}</li>\n<!-- /wp:list-item -->";
		}
		return $out . "</{$tag}>\n<!-- /wp:list -->\n\n";
	};
	$html = $p($t['intro'][0]) . $p($t['intro'][1])
		. $h($t['short'][0]) . $p($t['short'][1])
		. $h($t['sends'][0]) . $p($t['sends'][1]) . $li($t['sends'][2], true)
		. $h($t['never'][0]) . $p($t['never'][1])
		. $h($t['out'][0]) . $li($t['out'][1], false)
		. $h($t['company'][0]) . $p($t['company'][1])
		. $h($t['space'][0]) . $p($t['space'][1]);
	return [$t['title'], rtrim($html) . "\n"];
}

/** The post with this ID, if it has this type, slug and status; otherwise a reason to leave it alone. */
function rosmarops_gtm181_check($id, $type, $slug, $status) {
	$p = get_post($id);
	if (!$p) {
		return [null, "{$type} {$id} not found"];
	}
	if ($p->post_type !== $type || $p->post_name !== $slug || $p->post_status !== $status) {
		return [null, "{$type} {$id} is {$p->post_type} {$p->post_name} ({$p->post_status}), expected {$type} {$slug} ({$status})"];
	}
	return [$p, null];
}

/** Author for the CA pages: Albert, or the first administrator. */
function rosmarops_gtm181_author() {
	$users = get_users(['blog_id' => get_current_blog_id(), 'role__in' => ['administrator', 'editor'], 'orderby' => 'ID', 'order' => 'ASC']);
	foreach ($users as $u) {
		if ($u->display_name === ROSMAROPS_GTM181_AUTHOR) {
			return (int) $u->ID;
		}
	}
	foreach ($users as $u) {
		if (in_array('administrator', (array) $u->roles, true)) {
			return (int) $u->ID;
		}
	}
	return 0;
}

/** EN and ES: replaces the policy's title and content, and gives it the CA address for hreflang. */
function rosmarops_gtm181_replace_policy($lang, $id, &$log) {
	global $wpdb;
	[$p, $why] = rosmarops_gtm181_check($id, 'page', 'app', 'publish');
	if ($p === null) {
		$log[] = "skipped: policy, {$why}";
		return;
	}
	if (strpos($p->post_content, ROSMAROPS_GTM181_OLD[$lang]) === false) {
		$log[] = "skipped: policy page {$id} no longer has the old text; left as it is";
		return;
	}
	[$title, $html] = rosmarops_gtm181_policy($lang);
	$now = current_time('mysql');
	$row = ['post_title' => $title, 'post_content' => $html, 'post_modified' => $now, 'post_modified_gmt' => get_gmt_from_date($now)];
	if ($wpdb->update($wpdb->posts, $row, ['ID' => $id]) !== 1) {
		$log[] = "failed: policy page {$id} could not be written";
		return;
	}
	update_post_meta($id, 'rosmarops_url_ca', ROSMAROPS_GTM181_POLICY['ca']);
	clean_post_cache($id);
	$log[] = "done: policy page {$id} replaced (0.15.0), hreflang ca added";
}

/** CA: the parent «privadesa» (published, no content) and the policy under it at /ca/privadesa/app/. */
function rosmarops_gtm181_create_ca_policy(&$log) {
	$any = ['publish', 'draft', 'pending', 'future', 'private', 'trash'];
	$parents = get_posts(['name' => 'privadesa', 'post_type' => 'page', 'post_status' => $any, 'numberposts' => 2]);
	if (count($parents) > 1 || ($parents && $parents[0]->post_status !== 'publish')) {
		$log[] = 'skipped: CA policy, the slug privadesa is already used (' . count($parents) . ' page(s), ' . ($parents[0]->post_status ?? '') . ')';
		return;
	}
	$author = rosmarops_gtm181_author();
	if ($parents) {
		$parent = (int) $parents[0]->ID;
		$log[] = "parent: page {$parent} privadesa already published; used as it is";
	} else {
		$parent = wp_insert_post(['post_type' => 'page', 'post_status' => 'publish', 'post_author' => $author,
			'post_title' => 'Privadesa i galetes', 'post_name' => 'privadesa', 'post_content' => ''], true);
		if (is_wp_error($parent) || !$parent) {
			$log[] = 'failed: CA parent page privadesa not created';
			return;
		}
		$log[] = "done: CA parent page {$parent} privadesa created, published, no content (the static /ca/privadesa/ serves the address)";
	}
	$children = get_posts(['name' => 'app', 'post_type' => 'page', 'post_parent' => $parent, 'post_status' => $any, 'numberposts' => 1]);
	if ($children) {
		$log[] = "skipped: CA policy, page {$children[0]->ID} app already exists under {$parent} ({$children[0]->post_status})";
		return;
	}
	[$title, $html] = rosmarops_gtm181_policy('ca');
	$id = wp_insert_post(['post_type' => 'page', 'post_status' => 'publish', 'post_author' => $author, 'post_parent' => $parent,
		'post_title' => $title, 'post_name' => 'app', 'post_content' => $html], true);
	if (is_wp_error($id) || !$id) {
		$log[] = 'failed: CA policy page not created';
		return;
	}
	update_post_meta($id, 'rosmarops_url_en', ROSMAROPS_GTM181_POLICY['en']);
	update_post_meta($id, 'rosmarops_url_es', ROSMAROPS_GTM181_POLICY['es']);
	$log[] = "done: CA policy page {$id} created at privadesa/app, published, hreflang en and es";
}

/** Runs once on this site. Returns the log lines (also stored), or null when there is nothing to run here. */
function rosmarops_gtm181_run() {
	$plan = rosmarops_gtm181_plan(home_url());
	if ($plan === null || get_option(ROSMAROPS_GTM181_DONE)) {
		return null;
	}
	if (!add_option(ROSMAROPS_GTM181_LOCK, time(), '', false)) {
		if (time() - (int) get_option(ROSMAROPS_GTM181_LOCK) < 600) {
			return null; // another request is running it
		}
		update_option(ROSMAROPS_GTM181_LOCK, time(), false); // a run that died more than ten minutes ago: take over
	}
	global $wpdb;
	$lang = $plan['lang'];
	$log  = ['GTM-181 promise of 0.15.0, site ' . $lang . ', ' . gmdate('Y-m-d H:i:s') . ' UTC'];

	if ($plan['policy'] !== null) {
		rosmarops_gtm181_replace_policy($lang, $plan['policy'], $log);
	} else {
		rosmarops_gtm181_create_ca_policy($log);
	}

	foreach ($plan['posts'] as $id => $slug) {
		[$p, $why] = rosmarops_gtm181_check($id, 'post', $slug, 'publish');
		if ($p === null) {
			$log[] = "skipped: line, {$why}";
		} elseif (strpos($p->post_content, ROSMAROPS_GTM181_MARK) !== false) {
			$log[] = "skipped: post {$id} {$slug} already has the line";
		} elseif ($wpdb->update($wpdb->posts, ['post_content' => rosmarops_gtm181_line($lang) . $p->post_content], ['ID' => $id]) !== 1) {
			$log[] = "failed: post {$id} {$slug} could not be written";
		} else {
			clean_post_cache($id);
			$log[] = "done: post {$id} {$slug} has the dated line";
		}
	}

	foreach ($plan['drafts'] as $id => $slug) {
		[$p, $why] = rosmarops_gtm181_check($id, 'page', $slug, 'publish');
		if ($p === null) {
			$log[] = "skipped: draft, {$why}";
		} elseif ($wpdb->update($wpdb->posts, ['post_status' => 'draft'], ['ID' => $id]) !== 1) {
			$log[] = "failed: page {$id} {$slug} could not be set to draft";
		} else {
			clean_post_cache($id);
			$log[] = "done: page {$id} {$slug} is now draft (its address is served by the static page)";
		}
	}

	update_option(ROSMAROPS_GTM181_LOG, $log, false);
	update_option(ROSMAROPS_GTM181_DONE, gmdate('c'), false);
	delete_option(ROSMAROPS_GTM181_LOCK);
	rosmarops_gtm181_write_log($lang, $log);
	return $log;
}

/** Writes the log to wp-content/rosmarops-private/ (closed to the web). */
function rosmarops_gtm181_write_log($lang, $log) {
	$dir = WP_CONTENT_DIR . '/rosmarops-private';
	if (!is_dir($dir) && !@mkdir($dir, 0750)) {
		error_log('rosmarops-gtm181: cannot create ' . $dir);
		return;
	}
	if (!file_exists($dir . '/.htaccess')) {
		@file_put_contents($dir . '/.htaccess', "Require all denied\n");
	}
	@file_put_contents($dir . "/gtm181-{$lang}.log", implode("\n", $log) . "\n");
}

add_action('wp_loaded', function () {
	if (wp_doing_ajax() || wp_doing_cron()) {
		return;
	}
	rosmarops_gtm181_run();
});
