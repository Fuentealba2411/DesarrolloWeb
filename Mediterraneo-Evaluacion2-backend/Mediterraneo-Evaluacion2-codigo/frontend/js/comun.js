// La sesión queda en cookie HttpOnly; JavaScript nunca almacena el JWT.
async function api(ruta, opciones = {}) {
    const csrf = document.cookie.split('; ').find(x => x.startsWith('csrf='))?.split('=')[1] || '';
    const respuesta = await fetch('/api' + ruta, {
        ...opciones,
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf, ...(opciones.headers || {})},
        credentials: 'same-origin'
    });
    const datos = await respuesta.json();
    if (!respuesta.ok) throw new Error(typeof datos.detail === 'string' ? datos.detail : 'Revisa los datos e inténtalo nuevamente.');
    return datos;
}
function aviso(texto, error = false) {
    let caja = document.getElementById('avisoGlobal');
    if (!caja) {
        caja = document.createElement('div'); caja.id = 'avisoGlobal'; caja.role = 'status';
        document.querySelector('main').prepend(caja);
    }
    caja.className = 'container alert ' + (error ? 'alert-danger' : 'alert-success');
    caja.textContent = texto;
}
const parametrosUrl = new URLSearchParams(window.location.search);
const buscar = document.getElementById('buscar');
if (buscar) buscar.value = parametrosUrl.get('buscar') || '';
localStorage.removeItem('usuario'); // Se descarta la identidad simulada del prototipo.
const acceso = document.getElementById('formularioAcceso');
if (acceso) {
    const ayuda = document.createElement('p'); ayuda.className = 'px-3';
    const enlace = document.createElement('a'); enlace.href = 'cuenta.html'; enlace.textContent = 'Crear cuenta, verificar correo o ver mis pedidos';
    ayuda.append(enlace); acceso.append(ayuda);
    acceso.addEventListener('submit', async function (e) {
        e.preventDefault(); const boton = this.querySelector('[type=submit]'); boton.disabled = true;
        try {
            await api('/auth/login', {method: 'POST', body: JSON.stringify({correo: document.getElementById('correoAcceso').value, clave: document.getElementById('claveAcceso').value})});
            location.href = 'cuenta.html';
        } catch (error) {
            let mensaje = acceso.querySelector('[role=alert]');
            if (!mensaje) {mensaje = document.createElement('p'); mensaje.role = 'alert'; mensaje.className = 'text-danger px-3'; acceso.prepend(mensaje);}
            mensaje.textContent = error.message;
        } finally {boton.disabled = false;}
    });
}
// Los destacados consultan el mismo catálogo y precio que el menú.
for (const boton of document.querySelectorAll('[data-plato]')) {
    boton.addEventListener('click', async () => {
        try {
            const productos = await api('/products');
            const plato = productos.find(p => p.nombre === boton.dataset.plato);
            if (!plato || !plato.stock) throw new Error('Producto no disponible.');
            agregarAlCarrito(plato.nombre, plato.precio, plato.id);
            aviso(plato.nombre + ' agregado al carrito.');
        } catch (error) {aviso(error.message, true);}
    });
}
if (document.querySelector('[data-plato]')) {
    api('/products').then(productos => {
        for (const boton of document.querySelectorAll('[data-plato]')) {
            const p = productos.find(p => p.nombre === boton.dataset.plato);
            boton.disabled = !p || !p.stock;
            const precio = boton.closest('.destacado')?.querySelector('.precio');
            if (precio) precio.textContent = p ? '$' + p.precio.toLocaleString('es-CL') : 'No disponible';
        }
    }).catch(() => aviso('No pudimos actualizar los destacados. Reintenta desde Menú.', true));
}
