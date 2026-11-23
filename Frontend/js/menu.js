const platos = [
    { nombre: "Shakshuka", categoria: "Desayunos", descripcion: "Huevos cocidos en salsa de tomate, pimentón y comino, con pan.", precio: 6500, imagen: "shakshuka.jpg" },
    { nombre: "Tostada con tomate", categoria: "Desayunos", descripcion: "Pan de masa madre con tomate rallado, aceite de oliva y orégano.", precio: 4200, imagen: "tostada-tomate.jpg" },
    { nombre: "Yogur griego con miel", categoria: "Desayunos", descripcion: "Yogur natural, miel y nueces.", precio: 3500, imagen: "yogur-miel.jpg" },
    { nombre: "Labneh con pita", categoria: "Desayunos", descripcion: "Queso de yogur con zaatar, aceitunas y pan pita tibio.", precio: 4800, imagen: "labneh-pita.jpg" },
    { nombre: "Ensalada griega", categoria: "Almuerzos", descripcion: "Tomate, pepino, aceitunas kalamata y queso feta con orégano.", precio: 5900, imagen: "ensalada-griega.jpg" },
    { nombre: "Moussaka", categoria: "Almuerzos", descripcion: "Berenjena, carne, papas y bechamel gratinada al horno.", precio: 9800, imagen: "moussaka.jpg" },
    { nombre: "Paella de mariscos", categoria: "Almuerzos", descripcion: "Arroz con azafrán, choritos, camarones y calamar.", precio: 12500, imagen: "paella.jpg" },
    { nombre: "Falafel con hummus", categoria: "Almuerzos", descripcion: "Garbanzos, comino y tahini, con pan pita tibio.", precio: 7900, imagen: "falafel.jpg" },
    { nombre: "Pasta al pesto", categoria: "Almuerzos", descripcion: "Fusilli con albahaca, piñones y parmesano.", precio: 8500, imagen: "pasta-pesto.jpg" },
    { nombre: "Merluza a la plancha", categoria: "Almuerzos", descripcion: "Merluza con limón, papas al horno y hierbas.", precio: 10500, imagen: "merluza.jpg" },
    { nombre: "Baklava", categoria: "Postres", descripcion: "Masa filo, nueces y miel.", precio: 3900, imagen: "baklava.jpg" },
    { nombre: "Panna cotta", categoria: "Postres", descripcion: "Crema de vainilla con salsa de frutos rojos.", precio: 4200, imagen: "panna-cotta.jpg" },
    { nombre: "Loukoumades", categoria: "Postres", descripcion: "Buñuelos fritos con miel y canela.", precio: 3800, imagen: "loukoumades.jpg" }
];

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
            botonAgregar.innerText = "Agregar";
            botonAgregar.setAttribute("aria-label", "Agregar " + plato.nombre + " al carrito");
            botonAgregar.addEventListener("click", function () {
                agregarAlCarrito(plato.nombre, plato.precio);
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
        mostrarPlatos(categoria);
    });
    contenedorBotones.appendChild(boton);
});

mostrarPlatos(categoriaActual);
