const formulario = document.getElementById('formularioReserva');
const hoy = new Date(); hoy.setMinutes(hoy.getMinutes() - hoy.getTimezoneOffset());
document.getElementById('fecha').min = hoy.toISOString().slice(0, 10);
formulario.addEventListener('submit', async function (evento) {
    evento.preventDefault(); const boton = this.querySelector('[type=submit]'); boton.disabled = true;
    aviso('Guardando reserva…');
    try {
        const datos = Object.fromEntries(new FormData(this)); datos.personas = Number(datos.personas);
        const respuesta = await api('/reservations', {method: 'POST', body: JSON.stringify(datos)});
        aviso(respuesta.message); this.reset();
    } catch (error) {aviso(error.message + ' Para reservar debes iniciar sesión y verificar tu correo.', true);}
    finally {boton.disabled = false;}
});
