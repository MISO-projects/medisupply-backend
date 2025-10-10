# Medisupply

## Configuración del entorno de desarrollo

Para iniciar la base de datos de PostgreSQL, Redis y todos los microservicios, se debe ejecutar el siguiente comando en la raíz del proyecto:

```bash
docker compose up --profile dev
```

Se pueden utilizar profiles específicos para iniciar solo ciertos servicios. El siguiente comando inicia solo el servicio de productos además de la base de datos, Redis y los BFFs:

```sh
docker compose up --profile ordenes
```

de forma similar con el servicio de proveedores:

```sh
docker compose up --profile proveedores
```

Los profiles disponibles son:
- dev
- productos
- ordenes
- proveedores
- reportes
- ventas
- clientes
- auditoria

## Utilización de Pub/Sub
Para utilizar Pub/Sub se debe tener un proyecto de Google Cloud y un topic de Pub/Sub.
Se debe crear un archivo `credentials.json` en la raíz del servicio que se esté utilizando.
Este archivo tendra las credenciales del service account para utilizar Pub/Sub.