const formulario = document.getElementById("formularioReserva");
const mensajeExito = document.getElementById("mensajeExito");
const campoFecha = document.getElementById("fecha");

campoFecha.min = new Date().toISOString().split("T")[0];

formulario.addEventListener("submit", function (evento) {
    evento.preventDefault();
    const nombre = document.getElementById("nombre").value;
    const personas = document.getElementById("personas").value;
    const fecha = campoFecha.value.split("-").reverse().join("-");

    mensajeExito.innerText = "Gracias, " + nombre + ". Recibimos tu reserva para " + personas + " personas el " + fecha + ". Te escribiremos al correo para confirmarla.";
    mensajeExito.classList.remove("d-none");
    formulario.reset();
    mensajeExito.scrollIntoView({ behavior: "smooth", block: "center" });
});
