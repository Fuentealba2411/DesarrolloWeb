let platos = [];


const categorias = ["Todos", "Desayunos", "Almuerzos", "Postres"];
const parametros = new URLSearchParams(window.location.search);
const busqueda = (parametros.get("buscar") || "").trim();
const textoBuscado = busqueda.toLowerCase();
let categoriaActual = parametros.get("categoria");
if (!categorias.includes(categoriaActual)) {
    categoriaActual = "Todos";
}

const contenedorBotones = document.getElementById("botonesCategoria");
const contenedorPlatos = document.getElementById("listaPlatos");
const mensajeVacio = document.getElementById("mensajeVacio");
const textoResultados = document.getElementById("textoResultados");

if (busqueda != "") {
    textoResultados.innerText = "Resultados para: " + busqueda;
    textoResultados.classList.remove("d-none");
}

function mostrarPlatos(categoriaElegida) {
    contenedorPlatos.innerHTML = "";
    let cantidad = 0;

    platos.forEach((plato) => {
        let coincideCategoria = categoriaElegida == "Todos" || plato.categoria == categoriaElegida;
        let coincideTexto = (plato.nombre + " " + plato.descripcion).toLowerCase().includes(textoBuscado);

        if (coincideCategoria && coincideTexto) {
            cantidad++;

            let columna = document.createElement("div");
            columna.className = "col-md-6 col-lg-4";

            let tarjeta = document.createElement("div");
            tarjeta.className = "plato plato-con-imagen";

            let imagen = document.createElement("img");
            imagen.className = "plato-img";
            imagen.src = "imagenes/" + plato.imagen;
            imagen.alt = "Foto de " + plato.nombre;
            imagen.width = 600;
            imagen.height = 400;
            imagen.loading = "lazy";

            let cuerpo = document.createElement("div");
            cuerpo.className = "plato-cuerpo";

            let nombre = document.createElement("h3");
            nombre.innerText = plato.nombre;

            let categoria = document.createElement("p");
            categoria.className = "categoria";
            categoria.innerText = plato.categoria;

            let descripcion = document.createElement("p");
            descripcion.innerText = plato.descripcion;

            let pie = document.createElement("div");
            pie.className = "d-flex justify-content-between align-items-center mt-auto pt-3";

            let precio = document.createElement("p");
            precio.className = "precio";
            precio.innerText = formatoPrecio(plato.precio);

            let botonAgregar = document.createElement("button");
            botonAgregar.type = "button";
            botonAgregar.className = "btn btn-sm btn-rojo";
            botonAgregar.innerText = plato.stock ? "Agregar" : "Agotado";
            botonAgregar.disabled = !plato.stock;
            botonAgregar.setAttribute("aria-label", "Agregar " + plato.nombre + " al carrito");
            botonAgregar.addEventListener("click", function () {
                agregarAlCarrito(plato.nombre, plato.precio, plato.id);
            });

            pie.appendChild(precio);
            pie.appendChild(botonAgregar);
            cuerpo.appendChild(nombre);
            cuerpo.appendChild(categoria);
            cuerpo.appendChild(descripcion);
            cuerpo.appendChild(pie);
            tarjeta.appendChild(imagen);
            tarjeta.appendChild(cuerpo);
            columna.appendChild(tarjeta);
            contenedorPlatos.appendChild(columna);
        }
    });

    mensajeVacio.classList.toggle("d-none", cantidad > 0);
}

categorias.forEach((categoria) => {
    let boton = document.createElement("button");
    boton.type = "button";
    boton.className = "btn btn-borde-rojo";
    boton.innerText = categoria;
    if (categoria == categoriaActual) {
        boton.classList.add("active");
    }
    boton.addEventListener("click", function () {
        document.querySelectorAll("#botonesCategoria button").forEach((otro) => {
            otro.classList.remove("active");
        });
        boton.classList.add("active");
        categoriaActual = categoria;
        mostrarPlatos(categoria);
    });
    contenedorBotones.appendChild(boton);
});

async function cargarCatalogo() {
    contenedorPlatos.textContent = 'Cargando carta…';
    try {
        platos = await api('/products');
        mostrarPlatos(categoriaActual);
    } catch (error) {
        contenedorPlatos.textContent = error.message;
        const reintentar = document.createElement('button');
        reintentar.className = 'btn btn-rojo'; reintentar.textContent = 'Reintentar';
        reintentar.addEventListener('click', cargarCatalogo); contenedorPlatos.append(reintentar);
    }
}
cargarCatalogo();
