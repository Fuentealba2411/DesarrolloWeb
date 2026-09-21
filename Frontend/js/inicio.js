const carruselPromociones = document.getElementById("promociones");
const movimientoReducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

new bootstrap.Carousel(carruselPromociones, { ride: movimientoReducido ? false : "carousel" });
