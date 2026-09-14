require('dotenv').config();
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();

const SECRETO = process.env.API_SECRET;
const URL_API_PRIVADA = process.env.PRIVATE_API_URL;

function validarSecreto(req, res, next) {
    const secretoRecibido = req.headers['x-api-key'];
    if (secretoRecibido !== SECRETO) {
        return res.status(401).json({ message: "Acceso no autorizado, falta o esta mal el x-api-key" });
    }
    next();
}

app.use('/usuarios', validarSecreto, createProxyMiddleware({
    target: URL_API_PRIVADA,
    changeOrigin: true
}));

app.listen(3000, () => {
    console.log("API Gateway corriendo en http://localhost:3000");
});
