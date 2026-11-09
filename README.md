# Mediterráneo — Evaluación 2

Proyecto web de **Mediterráneo**, un restaurante de cocina mediterránea inspirada en Grecia, Italia, España y Líbano. El repositorio reúne el sitio web del restaurante (frontend) y una solución backend desarrollada con Python y FastAPI.

El proyecto contempla carta con fotografías, promociones, reservas, contacto, delivery, carrito de compras y servicios backend para gestionar usuarios, pedidos, pagos de prueba y operaciones del restaurante.

> **Estructura del repositorio:** el frontend se encuentra en `Frontend/` y el backend en `Mediterraneo-Evaluacion2-backend/Mediterraneo-Evaluacion2-codigo/`.

## Contenido

- [Componentes del proyecto](#componentes-del-proyecto)
- [Frontend](#frontend)
- [Backend](#backend)
- [Cómo ejecutar el proyecto](#cómo-ejecutar-el-proyecto)
- [Flujo de compra de prueba](#flujo-de-compra-de-prueba)
- [Pruebas](#pruebas)
- [Documentación del backend](#documentación-del-backend)
- [Seguridad y recuperación](#seguridad-y-recuperación)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Autores](#autores)
- [Imágenes y licencia](#imágenes-y-licencia)

## Componentes del proyecto

| Componente | Ubicación | Tecnologías | Descripción |
|---|---|---|---|
| Frontend | `Frontend/` | HTML, CSS, JavaScript, Bootstrap | Sitio web del restaurante, carta, promociones, carrito y formularios. |
| Backend | `Mediterraneo-Evaluacion2-backend/Mediterraneo-Evaluacion2-codigo/` | Python, FastAPI, SQLite | Servicios, persistencia, autenticación, pedidos, pagos de prueba y operaciones del restaurante. |

La integración del frontend con el backend es opcional, de acuerdo con la aclaración docente del 8 de noviembre de 2026. El frontend recibido se conserva como apoyo de demostración. Los servicios del backend sí están integrados entre sí.

## Frontend

El frontend es un sitio web estático desarrollado con HTML, CSS y JavaScript, sin proceso de compilación ni dependencias que instalar. Puede ejecutarse de manera independiente.

### Qué incluye

| Página | Archivo | Funcionalidad |
|---|---|---|
| Inicio | `index.html` | Carrusel de promociones, novedades y accesos a Desayunos, Almuerzos y Postres. |
| Menú | `menu.html` | 13 platos con fotografía, filtro por categoría, búsqueda y opción para agregarlos al carrito. |
| Promociones | `promociones.html` | Menú del día, 15 % en desayunos, postres 2x1 y delivery gratis sobre $20.000. |
| Reserva | `reserva.html` | Formulario para grupos de 2 a 12 personas; no permite fechas pasadas. |
| Contacto | `contacto.html` | Formulario de contacto y datos del local. |
| Delivery | `delivery.html` | Información sobre cómo pedir y el reparto. |
| Nosotros | `nosotros.html` | Quiénes somos, misión, visión y equipo. |

Todas las páginas comparten:

- **Carrito de compras:** panel lateral con contador, total y opciones para quitar platos o vaciar el carrito. Conserva los datos al recargar la página.
- **Buscador:** permite buscar desde el encabezado y lleva al menú con los resultados.
- **Acceso de usuario:** modal simulado que guarda el nombre y lo muestra en el botón «Perfil».
- **Diseño responsive:** adaptación a móviles, tablets y computadores.

### Tecnologías del frontend

- **HTML5** y **CSS3**, con variables CSS para la paleta de colores.
- **JavaScript** vanilla, sin frameworks.
- **Bootstrap 5.3.8** para la grilla y componentes como carrusel, offcanvas y modal.
- **Bootstrap Icons 1.11.3**.
- **Google Fonts:** Figtree para texto y Young Serif para títulos.

Bootstrap, los íconos y las fuentes se cargan desde CDN. Se necesita conexión a Internet para visualizarlos con todos sus estilos.

### Ejecutar el frontend

1. Entra a la carpeta `Frontend/`.
2. Abre `index.html` directamente en el navegador.

También se recomienda utilizar un servidor local:

```bash
cd Frontend
python3 -m http.server 8000
```

Luego abre <http://localhost:8000>.

Si utilizas Visual Studio Code, también puedes iniciar el sitio con la extensión **Live Server**, haciendo clic derecho sobre `index.html` y seleccionando *Open with Live Server*.

### Publicar el frontend con GitHub Pages

El sitio está dentro de `Frontend/`, no en la raíz del repositorio. GitHub Pages permite publicar desde la raíz o desde una carpeta `/docs`. Hay dos alternativas:

**Opción A: publicar desde `/docs`**

1. Renombra o duplica `Frontend/` como `docs/` en la raíz del repositorio, de modo que quede `docs/index.html`.
2. Ve a **Settings → Pages**.
3. En **Build and deployment**, selecciona **Deploy from a branch**, la rama `main` y la carpeta `/docs`.
4. Guarda los cambios y espera a que se publique.

Ten en cuenta que las capturas del README están dentro de `Frontend/docs/capturas/`. Si mueves la carpeta, ajusta también las rutas de esas imágenes.

**Opción B: publicar con GitHub Actions**

1. Ve a **Settings → Pages** y selecciona **GitHub Actions**.
2. Crea `.github/workflows/pages.yml` con un flujo que publique únicamente el contenido de `Frontend/`, por ejemplo, usando `actions/upload-pages-artifact` con `path: Frontend`.
3. Cada push a `main` podrá publicar el sitio.

### Cómo funciona el frontend

- `js/carrito.js`: almacena el pedido en `localStorage`, bajo la clave `carrito`, como objetos `{ nombre, precio, cantidad }`. Incluye las funciones `agregarAlCarrito(nombre, precio)`, `quitarDelCarrito(nombre)` y `mostrarCarrito()`.
- `js/menu.js`: contiene el arreglo `platos`, genera las tarjetas y permite filtrar por categoría o texto. Admite parámetros en la URL, como `menu.html?categoria=Postres` y `menu.html?buscar=miel`.
- `js/comun.js`: gestiona el buscador y el acceso simulado de usuario. Guarda el nombre en `localStorage`, bajo la clave `usuario`.
- `js/inicio.js`: activa el carrusel de promociones y respeta la preferencia `prefers-reduced-motion`.
- `js/reserva.js` y `js/contacto.js`: validan los formularios y muestran mensajes de confirmación en la página.

### Modificar el frontend

- **Agregar un plato:** guarda su fotografía en `Frontend/imagenes/` y agrega un objeto al arreglo `platos` de `Frontend/js/menu.js`. Las categorías disponibles son `Desayunos`, `Almuerzos` y `Postres`.
- **Cambiar colores:** modifica las variables CSS al inicio de `Frontend/css/estilo.css`.
- **Cambiar promociones:** modifica las clases de imágenes del carrusel en `estilo.css` y las imágenes de las tarjetas en `promociones.html`.
- **Cambiar datos del local:** revisa los pies de página y los archivos `contacto.html`, `reserva.html` y `delivery.html`.

### Accesibilidad del frontend

- Idioma declarado mediante `lang="es"`.
- Textos alternativos en fotografías.
- Etiquetas descriptivas (`aria-label`) para botones con íconos o texto genérico.
- Indicador de foco visible para navegación con teclado.
- Contador del carrito con `aria-live` y mensajes de formularios con `role="status"`.
- Respeto por la preferencia `prefers-reduced-motion`.

### Limitaciones del frontend independiente

Cuando se ejecuta por sí solo, el frontend conserva su comportamiento estático:

- Los formularios de reserva y contacto muestran una confirmación, pero no envían información a un servidor.
- El inicio de sesión es simulado y no valida ni almacena contraseñas.
- El carrito no procesa pagos; el flujo independiente informa que el pedido se confirma por teléfono o WhatsApp.
- El carrito y el nombre de usuario se almacenan en el `localStorage` del navegador.

Estas limitaciones describen el frontend ejecutado de forma independiente; las funcionalidades y flujos del backend se detallan a continuación.

## Backend

Backend desarrollado en **Python y FastAPI** para gestionar los datos y eventos de Mediterráneo. Incluye los diez módulos de la evaluación, microservicios privados, persistencia SQLite por servicio, autenticación real, API Gateway, gestor de secretos local y GraphQL.

### Tecnologías y arquitectura

- Python y FastAPI.
- SQLite, con una base de datos por servicio.
- Microservicios con comunicación interna protegida.
- API Gateway como punto de entrada externo.
- Autenticación mediante JWT y sesiones.
- Gestor local de secretos.
- API GraphQL y contratos OpenAPI.

Se eligieron FastAPI y SQLite siguiendo la indicación de utilizar Python/FastAPI trabajada en clases. El documento de referencia Caso19 menciona Oracle y .NET/J2EE; esta diferencia se declara en el informe del proyecto.

### Requisitos

- **Python 3.12 o 3.14**, con pip.
- Apache y XAMPP no son necesarios.

La ejecución original se verificó con Python 3.12 y el recorrido manual del estudiante funcionó en Windows con Python 3.14.

### Ejecutar el backend en Windows

Abre una terminal dentro de:

```text
Mediterraneo-Evaluacion2-backend/Mediterraneo-Evaluacion2-codigo/
```

Crea el entorno virtual, instala las dependencias e inicia los servicios:

```bat
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -X utf8 scripts\iniciar.py
```

También puedes utilizar `iniciar.bat` después de instalar las dependencias.

### Ejecutar el backend en Linux o macOS

Desde la carpeta `Mediterraneo-Evaluacion2-backend/Mediterraneo-Evaluacion2-codigo/`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/iniciar.py
```

### Acceder al backend

Abre <https://localhost:8443>.

En el primer inicio se genera un certificado autofirmado para desarrollo. El navegador mostrará una advertencia hasta que confíes en `.runtime/cert.pem`. Comprueba que estás accediendo a tu servidor local antes de aceptar el certificado. Los clientes internos verifican ese certificado; para una instalación pública se necesita un certificado válido de la organización.

Mantén abierta la terminal mientras utilizas el sistema. **Ctrl+C detiene todos los servicios.** Si necesitas detener una instancia anterior en Windows, abre otra terminal en la carpeta del backend y ejecuta:

```bat
.venv\Scripts\python -X utf8 scripts\detener.py
```

Los datos se guardan en `.runtime/data/` y se conservan al reiniciar. La configuración inicial no reemplaza las claves existentes. Si un puerto está ocupado, cierra la instancia anterior y vuelve a iniciar.

## Flujo de compra de prueba

El primer arranque genera cuentas de demostración `admin`, `owner`, `cashier` y `dispatch` en:

```text
.runtime/cuentas-demo.json
```

Abre ese archivo local para consultar los correos y las claves generadas. Utiliza solamente datos ficticios.

1. Entra a **Mi cuenta** y crea una cuenta con un RUN de prueba cuyo dígito verificador sea válido y una contraseña de al menos 10 caracteres.
2. En otra terminal, desde la carpeta del backend, ejecuta:

   ```bat
   .venv\Scripts\python -X utf8 scripts\operador.py correos
   ```

   Esta consola representa el buzón sandbox del proveedor. Copia el código de verificación de tu cuenta.
3. En **Mi cuenta**, ingresa el código en **Verificar correo**. Luego inicia sesión desde **Perfil**.
4. Agrega platos desde **Menú**, abre el carrito y elige **Pedir por delivery**. Escribe solamente la dirección. Para una prueba sin Internet, utiliza `Dirección de prueba 123, Santiago`. Los domicilios reales se consultan mediante Photon y deben quedar dentro de 3 km del punto de referencia.
5. En **Mi cuenta**, selecciona **Iniciar pago de prueba** y copia el identificador generado.
6. En la terminal del operador, aprueba el pago:

   ```bat
   .venv\Scripts\python -X utf8 scripts\operador.py aprobar IDENTIFICADOR_DEL_PAGO
   ```

7. Actualiza tus pedidos: el pedido aparecerá como pagado. Puedes consultar el comprobante y anularlo antes de iniciar la preparación.
8. Con una cuenta de cajero o administración, entra a **Gestión del restaurante**. Desde allí puedes enviar el comprobante al buzón de prueba, imprimir la orden de despacho y avanzar por los estados preparando → despachado → entregado.

El operador sandbox tiene una identidad técnica independiente y no permite que el comprador declare pagado su propio pedido. El aviso de pago lleva firma HMAC, fecha y evento idempotente.

**El entorno de demostración no realiza cobros, envía correos externos ni emite documentos tributarios reales.** El adaptador conserva los contratos y las transiciones para la demostración académica.

## Pruebas

Con la aplicación normal detenida y los puertos libres, ejecuta desde la carpeta del backend:

```bat
.venv\Scripts\python -X utf8 scripts\verificar.py
```

El script crea un entorno temporal independiente, inicia los nueve procesos, ejecuta pruebas HTTP, inyecta fallos de dependencias, mide carga y verifica la persistencia después de un reinicio completo. No elimina ni modifica los datos de tu instancia normal. Vuelve a escribir las evidencias de `docs/` con los resultados obtenidos en tu equipo.

### Comprobación opcional del navegador

Si tienes Node.js, puedes realizar pruebas adicionales con Playwright:

```bat
npm install --no-save playwright
npx playwright install chromium
.venv\Scripts\python -X utf8 scripts\verificar.py --navegador
```

No entregues `node_modules/`. Los cuatro anchos seleccionados para la comprobación son 375, 768, 1024 y 1440 píxeles. La disponibilidad y los resultados observados están detallados en el informe.

## Documentación del backend

Dentro de `Mediterraneo-Evaluacion2-backend/Mediterraneo-Evaluacion2-codigo/` se encuentra la documentación técnica:

- `docs/Informe.html`: informe de arquitectura y de los diez módulos, legible sin Internet.
- `docs/Informe.md`: versión editable del informe.
- `docs/diagramas/`: UML de dominio, UML del gateway, componentes y secuencia; incluye fuentes Graphviz DOT y Mermaid, además de versiones SVG.
- `docs/servicios.csv`, `docs/permisos.csv` y `docs/trazabilidad.csv`: matrices editables.
- `docs/contratos/`: contratos OpenAPI de los servicios, schema GraphQL y ejemplos ficticios.
- `docs/resultados-*.json` y `docs/resultados-pruebas.xml`: resultados de pruebas obtenidos.
- `docs/resultados-revision-final.json`: repetición de pruebas del 8 de noviembre sobre una copia recién extraída. Las cifras anteriores del informe corresponden a la ejecución del 7 de noviembre.
- `docs/Capturas.md`: guía de capturas del informe.

## Seguridad y recuperación

- Solo `gateway:8443` sirve páginas externas. Los demás procesos escuchan exclusivamente en `127.0.0.1`, utilizan HTTPS y exigen identidad de servicio en sus operaciones. No expongas los puertos privados a todas las interfaces de red.
- No subas `.runtime/`, `.venv/`, `node_modules/`, claves, contraseñas ni datos de ejecución. El `.gitignore` del backend excluye estos contenidos.
- Los JWT se almacenan en cookies `HttpOnly`, `Secure` y `SameSite Strict`; caducan a los 30 minutos. El cierre de sesión y los cambios de rol revocan sesiones. Las operaciones autenticadas requieren protección CSRF.
- Si un pedido queda en estado `cancelando`, entra con administración y utiliza **Reconciliar pedidos interrumpidos o vencidos**. La operación también libera reservas impagas de más de 15 minutos. Debe ejecutarse periódicamente durante la demostración; no se incluye un scheduler de producción.
- Para rotar identidades y claves después de una filtración, detén el sistema y ejecuta `scripts/rotar.py`. Luego reinicia. Esta operación invalida las sesiones anteriores, pero no borra los pedidos.
- Para respaldar los datos, copia las bases con los procesos detenidos y conserva la configuración cifrada en un lugar seguro.

## Direcciones de delivery

El navegador envía únicamente la dirección y los ítems. El servicio Orders solicita la ubicación al adaptador privado provider y calcula el radio de cobertura. Los campos `lat` y `lon` del contrato anterior siguen siendo opcionales por compatibilidad, pero se ignoran al decidir la cobertura.

Para demostrar el flujo sin Internet existe el domicilio ficticio `Dirección de prueba 123, Santiago`. El alias `Direccion ficticia 123` se conserva para pruebas anteriores. Este catálogo de demostración no asigna ubicaciones inventadas a domicilios reales.

Para direcciones reales se consulta Photon mediante HTTPS. La configuración contempla un plazo de cinco segundos, una consulta simultánea, un intervalo mínimo de un segundo y caché local de 24 horas. Solo se transmite el texto de la dirección. El formulario informa el proveedor y muestra atribución a OpenStreetMap.

- Servicio: <https://photon.komoot.io/api/>
- Proyecto Photon: <https://github.com/komoot/photon>
- Documentación de la API: <https://github.com/komoot/photon/blob/master/docs/api-v1.md>

La URL del geocodificador puede cambiarse mediante la variable `GEOCODER_URL` al iniciar los servicios, sin modificar el frontend. Si no se encuentra un domicilio numerado, hay varias coincidencias, está fuera de cobertura o el proveedor falla, el pedido no se crea y no se reserva stock.

El geocodificador ayuda a ubicar un domicilio, pero no acredita que una persona resida en él. Las pruebas automatizadas utilizan un proveedor HTTP local controlado, sin enviar domicilios ficticios al servidor público. La conectividad al servidor Photon desde el equipo del estudiante no ha sido confirmada.

## Decisiones y alcance académico

Las reglas del caso de referencia de sushi se adaptan al restaurante Mediterráneo, conservando el frontend y su carta. El informe identifica los límites del proveedor de prueba, la boleta académica y las decisiones propuestas sobre horarios, delivery y promociones. Estas adaptaciones no se presentan como instrucciones verbales confirmadas.

La portada de la Evaluación 2 indica el 9 de noviembre de 2026; otra sección deja la fecha y el medio sujetos a comunicación del docente.

## Estructura del repositorio

La estructura general del repositorio es la siguiente:

```text
DesarrolloWeb/
├── Frontend/
│   ├── index.html
│   ├── menu.html
│   ├── promociones.html
│   ├── reserva.html
│   ├── contacto.html
│   ├── delivery.html
│   ├── nosotros.html
│   ├── css/
│   │   └── estilo.css
│   ├── js/
│   │   ├── comun.js
│   │   ├── carrito.js
│   │   ├── inicio.js
│   │   ├── menu.js
│   │   ├── reserva.js
│   │   └── contacto.js
│   ├── imagenes/
│   └── docs/capturas/
│
└── Mediterraneo-Evaluacion2-backend/
    └── Mediterraneo-Evaluacion2-codigo/
        ├── scripts/
        ├── docs/
        │   ├── diagramas/
        │   └── contratos/
        ├── requirements.txt
        ├── iniciar.bat
        └── ...
```

La estructura interna del backend puede ampliarse con los archivos y directorios de ejecución que se generan localmente. No subas `.runtime/`, `.venv/` ni `node_modules/` al repositorio.

## Autores

**Frontend:**
- Maximiliano Urizar
- Fabian Monardez

**Backend:** solución desarrollada para la Evaluación 2 de Mediterráneo.

## Imágenes y licencia

Las fotografías de la carpeta `Frontend/imagenes/` son material de terceros y no fueron tomadas por los autores; pertenecen a sus respectivos dueños. Antes de reutilizar el proyecto con fines comerciales, verifica los derechos de cada imagen o reemplázalas por fotografías propias.

Este repositorio todavía no define una licencia para el código. Si quieres permitir que otras personas reutilicen el proyecto, agrega un archivo `LICENSE` (por ejemplo, [MIT](https://choosealicense.com/licenses/mit/)).
