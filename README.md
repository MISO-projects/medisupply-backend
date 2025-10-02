# Medisupply

## Configuración

Para iniciar la base de datos de PostgreSQL y Redis se debe ejecutar el siguiente comando:

```bash
docker compose up 
```

## Iniciar los servicios
Se pueden utilizar los profiles para iniciar ciertos servicios.

```sh
docker compose up -d --profile ordenes
```

Para iniciar todos los servicios se debe ejecutar el siguiente comando:

```bash
docker compose up -d --profile dev
```

## Utilización de Pub/Sub
Para utilizar Pub/Sub se debe tener un proyecto de Google Cloud y un topic de Pub/Sub.
Se debe crear un archivo `credentials.json` en la raíz del servicio que se esté utilizando.
Este archivo tendra las credenciales del service account para utilizar Pub/Sub.