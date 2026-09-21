let carrito = JSON.parse(localStorage.getItem("carrito")) || [];

function formatoPrecio(numero) {
    return "$" + numero.toLocaleString("es-CL");
}

function guardarCarrito() {
    localStorage.setItem("carrito", JSON.stringify(carrito));
    mostrarCarrito();
}

function agregarAlCarrito(nombre, precio) {
    let platoEncontrado = carrito.find((item) => item.nombre == nombre);
    if (platoEncontrado) {
        platoEncontrado.cantidad++;
    } else {
        carrito.push({ nombre: nombre, precio: precio, cantidad: 1 });
    }
    guardarCarrito();
}

function quitarDelCarrito(nombre) {
    carrito = carrito.filter((item) => item.nombre != nombre);
    guardarCarrito();
}

function mostrarCarrito() {
    const lista = document.getElementById("listaCarrito");
    lista.innerHTML = "";
    let total = 0;
    let cantidadTotal = 0;

    carrito.forEach((item) => {
        total += item.precio * item.cantidad;
        cantidadTotal += item.cantidad;

        let fila = document.createElement("li");
        fila.className = "d-flex justify-content-between align-items-center gap-2 py-2 border-bottom";

        let texto = document.createElement("span");
        texto.innerText = item.cantidad + " x " + item.nombre + " (" + formatoPrecio(item.precio * item.cantidad) + ")";

        let botonQuitar = document.createElement("button");
        botonQuitar.type = "button";
        botonQuitar.className = "btn btn-sm btn-borde-rojo";
        botonQuitar.innerText = "Quitar";
        botonQuitar.setAttribute("aria-label", "Quitar " + item.nombre);
        botonQuitar.addEventListener("click", function () {
            quitarDelCarrito(item.nombre);
        });

        fila.appendChild(texto);
        fila.appendChild(botonQuitar);
        lista.appendChild(fila);
    });

    document.getElementById("contadorCarrito").innerText = cantidadTotal;
    document.getElementById("totalCarrito").innerText = formatoPrecio(total);
    document.getElementById("carritoVacio").classList.toggle("d-none", carrito.length > 0);
    document.getElementById("botonVaciar").disabled = carrito.length == 0;
}

document.getElementById("botonVaciar").addEventListener("click", function () {
    carrito = [];
    guardarCarrito();
});

mostrarCarrito();
