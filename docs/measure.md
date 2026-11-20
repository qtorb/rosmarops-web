# Cómo se mide el repositorio de plantillas (GTM-188 §4)

Propuesta firmada: vigil `docs/research/2026-11-19-plantillas-abiertas-propuesta.md` §5. Se mide 30 días después de que la exportación de BV-266 llene `qtorb/rosmarops-templates`. Ningún enlace lleva parámetros de seguimiento.

| Número | Dónde se lee | Quién | Cómo |
| --- | --- | --- | --- |
| Estrellas | Página del repositorio, o `stargazers_count` en `GET /repos/qtorb/rosmarops-templates` | Cualquiera | El valor del día 30 |
| Visitantes del repositorio | Insights › Traffic de `qtorb/rosmarops-templates` | Albert, porque hace falta ser administrador | Suma de «Unique visitors» de los 14 días que muestra GitHub. Hay que anotarla los días 14 y 28, porque GitHub solo guarda 14 días |
| Visitas a rosmarops.com con procedencia github.com | `GET https://rosmarops.com/wp-json/rosmarops/v1/visits`, contador propio | Cualquiera, son públicos | Suma de las filas con procedencia `github` de los 30 días; personas distintas, en `people` con la misma procedencia. Comparar con los 30 días anteriores |

## Lo que el contador no distingue

- **Qué repositorio de GitHub.** La procedencia `github` es cualquier página de `github.com`: este repositorio, el de RosmarOps, el del plugin o cualquier otro. El contador solo guarda el tipo de procedencia, no la página. Por eso el número es un tope, no lo que trae este repositorio solo. La comparación con los 30 días anteriores es lo que da una idea.
- **Los clics en descargar no guardan procedencia, y no la van a guardar.** Decidido por Albert el 20-11-2026: no se guarda la procedencia de los clics de descarga. La llegada desde GitHub se mide solo con las visitas a rosmarops.com de procedencia `github`. El contador de descargas sigue guardando día, página de origen, idioma y sistema, y nada más (`wp/mu-plugins/rosmarops-downloads.php`, línea 4).
