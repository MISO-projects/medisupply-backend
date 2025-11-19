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
        Generates a recommendation for the vendor based on the visit details and top products.
        """
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not configured - returning default message")
            return "Recomendación no disponible (API Key no configurada)."

        try:
            # Format top products for the prompt
            products_summary = ""
            if client_orders:
                products_summary = "Productos más pedidos por este cliente (Top 5):\n"
                for idx, product in enumerate(client_orders[:5], 1):
                    product_name = product.get('nombre', 'Producto desconocido')
                    quantity = product.get('cantidad_total', 0)
                    products_summary += f"{idx}. {product_name} - Cantidad total pedida: {quantity} unidades\n"

            else:
                products_summary = "El cliente no tiene historial de pedidos."

            prompt = f"""
            Actúa como un asistente de ventas experto para un vendedor que visita a un cliente.

            Detalles de la visita actual/reciente:
            "{visit_details}"

            Productos favoritos del cliente (más pedidos históricamente):
            {products_summary}

            Basado en esta información, genera una recomendación breve y accionable (máximo 2-3 frases) para el vendedor.
            Sugiere qué productos ofrecer (priorizando sus favoritos o productos complementarios) o qué temas tratar en la próxima interacción para aumentar las ventas o mejorar la relación.
            """

            response = await self.model.generate_content_async(prompt)
            recommendation = response.text.strip()

            return recommendation

        except Exception as e:
            logger.error(f"Error generating recommendation with Gemini: {e}", exc_info=True)
            return "Error al generar recomendación."
