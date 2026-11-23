const formulario = document.getElementById('formularioContacto');
formulario.addEventListener('submit', async function (evento) {
    evento.preventDefault(); const boton = this.querySelector('[type=submit]'); boton.disabled = true;
    aviso('Enviando mensaje…');
    try {
        const datos = Object.fromEntries(new FormData(this));
        const respuesta = await api('/contact', {method: 'POST', body: JSON.stringify(datos)});
        aviso(respuesta.message); this.reset();
    } catch (error) {aviso(error.message + ' Puedes reintentar.', true);}
    finally {boton.disabled = false;}
});
