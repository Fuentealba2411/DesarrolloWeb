const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const { ApolloServer, gql } = require('apollo-server-express');
const Usuario = require('./models/usuario');

// Conexion a MongoDB
mongoose.connect('mongodb://localhost:27017/bdunab2')
  .then(() => console.log('MongoDB conectado'))
  .catch(err => console.error('Error al conectar MongoDB:', err));

// 1. Definicion del Schema (typeDefs)
const typeDefs = gql`
  type Usuario {
    id: ID!
    nombre: String!
    pass: String!
  }

  input UsuarioInput {
    nombre: String!
    pass: String!
  }

  type Alert {
    message: String
  }

  type Query {
    getUsuarios(limit: Int, offset: Int): [Usuario]
    getUsuarioById(id: ID!): Usuario
  }

  type Mutation {
    addUsuario(input: UsuarioInput): Usuario
    updUsuario(id: ID!, input: UsuarioInput): Usuario
    delUsuario(id: ID!): Alert
  }
`;

// 2. Resolvers (Logica de las operaciones)
const resolvers = {
  Query: {
    async getUsuarios(obj, { limit, offset }) {
      const usuarios = await Usuario.find()
        .skip(offset || 0)
        .limit(limit || 20);
      return usuarios;
    },
    async getUsuarioById(obj, { id }) {
      const usuarioBus = await Usuario.findById(id);
      if (usuarioBus == null) {
        return null;
      } else {
        return usuarioBus;
      }
    },
  },
  Mutation: {
    async addUsuario(obj, { input }) {
      if (!input.nombre || !input.pass) {
        throw new Error('Nombre y pass son obligatorios');
      }
      const usuario = new Usuario(input);
      await usuario.save();
      return usuario;
    },
    async updUsuario(obj, { id, input }) {
      const usuario = await Usuario.findByIdAndUpdate(id, input, { new: true });
      if (usuario == null) {
        throw new Error('Usuario no encontrado');
      }
      return usuario;
    },
    async delUsuario(obj, { id }) {
      const usuario = await Usuario.findByIdAndDelete(id);
      if (usuario == null) {
        throw new Error('Usuario no encontrado');
      }
      return {
        message: "Usuario Eliminado"
      };
    }
  }
};

// 3. Inicializacion del servidor Express y Apollo Server
let apolloServer = null;

const corsOption = {
  origin: "http://localhost:8090",
  credentials: false
};

const app = express();
app.use(cors(corsOption));

async function startServer() {
  apolloServer = new ApolloServer({
    typeDefs,
    resolvers
  });

  await apolloServer.start();
  apolloServer.applyMiddleware({ app, cors: false });

  app.listen(8090, function () {
    console.log("Graphql Iniciado en http://localhost:8090" + apolloServer.graphqlPath);
  });
}

startServer();