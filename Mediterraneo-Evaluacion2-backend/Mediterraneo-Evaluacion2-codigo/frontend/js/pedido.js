let intentoPedido = sessionStorage.getItem('intentoPedido') || crypto.randomUUID();
sessionStorage.setItem('intentoPedido', intentoPedido);
document.getElementById('pedido').addEventListener('submit', async function (e) {
    e.preventDefault(); const b = this.querySelector('button'); b.disabled = true;
    const resultado = document.getElementById('resultadoPedido'); resultado.textContent = 'Verificando disponibilidad y creando pedido…';
    try {
        if (!carrito.length) throw new Error('Agrega platos al carrito antes de confirmar.');
        const pedido = {items: carrito.map(i => ({id: i.id, cantidad: i.cantidad})), direccion: document.getElementById('direccionPedido').value};
        const r = await api('/orders', {method: 'POST', headers: {'Idempotency-Key': intentoPedido}, body: JSON.stringify(pedido)});
        resultado.textContent = 'Pedido ' + r.id + ' guardado. Estado: ' + r.status + '. Total oficial: ' + formatoPrecio(r.total) + '. Continúa en Mi cuenta para iniciar el pago.';
        if (r.status === 'cancelado' || r.status === 'cancelando') {sessionStorage.removeItem('intentoPedido'); throw new Error('El intento anterior fue cancelado. Recarga la página para generar otro pedido.');}
        carrito = []; guardarCarrito(); sessionStorage.removeItem('intentoPedido'); intentoPedido = crypto.randomUUID();
    } catch (e) {resultado.textContent = e.message + ' El carrito se conserva si no se creó el pedido.';} finally {b.disabled = false;}
});
