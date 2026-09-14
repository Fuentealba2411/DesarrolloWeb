const express = require('express');
const app = express();
app.use(express.json());

let usuarios = [
    { id: 1, nombre: "Max", pass: "1234" },
    { id: 2, nombre: "Fabian", pass: "hola1234" }
];
let siguienteId = 3;

app.get('/usuarios', (req, res) => {
    res.json(usuarios);
});

app.get('/usuarios/:id', (req, res) => {
    const usuario = usuarios.find(u => u.id == req.params.id);
    if (!usuario) {
        return res.status(404).json({ message: "Usuario no encontrado" });
    }
    res.json(usuario);
});

app.post('/usuarios', (req, res) => {
    const nuevo = { id: siguienteId++, nombre: req.body.nombre, pass: req.body.pass };
    usuarios.push(nuevo);
    res.status(201).json(nuevo);
});

app.put('/usuarios/:id', (req, res) => {
    const usuario = usuarios.find(u => u.id == req.params.id);
    if (!usuario) {
        return res.status(404).json({ message: "Usuario no encontrado" });
    }
    usuario.nombre = req.body.nombre;
    usuario.pass = req.body.pass;
    res.json(usuario);
});

app.delete('/usuarios/:id', (req, res) => {
    const index = usuarios.findIndex(u => u.id == req.params.id);
    if (index == -1) {
        return res.status(404).json({ message: "Usuario no encontrado" });
    }
    usuarios.splice(index, 1);
    res.json({ message: "Usuario eliminado" });
});

app.listen(4001, () => {
    console.log("API privada corriendo en http://localhost:4001");
});
