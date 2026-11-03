<?php
/**
 * Plugin Name: RosmarOps retired posts
 * Description: Legacy Spanish blog posts and topic pages retired from rosmarops.com (selection in the claude.ai project, claude/criba-blog-heredado.md, group 3; asked by Albert 2026-11-03 19:48). Each listed /es/blog/<slug>/ answers 301 to /es/blog/, also when the post is a draft. A category or tag archive under /es/blog/ with no published posts answers 301 to /es/blog/ too. Nothing is deleted. Versioned in qtorb/rosmarops-web; do not edit on the server.
 */

if (!defined('ABSPATH')) {
	exit;
}

const ROSMAROPS_RETIRED_HOME = '/es/blog/';
const ROSMAROPS_RETIRED = [
	'adversarial-seo-en-resultados-de-busqueda-generativa-sge',
	'agentes-autonomia',
	'ai-seo',
	'ai-seo-adversarial-protocolos-ofensivos-prompt-injection',
	'ai-seo-optimizacion-avanzada-para-buscadores-en-la-era-de-la-ia',
	'amenazas-emergentes-como-la-ia-esta-transformando-el-panorama-de-la-ciberseguridad',
	'analisis-forense-impulsado-por-ia-el-futuro-de-la-investigacion-post-incidente',
	'analisis-predictivo-con-ia-para-anticipar-tendencias-de-busqueda',
	'arquitectura-de-bots-diseno-pruebas-y-optimizacion',
	'arquitectura-de-un-dron-de-guerra-cuando-el-software-vale-mas-que-el-hardware',
	'ataques-de-contenido-fantasma-como-ocupar-espacio-en-los-motores-de-ia-antes-que-la-competencia',
	'automatizacion-de-ataques-adversariales-seo-con-llms-open-source',
	'automatizacion-de-la-monitorizacion-de-la-reputacion-online-con-ia-innovacion-beneficios-y-desafios',
	'black-hat-vs-seo-adversarial-donde-esta-el-limite-entre-estrategia-y-sabotaje',
	'botnets-la-evolucion-de-las-infraestructuras-ciberneticas-maliciosas',
	'bots-y-seo-adversarial-el-lado-oscuro-de-la-optimizacion-web',
	'ciberataques-impulsados-por-ia-generativa-la-nueva-frontera-de-las-amenazas-digitales',
	'ciberseguridad-en-dispositivos-iot-amenazas-ataques-automatizados-y-estrategias-de-defensa',
	'ciberseguridad-en-el-aire-como-sobrevivir-a-la-guerra-electronica',
	'ciberseguridad-en-ia',
	'como-construir-un-ejercito-de-bots-para-manipulacion-de-seo-guia-tecnica',
	'como-crear-un-bot-desde-cero-guia-practica-para-principiantes',
	'como-detectar-contenido-generado-por-ia-malicioso-en-los-primeros-resultados-de-busqueda',
	'como-enganar-sistemas-de-deteccion-de-contenido-ia-desde-una-perspectiva-seo',
	'como-identificar-y-neutralizar-un-ataque-de-seo-adversarial-en-tu-sitio-web',
	'como-los-atacantes-manipulan-llms-con-prompt-injection-y-como-defenderte',
	'como-un-prompt-malicioso-puede-convertir-tu-chatbot-en-un-insider-threat',
	'computacion-cuantica-y-su-impacto-en-ciberseguridad',
	'cuando-el-protocolo-canonico-ya-viene-roto',
	'cuando-optimizar-para-llms-te-convierte-en-atacante',
	'ddos-en-el-contexto-de-la-guerra-de-la-informacion-5gw-parte-1',
	'ddos-en-el-contexto-de-la-guerra-de-la-informacion-5gw-parte-2',
	'deepfakes-desafios-para-la-seguridad-digital',
	'deepfakes-en-audio-riesgos-deteccion-y-contramedidas-para-marcas-y-figuras-publicas',
	'deepfakes-en-operaciones-militares-como-el-contenido-sintetico-se-convirtio-en-arma-tactica',
	'del-campo-de-batalla-a-la-innovacion-tecnologica-como-los-drones-reescriben-la-guerra-moderna',
	'descifrando-la-caja-negra-ingenieria-inversa-del-algoritmo-de-google-mediante-ataques-adversariales-controlados',
	'detectando-seo-poisoning-guia-para-identificar-resultados-de-busqueda-maliciosos',
	'drones-de-fibra-optica-y-kill-chains-a-60-segundos-cuando-la-ciberguerra-se-fusiona-con-el-aire',
	'drones-trampa-la-guerra-cibernetica-se-infiltra-en-ucrania',
	'ejercitos-de-un-solo-prompt-bots-agenticos-a-escala',
	'el-agente-ya-no-asiste-ejecuta-el-ataque-completo',
	'el-dilema-del-prisionero-llego-a-los-llms-cuando-envenenar-la-memoria-de-tu-asistente-es-un-servicio-de-marketing',
	'el-impacto-de-los-modelos-de-ia-locales-en-el-seo',
	'el-malware-la-amenaza-invisible-del-mundo-digital',
	'entre-escudos-y-brechas-como-un-waf-puede-proteger-o-bloquear-tu-aplicacion-web',
	'estrategias-fundamentales-de-ai-seo-en-perplexity-guia-de-rosmarops',
	'evolucion-de-los-sistemas-de-defensa-de-google',
	'falsos-positivos-y-reglas-adaptativas-la-cara-b-de-tu-waf',
	'guerra-de-la-informacion-iw',
	'guia-avanzada-de-ai-seo-en-perplexity-para-rosmarops-2a-parte',
	'herramientas-de-monitorizacion-para-detectar-ataques-seo',
	'honeypots-de-contenido-como-identificar-que-buscan-los-motores-de-ia-y-adaptarte-antes-que-nadie',
	'ia-adversarial-generacion-y-deteccion-de-contenido-sintetico',
	'ia-como-herramienta-defensiva-en-ciberseguridad',
	'ia-seo-como-posicionar-contenido-en-motores-de-busqueda-basados-en-ia-chatgpt-perplexity-copilot-y-gemini',
	'ia-vs-ia-en-la-iw-contraataques-algoritmicos-y-defensas-generativas',
	'ingenieria-de-incepcion-manipulacion-de-vectores-semanticos-en-la-guerra-cognitiva',
	'ingenieria-inversa-de-algoritmos-de-recomendacion-manipulacion-de-la-opinion-publica',
	'ingenieria-inversa-de-motores-de-busqueda-ia-como-entender-su-ranking-en-base-a-respuestas-generadas',
	'ingenieria-social-con-ia-la-nueva-era-del-phishing-y-la-manipulacion-digital',
	'innovacion-bajo-presion-lecciones-para-la-defensa-digital-del-futuro',
	'la-amenaza-oculta-de-los-ataques-ddos-contra-apis-y-servicios-en-la-nube-una-guia-completa',
	'la-era-cuantica-en-la-guerra-de-la-informacion',
	'la-instruccion-como-vector-de-ataque-la-inyeccion-de-prompts-como-vulnerabilidad-de-diseno',
	'la-memoria-como-superficie-de-ataque-cuando-el-seo-se-vuelve-persistente',
	'la-optimizacion-invisible-cuando-envenenar-la-memoria-del-asistente-se-convierte-en-estrategia-seo',
	'lagunas-algoritmicas-en-ia-como-posicionar-contenido-estrategicamente',
	'los-bots-en-el-ecosistema-digital-funcionamiento-aplicaciones-y-consideraciones-eticas',
	'malware-sin-archivos-el-fantasma-digital-que-burla-tus-defensas',
	'narrativas-que-se-autocorrigen-cuando-la-ia-reescribe-su-propio-historial',
	'optimizacion-de-ataques-semanticos-como-hacer-que-un-termino-se-relacione-exclusivamente-con-tu-marca',
	'owasp-zed-attack-proxy-zap-una-herramienta-esencial-para-la-seguridad-de-aplicaciones-web',
	'personalizacion-semantica-contextual-tecnicas-para-adaptar-tu-contenido-al-contexto-del-usuario-con-ia',
	'prompt-injection-bots-atacando-asistentes-de-ia-mediante-entradas-automatizadas',
	'proteger-la-era-post-prompt-por-que-los-waf-clasicos-ya-no-son-suficientes',
	'rag-envenena-mas-rapido-de-lo-que-google-indexa',
	'redes-de-proxys-dinamicas-la-clave-para-el-anonimato-y-la-flexibilidad-en-linea',
	'saturacion-de-corpus-el-ddos-silencioso-contra-la-memoria-del-modelo',
	'seguridad-en-activos-espaciales-el-nuevo-frente-de-la-ciberseguridad',
	'seo-adversarial',
	'seo-inverso-en-ia-como-hacer-que-la-competencia-pierda-relevancia-sin-caer-en-lo-black-hat',
	'seo-multimodal-2025-7-estrategias-para-dominar-busquedas-por-voz-imagen-y-texto-en-ia',
	'seo-ofensivo-con-embeddings-y-vectores-semanticos-como-manipular-asociaciones-tematicas',
	'seo-poisoning-protegiendo-tu-marca-de-la-manipulacion-maliciosa-en-buscadores',
	'seo-tecnico-para-apis-de-ia-hacer-que-tu-contenido-sea-compatible-y-facilmente-procesable-por-agentes-inteligentes-y-sistemas-de-terceros',
	'silencio-como-vector-ddos-que-ensenan-a-los-llms-a-olvidar',
	'sistemas-inmunologicos-digitales-como-la-ia-biomimetica-esta-transformando-la-ciberseguridad',
	'swarming-la-nueva-generacion-de-ataques-coordinados-por-ia',
	'zero-day-psicologicos-vulnerabilidades-emocionales-sin-parche',
];

/** Target of a request URI if it is a retired post or page (or a sub-path such as its feed), else null. */
function rosmarops_retired_target($request_uri) {
	$path = parse_url((string) $request_uri, PHP_URL_PATH);
	if (!is_string($path) || strpos($path, ROSMAROPS_RETIRED_HOME) !== 0) {
		return null;
	}
	$parts = explode('/', trim(substr($path, strlen(ROSMAROPS_RETIRED_HOME)), '/'));
	$slug  = rawurldecode($parts[0] ?? '');
	return in_array($slug, ROSMAROPS_RETIRED, true) ? ROSMAROPS_RETIRED_HOME : null;
}

add_action('template_redirect', function () {
	$target = rosmarops_retired_target($_SERVER['REQUEST_URI'] ?? '');
	if ($target === null && (is_category() || is_tag())) {
		$term = get_queried_object();
		$uri  = (string) ($_SERVER['REQUEST_URI'] ?? '');
		if ($term && isset($term->count) && (int) $term->count === 0 && strpos($uri, ROSMAROPS_RETIRED_HOME) === 0) {
			$target = ROSMAROPS_RETIRED_HOME;
		}
	}
	if ($target !== null) {
		wp_redirect(rosmarops_retired_root() . $target, 301, 'RosmarOps');
		exit;
	}
}, 0);

/** Scheme and host of the site, without a path: the multisite /es/ site's home_url() already ends in /es. */
function rosmarops_retired_root() {
	$p = wp_parse_url(home_url());
	return $p['scheme'] . '://' . $p['host'] . (isset($p['port']) ? ':' . $p['port'] : '');
}
