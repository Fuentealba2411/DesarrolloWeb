const parametrosUrl = new URLSearchParams(window.location.search);
document.getElementById("buscar").value = parametrosUrl.get("buscar") || "";

const textoPerfil = document.getElementById("textoPerfil");
const usuarioGuardado = localStorage.getItem("usuario");
if (usuarioGuardado) {
    textoPerfil.innerText = usuarioGuardado;
}

document.getElementById("formularioAcceso").addEventListener("submit", function (evento) {
    evento.preventDefault();
    const correo = document.getElementById("correoAcceso").value;
    const nombre = correo.split("@")[0];
    localStorage.setItem("usuario", nombre);
    textoPerfil.innerText = nombre;
    bootstrap.Modal.getInstance(document.getElementById("modalAcceso")).hide();
    this.reset();
});
