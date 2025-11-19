import google.generativeai as genai
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY is not set. Gemini features will be disabled.")
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    async def generate_recommendation(self, visit_details: str, client_orders: List[Dict[str, Any]]) -> str:
        """
        Generates a recommendation for the vendor based on the visit details and client orders.
        """
        if not self.api_key:
            return "Recomendación no disponible (API Key no configurada)."

        try:
            # Format orders for the prompt
            orders_summary = ""
            if client_orders:
                orders_summary = "Últimos pedidos del cliente:\n"
                for order in client_orders[:5]: # Limit to last 5 orders
                    products = order.get('detalles', [])
                    product_names = [p.get('nombre_producto', 'Producto desconocido') for p in products]
                    orders_summary += f"- Fecha: {order.get('fecha_creacion', 'N/A')}, Productos: {', '.join(product_names)}\n"
            else:
                orders_summary = "El cliente no tiene pedidos recientes."

            prompt = f"""
            Actúa como un asistente de ventas experto para un vendedor que visita a un cliente.
            
            Detalles de la visita actual/reciente:
            "{visit_details}"
            
            Historial de pedidos del cliente:
            {orders_summary}
            
            Basado en esta información, genera una recomendación breve y accionable (máximo 2 frases) para el vendedor. 
            Sugiere qué productos ofrecer o qué temas tratar en la próxima interacción para aumentar las ventas o mejorar la relación.
            """

            response = await self.model.generate_content_async(prompt)
            return response.text.strip()

        except Exception as e:
            logger.error(f"Error generating recommendation with Gemini: {e}")
            return "Error al generar recomendación."
