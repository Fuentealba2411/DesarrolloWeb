const contenido = document.getElementById('gestionContenido');
function accion(texto, fn) {
    const b = document.createElement('button'); b.className = 'btn btn-borde-rojo m-1'; b.textContent = texto;
    b.addEventListener('click', async () => {b.disabled = true; try {await fn();} catch (e) {aviso(e.message, true);} finally {b.disabled = false;}}); return b;
}
function seccion(titulo) {const h = document.createElement('h2'); h.className = 'mt-5';h.textContent = titulo;contenido.append(h);}
function datos(value) {
    const caja = document.createElement('div'); caja.className = 'resultado-json';
    const etiquetas = {total:'Total CLP',items:'Platos',direccion:'Dirección',nombre:'Plato',cantidad:'Cantidad',precio:'Precio unitario',descuento:'Descuento',subtotal:'Subtotal',ventas:'Ventas',moneda:'Moneda',desde:'Desde',hasta:'Hasta',id:'Número',orden:'Orden',created:'Fecha de registro',data:'Mensaje',correo:'Correo',mensaje:'Mensaje'};
    function agregar(parent, objeto) {
        if (Array.isArray(objeto)) {const lista = document.createElement('ul');for(const elemento of objeto) {const li = document.createElement('li');agregar(li,elemento);lista.append(li);}parent.append(lista);}
        else if (objeto && typeof objeto === 'object') {for(const [key,val] of Object.entries(objeto)) {const p = document.createElement('div');const label = document.createElement('strong');label.textContent = (etiquetas[key] || key) + ': ';p.append(label);agregar(p,val);parent.append(p);}}
        else parent.append(document.createTextNode(String(objeto ?? '')));
    }
    agregar(caja,value);return caja;
}
function productoForm(p = {}) {
    const f = document.createElement('form'); f.className = 'row g-2 border p-3 my-3';
    for (const [nombre, tipo] of [['nombre','text'],['categoria','text'],['descripcion','text'],['precio','number'],['imagen','text'],['stock','number']]) {
        const c = document.createElement('div');c.className = 'col-md-6';const label = document.createElement('label');label.textContent = nombre;
        const input = document.createElement('input');input.className = 'form-control'; input.name = nombre;input.type = tipo;input.value = p[nombre] ?? '';input.required = true;
        if (tipo === 'number') input.min = nombre === 'precio' ? 1 : 0;
        label.append(input);c.append(label);f.append(c);
    }
    const label = document.createElement('label');const check = document.createElement('input');check.type = 'checkbox';check.checked = p.disponible ?? true;label.append(check, ' Disponible');f.append(label);
    const b = document.createElement('button');b.className = 'btn btn-rojo';b.textContent = p.id ? 'Guardar producto ' + p.id : 'Crear producto';f.append(b);
    f.addEventListener('submit', async e => {
        e.preventDefault();b.disabled = true;
        const d = Object.fromEntries(new FormData(f));d.precio = Number(d.precio);d.stock = Number(d.stock);d.disponible = check.checked;
        try {await api('/admin/products' + (p.id ? '/' + p.id : ''), {method: p.id ? 'PUT' : 'POST', body: JSON.stringify(d)});aviso('Producto guardado.');} catch (e) {aviso(e.message, true);} finally {b.disabled = false;}
    });
    if (p.id) f.append(accion('Desactivar', async () => {await api('/admin/products/' + p.id, {method: 'DELETE'});await cargarGestion();}));
    return f;
}
async function cargarGestion() {
    contenido.textContent = 'Cargando…';
    try {
        const lista = await api('/orders?limit=100'); contenido.replaceChildren();seccion('Pedidos');
        for (const p of lista) {
            const caja = document.createElement('article');caja.className = 'plato p-3 mb-3';
            const h = document.createElement('h3');h.textContent = p.id + ' · ' + p.status; caja.append(h, datos({total: p.total, items: p.items, direccion: p.address}));
            const siguiente = {pagado:'preparando', preparando:'despachado', despachado:'entregado'}[p.status];
            if (siguiente) caja.append(accion('Pasar a ' + siguiente, async () => {await api('/orders/' + p.id + '/status', {method:'PUT',body:JSON.stringify({status:siguiente})});await cargarGestion();}));
            caja.append(accion('Orden de despacho / imprimir', async () => {caja.append(datos(await api('/orders/' + p.id + '/dispatch')));window.print();}));
            caja.append(accion('Enviar comprobante', async () => {aviso((await api('/orders/' + p.id + '/receipt-email', {method:'POST'})).message);}));
            caja.append(accion('Anular con motivo', async () => {const motivo = prompt('Motivo de anulación:');if(motivo) {await api('/orders/' + p.id + '/cancel', {method:'POST',body:JSON.stringify({motivo})});await cargarGestion();}}));contenido.append(caja);
        }
        if (!lista.length) contenido.append('No hay pedidos.');
        // Cada bloque solicita su permiso al servidor; el fallo de uno no oculta los demás.
        try {
            const productos = await api('/admin/products');seccion('Productos');contenido.append(productoForm());
            for (const p of productos) contenido.append(productoForm(p));
        } catch {}
        try {
            await api('/reports/sales');seccion('Ventas por período');
            const f = document.createElement('form');f.className = 'd-flex flex-wrap gap-2';
            const desde = document.createElement('input'), hasta = document.createElement('input');desde.type = hasta.type = 'date';desde.required = hasta.required = true;desde.ariaLabel = 'Desde';hasta.ariaLabel = 'Hasta';
            const b = document.createElement('button');b.textContent = 'Consultar ventas';b.className = 'btn btn-rojo';f.append(desde,hasta,b);const result = document.createElement('div');
            f.addEventListener('submit', async e => {e.preventDefault();try {const a = Math.floor(new Date(desde.value+'T00:00:00-03:00').getTime()/1000), z = Math.floor(new Date(hasta.value+'T23:59:59-03:00').getTime()/1000);result.replaceChildren(datos(await api('/reports/sales?desde='+a+'&hasta='+z)));} catch(e) {aviso(e.message,true);}});contenido.append(f,result);
        } catch {}
        try {
            const users = await api('/users');seccion('Usuarios y permisos');
            contenido.append(accion('Reconciliar pedidos interrumpidos o vencidos',async () => {aviso(JSON.stringify(await api('/admin/reconcile',{method:'POST'})));await cargarGestion();}));
            for (const u of users) {
                const p = document.createElement('p');p.textContent = u.email + ' · ' + u.role;
                const select = document.createElement('select');select.ariaLabel = 'Perfil de '+u.email;
                for (const rol of ['client','admin','owner','cashier','dispatch']) {const o = document.createElement('option');o.value = rol;o.textContent = rol;select.append(o);}select.value = u.role;
                const active = document.createElement('input');active.type = 'checkbox';active.checked = !!u.active;active.ariaLabel = 'Cuenta activa';p.append(select,active,accion('Guardar rol / estado',async () => {await api('/users/'+u.id,{method:'PUT',body:JSON.stringify({role:select.value,active:active.checked})});aviso('Cuenta actualizada.');}));contenido.append(p);
            }
            seccion('Clientes');
            for (const cliente of await api('/profiles')) {
                const p = document.createElement('p');p.textContent = cliente.nombre + ' · ' + cliente.correo;
                p.append(accion('Actualizar dirección', async () => {const direccion = prompt('Nueva dirección:', cliente.direccion);if(direccion) {await api('/profiles/'+cliente.id,{method:'PUT',body:JSON.stringify({direccion})});aviso('Cliente actualizado.');}}));contenido.append(p);
            }
            contenido.append('Para registrar un cliente desde administración, usa Crear cuenta en Mi cuenta. También se requiere verificación de correo.');
            seccion('Contacto');contenido.append(datos(await api('/contact')));
            seccion('Reservas');
            for (const r of await api('/reservations')) {
                const p = document.createElement('p');p.textContent = r.fecha+' · '+r.personas+' personas · '+r.status;
                for (const status of ['confirmada','cancelada']) p.append(accion(status,async () => {await api('/reservations/'+r.id,{method:'PUT',body:JSON.stringify({status})});await cargarGestion();}));contenido.append(p);
            }
        } catch {}
        document.getElementById('gestionEstado').textContent = 'Las operaciones disponibles dependen de tu perfil. El servidor comprueba cada solicitud.';
    } catch (e) {contenido.textContent = e.message;}
}
document.getElementById('actualizarGestion').addEventListener('click',cargarGestion);cargarGestion();
