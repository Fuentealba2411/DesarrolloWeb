const formulario = document.getElementById("formularioContacto");
const mensajeExito = document.getElementById("mensajeExito");

formulario.addEventListener("submit", function (evento) {
    evento.preventDefault();
    const nombre = document.getElementById("nombre").value;

    mensajeExito.innerText = "Gracias, " + nombre + ". Recibimos tu mensaje y te responderemos al correo.";
    mensajeExito.classList.remove("d-none");
    formulario.reset();
    mensajeExito.scrollIntoView({ behavior: "smooth", block: "center" });
});
