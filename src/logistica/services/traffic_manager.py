import requests
import numpy as np
import time
from typing import List, Tuple, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class TrafficAPIManager:
    """Gestor para calcular matrices de tiempo de viaje usando OSRM"""
    
    def calculate_traffic_matrix(self, coords: List[Tuple[float, float]]) -> Dict:
        """
        Calcula la matriz de tiempos de viaje entre todas las coordenadas usando OSRM
        
        Args:
            coords: Lista de tuplas (latitud, longitud)
            
        Returns:
            Dict con la matriz de tiempos, información del proveedor y tiempo de cálculo
        """
        logger.info(f"Calculando matriz de tiempos con OSRM para {len(coords)} puntos")
        
        start_time = time.perf_counter()
        matrix = self._osrm_matrix(coords)
        calc_time = time.perf_counter() - start_time
        
        return {
            'matrix': matrix,
            'provider_used': 'osrm',
            'has_realtime_traffic': False,
            'calculation_time_ms': int(calc_time * 1000),
            'matrix_size': f"{len(coords)}x{len(coords)}"
        }
    
    def _osrm_matrix(self, coords: List[Tuple[float, float]]) -> np.ndarray:
        """
        Obtiene la matriz de tiempos de viaje desde la API de OSRM
        
        Args:
            coords: Lista de tuplas (latitud, longitud)
            
        Returns:
            Matriz numpy con tiempos de viaje en segundos
        """
        if len(coords) == 0:
            return np.array([])
        
        # OSRM espera formato: lng,lat
        coords_str = ';'.join([f"{lng},{lat}" for lat, lng in coords])
        
        url = f"http://router.project-osrm.org/table/v1/driving/{coords_str}"
        params = {
            'sources': ';'.join([str(i) for i in range(len(coords))]),
            'destinations': ';'.join([str(i) for i in range(len(coords))])
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != 'Ok':
                raise Exception(f"OSRM API error: {data.get('message', 'Unknown error')}")
            
            clean_matrix = []
            for row in data.get('durations', []):
                clean_row = [val if val is not None else 999999 for val in row]
                clean_matrix.append(clean_row)
            
            matrix = np.array(clean_matrix, dtype=np.int32)
            matrix = np.nan_to_num(matrix, nan=999999, posinf=999999, neginf=999999)
            
            return matrix
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al conectar con OSRM: {str(e)}")
            # Retornar matriz con valores altos si hay error de conexión
            size = len(coords)
            return np.full((size, size), 999999, dtype=np.int32)
        except Exception as e:
            logger.error(f"Error al procesar respuesta de OSRM: {str(e)}")
            size = len(coords)
            return np.full((size, size), 999999, dtype=np.int32)


def optimize_route_order(
    origin_coords: Tuple[float, float],
    stops_coords: List[Tuple[float, float]],
    traffic_manager: Optional[TrafficAPIManager] = None
) -> List[int]:
    if not stops_coords:
        return []
    
    if len(stops_coords) == 1:
        return [0]
    
    if traffic_manager is None:
        traffic_manager = TrafficAPIManager()
    
    all_coords = [origin_coords] + stops_coords
    
    logger.info(f"Optimizando ruta con {len(stops_coords)} paradas")
    result = traffic_manager.calculate_traffic_matrix(all_coords)
    matrix = result['matrix']
    
    n_stops = len(stops_coords)
    visited = [False] * n_stops
    route = []
    current = 0  
    
    for _ in range(n_stops):
        best_next = None
        best_time = float('inf')
        
        for i in range(n_stops):
            if not visited[i]:
                time_to_stop = matrix[current][i + 1]  
                if time_to_stop < best_time:
                    best_time = time_to_stop
                    best_next = i
        
        if best_next is not None:
            route.append(best_next)
            visited[best_next] = True
            current = best_next + 1  
    
    logger.info(f"Orden optimizado de paradas: {route}")
    return route

