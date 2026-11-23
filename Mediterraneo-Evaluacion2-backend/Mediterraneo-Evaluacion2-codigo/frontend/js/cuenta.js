function boton(texto, accion) {
    const b = document.createElement('button'); b.className = 'btn btn-borde-rojo m-1'; b.textContent = texto;
    b.addEventListener('click', async () => {b.disabled = true; try {await accion();} catch (e) {aviso(e.message, true);} finally {b.disabled = false;}}); return b;
}
async function cargarPedidos() {
    const lista = document.getElementById('pedidos'); lista.textContent = 'Cargando pedidos…';
    try {
        const r = await api('/graphql', {method: 'POST', body: JSON.stringify({query: '{ misPedidos(limit: 20) { id estado total aviso lineas { nombre cantidad subtotal descripcionActual } } }'})});
        if (r.errors) throw new Error(r.errors[0].message);
        lista.replaceChildren();
        if (!r.data.misPedidos.length) lista.textContent = 'Todavía no tienes pedidos.';
        for (const pedido of r.data.misPedidos) {
            const caja = document.createElement('article'); caja.className = 'plato p-3 mb-3';
            const titulo = document.createElement('h3'); titulo.textContent = pedido.id + ' · ' + pedido.estado;
            const detalle = document.createElement('p'); detalle.textContent = pedido.lineas.map(i => i.cantidad + ' × ' + i.nombre).join(', ') + ' · Total oficial: ' + formatoPrecio(pedido.total);
            caja.append(titulo, detalle);
            if (pedido.aviso) {const a = document.createElement('p'); a.textContent = pedido.aviso; caja.append(a);}
            if (pedido.estado === 'pendiente_pago') caja.append(boton('Iniciar pago de prueba', async () => {
                const pago = await api('/payments', {method: 'POST', body: JSON.stringify({order_id: pedido.id})});
                aviso('Pago iniciado. Identificador para la consola del proveedor de prueba: ' + pago.id + '. Después de la aprobación, actualiza tus pedidos.');
            }));
            if (['pendiente_pago', 'pagado', 'cancelando'].includes(pedido.estado)) caja.append(boton('Anular pedido', async () => {
                const motivo = prompt('Motivo de anulación (mínimo 5 caracteres):'); if (!motivo) return;
                await api('/orders/' + pedido.id + '/cancel', {method: 'POST', body: JSON.stringify({motivo})}); await cargarPedidos();
            }));
            if (['pagado', 'preparando', 'despachado', 'entregado'].includes(pedido.estado)) caja.append(boton('Ver comprobante', async () => {
                const r = await api('/orders/' + pedido.id + '/receipt');
                caja.querySelector('.comprobante')?.remove();
                const comprobante = document.createElement('section'); comprobante.className = 'comprobante mt-3';
                const titulo = document.createElement('h4'); titulo.textContent = 'Comprobante ' + r.numero;
                const nota = document.createElement('p'); nota.textContent = r.tipo;
                const lista = document.createElement('ul');
                for (const item of r.items) {const li = document.createElement('li');li.textContent = item.cantidad + ' × ' + item.nombre + ': ' + formatoPrecio(item.subtotal);lista.append(li);}
                const total = document.createElement('p');total.className = 'fw-bold';total.textContent = 'Total: ' + formatoPrecio(r.total) + ' CLP';
                comprobante.append(titulo, nota, lista, total, boton('Imprimir comprobante', () => window.print())); caja.append(comprobante);
            }));
            lista.append(caja);
        }
    } catch (e) {lista.textContent = e.message + ' Usa Actualizar pedidos para reintentar.';}
}
document.getElementById('recargar').addEventListener('click', cargarPedidos);
document.getElementById('salir').addEventListener('click', async () => {try {await api('/auth/logout', {method: 'POST'});location.reload();} catch (e) {aviso(e.message, true);}});
document.getElementById('registro').addEventListener('submit', async function (e) {
    e.preventDefault(); const b = this.querySelector('button'); b.disabled = true;
    try {const r = await api('/auth/register', {method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(this)))});aviso(r.message);this.reset();} catch (e) {aviso(e.message, true);} finally {b.disabled = false;}
});
document.getElementById('verificacion').addEventListener('submit', async function (e) {
    e.preventDefault(); try {const r = await api('/auth/verify', {method: 'POST', body: JSON.stringify({token: document.getElementById('codigo').value})});aviso(r.message);await cargarPedidos();} catch (e) {aviso(e.message, true);}
});
document.getElementById('reenviar').addEventListener('click', async () => {try {aviso((await api('/auth/resend', {method: 'POST'})).message);} catch (e) {aviso(e.message, true);}});
document.getElementById('perfil').addEventListener('submit', async function (e) {
    e.preventDefault(); try {await api('/me', {method: 'PUT', body: JSON.stringify(Object.fromEntries(new FormData(this)))});aviso('Datos actualizados.');} catch (e) {aviso(e.message, true);}
});
async function cargarCuenta() {
    try {
        const p = await api('/me'); document.getElementById('estadoCuenta').textContent = 'Cuenta: ' + p.correo;
        for (const key of ['nombre', 'direccion', 'comuna', 'provincia', 'region', 'telefono']) document.getElementById('perfil_' + key).value = p[key] || '';
        const rs = await api('/reservations'); const lista = document.getElementById('reservasCuenta'); lista.replaceChildren();
        if (!rs.length) lista.textContent = 'No tienes reservas.';
        for (const r of rs) {
            const p = document.createElement('p'); p.textContent = r.fecha + ' · ' + r.personas + ' personas · ' + r.status;
            if (r.status !== 'cancelada') p.append(boton('Cancelar reserva', async () => {await api('/reservations/' + r.id, {method: 'PUT', body: JSON.stringify({status: 'cancelada'})});location.reload();})); lista.append(p);
        }
    } catch (e) {document.getElementById('estadoCuenta').textContent = e.message;}
}
cargarCuenta(); cargarPedidos();
