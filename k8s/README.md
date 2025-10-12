# Gestión de Kubernetes

## Programación de Auto-escalado

### Reducción de Escala Automática
Los servicios se reducen automáticamente a 0 réplicas a las **11 PM hora Colombia** (4 AM UTC) cada noche mediante CronJob para ahorrar costos.

### Operaciones Manuales

#### Reducir Escala de Servicios (Manual)
Usa esto cuando quieras reducir la escala temprano (por ejemplo, terminar de trabajar a las 8 PM):

**Opción 1 - Usando kubectl:**
```bash
kubectl create job --from=cronjob/scale-down-services manual-scale-down-$(date +%s) -n default
```

**Opción 2 - Usando la Consola de GCP:**
1. Ve a GKE → Workloads
2. Encuentra el CronJob `scale-down-services`
3. Haz clic en "Actions" → "Trigger Job"

**Opción 3 - Comando kubectl directo:**
```bash
kubectl scale deployment --all --replicas=0 -n default
```

#### Aumentar Escala de Servicios (Manual)
Usa esto cuando necesites comenzar a trabajar:

**Opción 1 - Aplicar el job de scale-up:**
```bash
kubectl apply -f k8s/scale-up-job.yaml
```

**Opción 2 - Comando kubectl directo:**
```bash
# Aumentar escala de todos los servicios
kubectl scale deployment/proveedores-service --replicas=1 -n default
kubectl scale deployment/productos-service --replicas=1 -n default
kubectl scale deployment/redis --replicas=1 -n default
# ... etc
```

**Opción 3 - Aumentar escala de todos a la vez:**
```bash
kubectl scale deployment --all --replicas=1 -n default
```

#### Verificar Estado Actual
```bash
# Ver todos los deployments y su cantidad de réplicas
kubectl get deployments -n default

# Ver deployments escalando en tiempo real
kubectl get deployments -n default --watch
```

#### Ver Logs de Job/CronJob
```bash
# Ver programación del CronJob
kubectl get cronjobs -n default

# Ver jobs recientes creados por el CronJob
kubectl get jobs -n default

# Ver logs del último job de scale-down
kubectl logs -n default job/scale-down-services-<job-id>
```
